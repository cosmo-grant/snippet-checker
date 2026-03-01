from __future__ import annotations

import atexit
import io
import logging
import platform
import tarfile
import time
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import ClassVar

import docker

from .output import GoOutput, NodeOutput, Output, PythonOutput, RubyOutput, RustOutput

logger = logging.getLogger(__name__)


class DockerExecutor:
    _client: ClassVar[docker.client.DockerClient] = (
        docker.from_env()
        if platform.system() == "Linux"
        else docker.from_env(environment={"DOCKER_HOST": f"unix://{Path.home()}/.docker/run/docker.sock"})
    )

    _container_pool: ClassVar[dict[str, docker.models.containers.Container]] = {}

    def _get_container(self, image: str) -> docker.models.containers.Container:
        """Get or create a long-running container for the given image."""
        if image not in self._container_pool:
            try:
                self._client.images.get(image)
            except docker.errors.ImageNotFound:
                logger.info(f"Pulling image {image}...")
                self._client.images.pull(image)

            logger.info(f"Creating container from image {image}...")

            self._container_pool[image] = self._client.containers.run(
                image,
                ["tail", "-f", "/dev/null"],
                detach=True,
            )
        return self._container_pool[image]

    def write(self, image: str, content: str, dest: Path) -> None:
        container = self._get_container(image)
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
        for container in self._container_pool.values():
            container.remove(force=True)
        self._container_pool.clear()

    def exec_run(
        self,
        image: str,
        command: list[str],
        environment: dict[str, str] | None = None,
        workdir: str | None = None,
    ) -> tuple[int, bytes]:
        container = self._get_container(image)
        return container.exec_run(command, environment=environment, workdir=workdir)

    def exec_run_timed(
        self,
        image: str,
        command: list[str],
        environment: dict[str, str] | None = None,
        workdir: str | None = None,
    ) -> list[tuple[float, bytes]]:
        container = self._get_container(image)
        logs: list[tuple[float, bytes]] = []
        previous = time.perf_counter()  # must come after getting the container
        _, output_stream = container.exec_run(command, tty=True, stream=True, environment=environment, workdir=workdir)
        for chunk in output_stream:
            now = time.perf_counter()
            logs.append((now - previous, chunk))
            previous = now

        return logs


class Snippet(ABC):
    """Abstract base class for code snippets in some language."""

    def __init__(self, code: str, image: str):
        self.code = code
        self.image = image
        self.executor = DockerExecutor()

    @cached_property
    @abstractmethod
    def output(self) -> Output:
        raise NotImplementedError

    @abstractmethod
    def format(self, compress: bool) -> str | None:
        raise NotImplementedError


class PythonSnippet(Snippet):
    "A Python code snippet."

    @cached_property
    def output(self) -> PythonOutput:
        dest = Path("/tmp/main.py")
        self.executor.write(self.image, self.code, dest)
        logs = self.executor.exec_run_timed(
            self.image,
            ["python", str(dest)],
            environment={
                "NO_COLOR": "true",
                "PYTHONWARNINGS": "ignore",
            },
        )

        return PythonOutput(logs)

    def format(self, compress: bool) -> str | None:
        dest = Path("/tmp/main.py")
        self.executor.write(self.image, self.code, dest)
        exit_code, foo = self.executor.exec_run(self.image, ["/bin/sh", "-c", f"python -m pip install ruff && ruff format {dest}"])
        _, bytes_ = self.executor.exec_run(self.image, ["cat", str(dest)])
        if exit_code != 0:
            formatted = None
        else:
            formatted = bytes_.decode("utf-8")
            if compress:
                formatted = formatted.replace("\n\n\n", "\n\n")  # crude

        return formatted


class GoSnippet(Snippet):
    "A Go code snippet."

    @cached_property
    def output(self) -> GoOutput:
        dest = Path("/tmp/main.go")
        self.executor.write(self.image, self.code, dest)
        self.executor.exec_run(
            self.image,
            ["go", "build", str(dest)],
            workdir="/tmp",
        )
        logs = self.executor.exec_run_timed(self.image, ["/tmp/main"])
        return GoOutput(logs)

    def format(self, compress: bool = False) -> str | None:
        dest = Path("/tmp/main.go")
        self.executor.write(self.image, self.code, dest)
        exit_code, _ = self.executor.exec_run(self.image, ["go", "fmt", str(dest)])
        if exit_code != 0:
            formatted = None
        else:
            _, output = self.executor.exec_run(self.image, ["cat", str(dest)])
            formatted = output.decode("utf-8")
            if compress:
                formatted = formatted.strip().replace("\n\n\n", "\n\n")

        return formatted


class NodeSnippet(Snippet):
    "A Node code snippet."

    @cached_property
    def output(self) -> NodeOutput:
        dest = Path("/tmp/main.js")
        self.executor.write(self.image, self.code, dest)
        logs = self.executor.exec_run_timed(self.image, ["node", str(dest)], environment={"NO_COLOR": "1"})

        return NodeOutput(logs)

    def format(self, compress: bool = False) -> str | None:
        dest = Path("/tmp/main.js")
        self.executor.write(self.image, self.code, dest)
        exit_code, _ = self.executor.exec_run(self.image, ["/bin/sh", "-c", f"npx prettier --write {dest}"])
        _, bytes_ = self.executor.exec_run(self.image, ["cat", str(dest)])
        if exit_code != 0:
            formatted = None
        else:
            formatted = bytes_.decode("utf-8")
            if compress:
                formatted = formatted.replace("\n\n\n", "\n\n")  # crude

        return formatted


class RubySnippet(Snippet):
    "A Ruby code snippet."

    @cached_property
    def output(self) -> RubyOutput:
        dest = Path("/tmp/main.rb")
        self.executor.write(self.image, self.code, dest)
        logs = self.executor.exec_run_timed(self.image, ["ruby", str(dest)])

        return RubyOutput(logs)

    def format(self, compress: bool = False) -> str | None:
        dest = Path("/tmp/main.rb")
        self.executor.write(self.image, self.code, dest)
        exit_code, _ = self.executor.exec_run(self.image, ["/bin/sh", "-c", f"gem install rubocop && rubocop -A {dest}"])
        _, bytes_ = self.executor.exec_run(self.image, ["cat", str(dest)])
        if exit_code != 0:
            formatted = None
        else:
            formatted = bytes_.decode("utf-8")
            if compress:
                formatted = formatted.replace("\n\n\n", "\n\n")  # crude

        return formatted


class RustSnippet(Snippet):
    "A Rust code snippet."

    @cached_property
    def output(self) -> RustOutput:
        dest = Path("/tmp/main.rs")
        self.executor.write(self.image, self.code, dest)
        self.executor.exec_run(self.image, ["rustc", "main.rs"], workdir="/tmp")
        logs = self.executor.exec_run_timed(self.image, ["/tmp/main"])
        return RustOutput(logs)

    def format(self, compress: bool = False) -> str | None:
        dest = Path("/tmp/main.rs")
        self.executor.exec_run(self.image, ["rustup", "component", "add", "rustfmt"])
        self.executor.write(self.image, self.code, dest)
        exit_code, _ = self.executor.exec_run(self.image, ["rustfmt", str(dest)])
        _, bytes_ = self.executor.exec_run(self.image, ["cat", str(dest)])
        if exit_code != 0:
            formatted = None
        else:
            formatted = bytes_.decode("utf-8")
            if compress:
                formatted = formatted.replace("\n\n\n", "\n\n")  # crude

        return formatted


atexit.register(DockerExecutor.cleanup)
