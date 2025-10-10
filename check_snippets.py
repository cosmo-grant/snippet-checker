import os
import time
from pathlib import Path

import docker


class Output:
    def __init__(self, output: dict[int, str]):
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

        output = {}
        start = time.perf_counter()
        for line in container.logs(stream=True):  # blocks until \n
            now = time.perf_counter()
            delta = round(now - start)
            output[delta] = output.get(delta, "") + line.decode("utf-8")
        return Output(output)


def main():
    pass


if __name__ == "__main__":
    main()
