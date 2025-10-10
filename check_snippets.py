import os
import subprocess
import time
from pathlib import Path

import docker

import re


def canonicalize_memory_addresses(output: str) -> str:
    memory_address = re.compile(r"\b0x[0-9A-Fa-f]+\b")
    seen = set()
    canonicalized = output
    for match in re.finditer(memory_address, output):
        address = match.group()
        if address in seen:
            continue
        seen.add(address)
        canonicalized = canonicalized.replace(address, f"0x{len(seen)}")

    return canonicalized


class Output:
    def __init__(self, raw_output: dict[float, bytes]):
        self.raw_output = raw_output

        output: dict[int, str] = {}
        # insertion order should be ascending t, but let's be clear and cautious
        for t in sorted(raw_output):
            rounded_t = round(t)
            line = raw_output[t].decode("utf-8")
            output[rounded_t] = output.get(rounded_t, "") + line
        self.output = output

    def __str__(self) -> str:
        result = ""
        previous = 0
        for t, line in self.output.items():
            delta = t - previous
            result += f"<~{delta}s>\n"
            result += line
            previous = t
        result = result.removeprefix("<~0s>\n")
        return result


class Snippet:
    def __init__(self, code: str, python_version: str = "3.13"):
        os.environ["DOCKER_HOST"] = f"unix://{Path.home()}/.docker/run/docker.sock"
        self.client = docker.from_env()
        self.code = code
        self.python_version = python_version

    def run(self) -> dict[int, str]:
        container = self.client.containers.run(
            f"python:{self.python_version}",
            command=["python", "-u", "-c", self.code],
            detach=True,
        )

        raw_output = {}
        start = time.perf_counter()
        for line in container.logs(stream=True):  # blocks until \n
            now = time.perf_counter()
            delta = now - start
            raw_output[delta] = line
        return Output(raw_output)

    def format(self) -> str:
        called_process = subprocess.run(
            ["ruff", "format", "-"],
            check=True,
            input=self.code,
            stdout=subprocess.PIPE,
            text=True,
        )
        return called_process.stdout


def main():
    pass


if __name__ == "__main__":
    main()
