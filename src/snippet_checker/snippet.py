from __future__ import annotations

import io
import platform
import subprocess
import tarfile
import time
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import ClassVar

import docker

from .output import GoOutput, Output, PythonOutput


class Snippet(ABC):
    """Abstract base class for code snippets in some language."""

    client = (
        docker.from_env()
        if platform.system() == "Linux"
        else docker.from_env(environment={"DOCKER_HOST": f"unix://{Path.home()}/.docker/run/docker.sock"})
    )
    _container_pool: ClassVar[dict[str, docker.models.containers.Container]] = {}

    @classmethod
    def _get_container(cls, image: str) -> docker.models.containers.Container:
        """Get or create a long-running container for the given image."""
        if image not in cls._container_pool:
            cls._container_pool[image] = cls.client.containers.run(
                image,
                ["tail", "-f", "/dev/null"],
                detach=True,
            )
        return cls._container_pool[image]

    @classmethod
    def _copy_to_container(
        cls,
        container: docker.models.containers.Container,
        content: str,
        dest: Path,
    ) -> None:
        """
        Copy a string as a file into a container.
        Overwrites any existing file at the destination.
        """
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w") as tar:
            file_bytes = content.encode("utf-8")
            tarinfo = tarfile.TarInfo(name=dest.name)
            tarinfo.size = len(file_bytes)
            tar.addfile(tarinfo, io.BytesIO(file_bytes))
        data.seek(0)

        succeeded = container.put_archive(str(dest.parent), data)
        assert succeeded

    @classmethod
    def cleanup(cls) -> None:
        """Remove all containers in the pool."""
        for container in cls._container_pool.values():
            container.remove(force=True)
        cls._container_pool.clear()

    def __init__(self, code: str, image: str):
        self.code = code
        self.image = image

    @cached_property
    @abstractmethod
    def output(self) -> Output:
        raise NotImplementedError

    @abstractmethod
    def format(self, compressed: bool = False) -> str | None:
        raise NotImplementedError


class PythonSnippet(Snippet):
    "A Python code snippet."

    @cached_property
    def output(self) -> PythonOutput:
        container = self._get_container(self.image)
        self._copy_to_container(container, self.code, Path("/tmp/main.py"))

        logs: list[tuple[float, bytes]] = []
        previous = time.perf_counter()

        _, output_stream = container.exec_run(
            ["python", "/tmp/main.py"],
            tty=True,
            stream=True,
            environment={
                "NO_COLOR": "true",
                "PYTHONWARNINGS": "ignore",
            },
        )

        for chunk in output_stream:
            now = time.perf_counter()
            logs.append((now - previous, chunk))
            previous = now

        return PythonOutput.from_logs(logs)

    def format(self, compressed: bool = False) -> str | None:
        called_process = subprocess.run(
            ["ruff", "format", "-"],  # TODO: should be able to control config
            input=self.code,
            capture_output=True,
            text=True,
        )
        if called_process.returncode == 0:
            formatted = called_process.stdout
            if compressed:
                formatted = formatted.strip().replace("\n\n\n", "\n\n")  # crude
        else:
            formatted = None

        return formatted


class GoSnippet(Snippet):
    "A Go code snippet."

    @cached_property
    def output(self) -> GoOutput:
        container = self._get_container(self.image)
        self._copy_to_container(container, self.code, Path("/tmp/main.go"))

        exit_code, _ = container.exec_run(["go", "build", "/tmp/main.go"], workdir="/tmp")
        assert exit_code == 0

        logs: list[tuple[float, bytes]] = []
        previous = time.perf_counter()
        _, output_stream = container.exec_run(["/tmp/main"], tty=True, stream=True)
        for chunk in output_stream:
            now = time.perf_counter()
            logs.append((now - previous, chunk))
            previous = now

        return GoOutput.from_logs(logs)

    def format(self, compressed: bool = False) -> str | None:
        container = self._get_container(self.image)
        self._copy_to_container(container, self.code, Path("/tmp/main.go"))
        exit_code, _ = container.exec_run(["go", "fmt", "/tmp/main.go"])
        if exit_code != 0:
            formatted = None
        else:
            _, output = container.exec_run(["cat", "/tmp/main.go"])
            formatted = output.decode("utf-8")
            if compressed:
                formatted = formatted.strip().replace("\n\n\n", "\n\n")

        return formatted
