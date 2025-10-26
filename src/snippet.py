from __future__ import annotations

import os
import subprocess
import tempfile
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path

import docker

from output import GoOutput, Output, PythonOutput


class Snippet(ABC):
    """Abstract base class for code snippets in some language."""

    def __init__(self, code: str):
        os.environ["DOCKER_HOST"] = f"unix://{Path.home()}/.docker/run/docker.sock"
        self.client = docker.from_env()
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

    # FIXME: deal with exceptions
    @cached_property
    def output(self) -> PythonOutput:
        result = self.client.containers.run(
            "python:3.13",
            command=["python", "-c", self.code],
            auto_remove=True,
        )

        return PythonOutput(result.decode("utf-8"))

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
            result = self.client.containers.run(
                "golang:1.25",
                command=["go", "run", "main.go"],
                volumes={tmpdirname: {"bind": "/mnt/vol1", "mode": "rw"}},
                working_dir="/mnt/vol1",
                auto_remove=True,
            )

            return GoOutput(result.decode("utf-8"))

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
                    auto_remove=True,
                )
            except docker.errors.ContainerError:
                formatted = None
            else:
                with open(Path(tmpdirname) / "main.go") as f:
                    formatted = f.read()
                if compressed:
                    formatted = formatted.strip().replace("\n\n\n", "\n\n")

        return formatted
