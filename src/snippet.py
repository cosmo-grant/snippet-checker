from __future__ import annotations

import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path

import docker

from .output import GoOutput, Output, PythonOutput


class Snippet(ABC):
    """Abstract base class for code snippets in some language."""

    client = docker.from_env(environment={"DOCKER_HOST": f"unix://{Path.home()}/.docker/run/docker.sock"})

    def __init__(self, code: str):
        self.code = code

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
        logs: list[tuple[float, bytes]] = []
        try:
            container = self.client.containers.run(
                "python:3.13",
                command=["python", "-c", self.code],
                environment={"NO_COLOR": "true"},  # any non-empty string will do; prevents ansi sequences
                detach=True,  # needed to get timing; cannot auto_remove in consequence
                tty=True,
            )
            previous = time.perf_counter()
            for char in container.logs(stream=True):
                now = time.perf_counter()
                logs.append((now - previous, char))
                previous = now
        finally:
            container.remove()

        return PythonOutput.from_logs(logs)

    def format(self, compressed: bool = False) -> str | None:
        called_process = subprocess.run(
            ["ruff", "format", "-"],
            input=self.code,
            capture_output=True,
            text=True,
        )
        if called_process.returncode == 0:
            formatted = called_process.stdout
            if compressed:
                formatted = formatted.strip().replace("\n\n\n", "\n\n")
        else:
            formatted = None

        return formatted


class GoSnippet(Snippet):
    "A Go code snippet."

    @cached_property
    def output(self) -> GoOutput:
        with tempfile.TemporaryDirectory() as tmpdirname:
            with open(Path(tmpdirname) / "main.go", "w") as f:
                f.write(self.code)
            # `go run` takes a while, producing a spurious <~2s> at start of the output
            # so `go build` first, blocking until done, then execute
            self.client.containers.run(
                "golang:1.25",
                command=["go", "build", "main.go"],
                volumes={tmpdirname: {"bind": "/mnt/vol1", "mode": "rw"}},
                working_dir="/mnt/vol1",
                auto_remove=True,
            )
            try:
                container = self.client.containers.run(
                    "golang:1.25",
                    command=["./main"],
                    volumes={tmpdirname: {"bind": "/mnt/vol1", "mode": "rw"}},
                    working_dir="/mnt/vol1",
                    detach=True,
                )

                logs: list[tuple[float, bytes]] = []
                previous = time.perf_counter()
                for char in container.logs(stream=True):
                    now = time.perf_counter()
                    logs.append((now - previous, char))
                    previous = now
            finally:
                container.remove()

        return GoOutput.from_logs(logs)

    def format(self, compressed: bool = False) -> str | None:
        with tempfile.TemporaryDirectory() as tmpdirname:
            with open(Path(tmpdirname) / "main.go", "w") as f:
                f.write(self.code)
            try:
                self.client.containers.run(
                    "golang:1.25",
                    command=["go", "fmt", "main.go"],
                    volumes={tmpdirname: {"bind": "/mnt/vol1", "mode": "rw"}},
                    working_dir="/mnt/vol1",
                )
            except docker.errors.ContainerError:
                formatted = None
            else:
                with open(Path(tmpdirname) / "main.go") as f:
                    formatted = f.read()
                if compressed:
                    formatted = formatted.strip().replace("\n\n\n", "\n\n")

        return formatted
