from __future__ import annotations

import atexit
import io
import logging
import platform
import tarfile
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from typing import ClassVar

import docker

logger = logging.getLogger(__name__)


class DockerExecutor:
    _lock = threading.Lock()
    _client: ClassVar[docker.client.DockerClient] = (
        docker.from_env()
        if platform.system() == "Linux"
        else docker.from_env(environment={"DOCKER_HOST": f"unix://{Path.home()}/.docker/run/docker.sock"})
    )

    _container_pools: ClassVar[dict[str, list[docker.models.containers.Container]]] = defaultdict(list)

    def get_container(self, image: str) -> docker.models.containers.Container:
        """Get or create a long-running container for the given image."""
        # pull image if necessary
        # we only really need a lock per image, but let's keep it simple to start with: one lock total
        # could get fancy:
        #   - image_lock
        #   - image_pull_locks: dict from image to lock
        #   - you have to acquire image_lock to check for image_pull_locks[image], create lock if not found
        # then you have to acquire image_pull_locks[image] to pull the image
        # that way, you can pull different images concurrently, because different locks
        with self._lock:
            try:
                self._client.images.get(image)
            except docker.errors.ImageNotFound:
                logger.info(f"Pulling image {image}...")  # TODO: logging locks?
                self._client.images.pull(image)

        with self._lock:
            pool = self._container_pools[image]
            if pool:
                return pool.pop()

        # Create container outside the lock.
        # We add it to the pool when finished with it.
        logger.info(f"Creating container from image {image}...")
        return self._client.containers.run(
            image,
            ["tail", "-f", "/dev/null"],
            detach=True,
        )

    def release_container(self, image: str, container: docker.models.containers.Container):
        # TODO: can we find the image from the container, so simplify the signature?
        with self._lock:
            self._container_pools[image].append(container)

    def write(self, container: docker.models.containers.Container, content: str, dest: Path) -> None:
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w") as tar:
            file_bytes = content.encode("utf-8")
            tarinfo = tarfile.TarInfo(name=dest.name)
            tarinfo.size = len(file_bytes)
            tarinfo.mtime = time.time()
            tar.addfile(tarinfo, io.BytesIO(file_bytes))
        data.seek(0)

        succeeded = container.put_archive(str(dest.parent), data)
        assert succeeded

    @classmethod
    def cleanup(self) -> None:
        """Remove all containers in the pool."""
        for pool in self._container_pools.values():
            for container in pool:
                container.remove(force=True)
        self._container_pools.clear()

    # TOOD: timeouts?
    def exec_run(
        self,
        container: docker.models.containers.Container,
        command: list[str],
        environment: dict[str, str] | None = None,
        workdir: str | None = None,
    ) -> tuple[int, bytes]:
        return container.exec_run(command, environment=environment, workdir=workdir)

    def exec_run_timed(
        self,
        container: docker.models.containers.Container,
        command: list[str],
        environment: dict[str, str] | None = None,
        workdir: str | None = None,
    ) -> str:
        "Run the given command in a container, returning a string representing the timed output."
        logs: list[tuple[float, bytes]] = []
        previous = time.perf_counter()  # must come after getting the container
        _, output_stream = container.exec_run(command, tty=True, stream=True, environment=environment, workdir=workdir)
        for chunk in output_stream:
            now = time.perf_counter()
            logs.append((now - previous, chunk))
            previous = now

        output_stream.close()
        # CancellableStream.close() doesn't close the underlying response,
        # causing "ValueError: I/O operation on closed file" at shutdown.
        # See https://github.com/docker/docker-py/issues/3345
        output_stream._response.close()

        return to_string(logs)


def to_string(logs: list[tuple[float, bytes]]) -> str:
    "Return a string constructed from timed docker logs."
    output = b""
    for delta, char in logs:
        rounded_delta = round(delta)
        if rounded_delta == 0:
            output += char
        else:
            output += bytes(f"<~{rounded_delta}s>\n", "utf-8")
            output += char

    return output.decode("utf-8").replace("\r\n", "\n")


class Snippet(ABC):
    """Abstract base class for code snippets in some language."""

    def __init__(self, code: str, image: str):
        self.code = code
        self.image = image
        self.executor = DockerExecutor()

    @abstractmethod
    def output(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def format(self, compress: bool) -> str | None:
        raise NotImplementedError


class PythonSnippet(Snippet):
    "A Python code snippet."

    def output(self) -> str:
        dest = Path("/tmp/main.py")
        container = self.executor.get_container(self.image)
        # TODO: context manager?
        try:
            self.executor.write(container, self.code, dest)
            return self.executor.exec_run_timed(
                container,
                ["python", str(dest)],
                environment={
                    "NO_COLOR": "true",
                    "PYTHONWARNINGS": "ignore",
                },
            )
        finally:
            self.executor.release_container(self.image, container)

    def format(self, compress: bool) -> str | None:
        dest = Path("/tmp/main.py")
        container = self.executor.get_container(self.image)
        try:
            self.executor.write(container, self.code, dest)
            exit_code, _ = self.executor.exec_run(container, ["/bin/sh", "-c", f"python -m pip install ruff && ruff format {dest}"])
            _, bytes_ = self.executor.exec_run(container, ["cat", str(dest)])
            if exit_code != 0:
                formatted = None
            else:
                formatted = bytes_.decode("utf-8")
                if compress:
                    formatted = formatted.replace("\n\n\n", "\n\n")  # crude
            return formatted
        finally:
            self.executor.release_container(self.image, container)


class GoSnippet(Snippet):
    "A Go code snippet."

    def output(self) -> str:
        dest = Path("/tmp/main.go")
        container = self.executor.get_container(self.image)
        try:
            self.executor.write(container, self.code, dest)
            self.executor.exec_run(
                container,
                ["go", "build", str(dest)],
                workdir="/tmp",
            )
            return self.executor.exec_run_timed(container, ["/tmp/main"])
        finally:
            self.executor.release_container(self.image, container)

    def format(self, compress: bool = False) -> str | None:
        dest = Path("/tmp/main.go")
        container = self.executor.get_container(self.image)
        try:
            self.executor.write(container, self.code, dest)
            exit_code, _ = self.executor.exec_run(container, ["go", "fmt", str(dest)])
            if exit_code != 0:
                formatted = None
            else:
                _, output = self.executor.exec_run(container, ["cat", str(dest)])
                formatted = output.decode("utf-8")
                if compress:
                    formatted = formatted.strip().replace("\n\n\n", "\n\n")

            return formatted
        finally:
            self.executor.release_container(self.image, container)


class NodeSnippet(Snippet):
    "A Node code snippet."

    def output(self) -> str:
        dest = Path("/tmp/main.js")
        container = self.executor.get_container(self.image)
        try:
            self.executor.write(container, self.code, dest)
            return self.executor.exec_run_timed(container, ["node", str(dest)], environment={"NO_COLOR": "1"})
        finally:
            self.executor.release_container(self.image, container)

    def format(self, compress: bool = False) -> str | None:
        dest = Path("/tmp/main.js")
        container = self.executor.get_container(self.image)
        try:
            self.executor.write(container, self.code, dest)
            exit_code, _ = self.executor.exec_run(container, ["/bin/sh", "-c", f"npx prettier --write {dest}"])
            _, bytes_ = self.executor.exec_run(container, ["cat", str(dest)])
            if exit_code != 0:
                formatted = None
            else:
                formatted = bytes_.decode("utf-8")
                if compress:
                    formatted = formatted.replace("\n\n\n", "\n\n")  # crude

            return formatted
        finally:
            self.executor.release_container(self.image, container)


class RubySnippet(Snippet):
    "A Ruby code snippet."

    def output(self) -> str:
        dest = Path("/tmp/main.rb")
        container = self.executor.get_container(self.image)
        try:
            self.executor.write(container, self.code, dest)
            return self.executor.exec_run_timed(container, ["ruby", str(dest)])
        finally:
            self.executor.release_container(self.image, container)

    def format(self, compress: bool = False) -> str | None:
        dest = Path("/tmp/main.rb")
        container = self.executor.get_container(self.image)
        try:
            self.executor.write(container, self.code, dest)
            exit_code, _ = self.executor.exec_run(container, ["/bin/sh", "-c", f"gem install rubocop && rubocop -A {dest}"])
            _, bytes_ = self.executor.exec_run(container, ["cat", str(dest)])
            if exit_code != 0:
                formatted = None
            else:
                formatted = bytes_.decode("utf-8")
                if compress:
                    formatted = formatted.replace("\n\n\n", "\n\n")  # crude

            return formatted
        finally:
            self.executor.release_container(self.image, container)


class RustSnippet(Snippet):
    "A Rust code snippet."

    def output(self) -> str:
        dest = Path("/tmp/main.rs")
        container = self.executor.get_container(self.image)
        try:
            self.executor.write(container, self.code, dest)
            self.executor.exec_run(container, ["rustc", "main.rs"], workdir="/tmp")
            return self.executor.exec_run_timed(container, ["/tmp/main"])
        finally:
            self.executor.release_container(self.image, container)

    def format(self, compress: bool = False) -> str | None:
        dest = Path("/tmp/main.rs")
        container = self.executor.get_container(self.image)
        try:
            self.executor.exec_run(container, ["rustup", "component", "add", "rustfmt"])
            self.executor.write(container, self.code, dest)
            exit_code, _ = self.executor.exec_run(container, ["rustfmt", str(dest)])
            _, bytes_ = self.executor.exec_run(container, ["cat", str(dest)])
            if exit_code != 0:
                formatted = None
            else:
                formatted = bytes_.decode("utf-8")
                if compress:
                    formatted = formatted.replace("\n\n\n", "\n\n")  # crude

            return formatted
        finally:
            self.executor.release_container(self.image, container)


# TODO: what about ctrl-c?
atexit.register(DockerExecutor.cleanup)
