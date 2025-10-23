from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import TypeVar

LanguageOutput = TypeVar("LanguageOutput", bound="Output")


class Output(ABC):
    def __init__(self, output: str) -> None:
        self.raw = output
        self.normalised = self.normalise(output)

    @classmethod
    @abstractmethod
    def from_logs(cls: type[LanguageOutput], logs: dict[float, bytes]) -> LanguageOutput:
        "Alternative constructor, creating an output from timed docker logs."

        rounded_logs: dict[int, str] = {}
        # insertion order should be ascending t, but let's be clear and cautious
        for t in sorted(logs):
            rounded_t = round(t)
            line = logs[t].decode("utf-8")
            rounded_logs[rounded_t] = rounded_logs.get(rounded_t, "") + line

        output = ""
        previous = 0
        for t, line in rounded_logs.items():
            delta = t - previous
            output += f"<~{delta}s>\n"
            output += line
            previous = t
        output = output.removeprefix("<~0s>\n")

        return cls(output)

    @abstractmethod
    def normalise(self, output: str) -> str:
        raise NotImplementedError


class PythonOutput(Output):
    "A representation of a Python snippet's output."

    memory_address = re.compile(r"\b0x[0-9A-Fa-f]+\b")
    traceback_except_for_last_line = re.compile(
        r"Traceback \(most\ recent\ call\ last\):\n"  # start of traceback
        r"(\s.*\n)+",  # one or more lines starting with unicode whitespace and ending with newline
    )  # a traceback's last line doesn't start with whitespace so won't be captured
    location_info = re.compile(r'  File "<string>", line.*\n')

    def __init__(self, output: str) -> None:
        super().__init__(output)

    @classmethod
    def from_logs(cls, logs: dict[float, bytes]) -> PythonOutput:
        return super().from_logs(logs)

    def normalise(self, output: str) -> str:
        output = output.rstrip("\n")  # TODO: do we want this? it looks nicer in anki notes, but the output may actually end in a newline
        output = self.normalise_memory_addresses(output)
        output = self.normalise_traceback(output)
        output = self.normalise_location_info(output)
        return output

    def normalise_memory_addresses(self, output: str) -> str:
        seen = set()
        normalised = output
        for match in re.finditer(self.memory_address, output):
            address = match.group()
            if address in seen:
                continue
            seen.add(address)
            normalised = normalised.replace(address, f"0x{len(seen)}")

        return normalised

    def normalise_traceback(self, output: str) -> str:
        normalised = re.sub(self.traceback_except_for_last_line, "", output)

        return normalised

    def normalise_location_info(self, output: str) -> str:
        normalised = re.sub(self.location_info, "", output)
        return normalised


class GoOutput(Output):
    "A representation of a Go snippet's output."

    def __init__(self, output: str) -> None:
        super().__init__(output)

    @classmethod
    def from_logs(cls, logs: dict[float, bytes]) -> GoOutput:
        return super().from_logs(logs)

    def normalise(self, output: str) -> str:
        output = output.rstrip("\n")  # TODO: do we want this? it looks nicer in anki notes, but the output may actually end in a newline
        return output
