from __future__ import annotations

import re
from abc import ABC, abstractmethod
from itertools import count
from typing import TypeVar

LanguageOutput = TypeVar("LanguageOutput", bound="Output")


class Output(ABC):
    def __init__(self, output: str) -> None:
        self.raw = output
        self.normalised = self.normalise(output)

    @abstractmethod
    def normalise(self, output: str) -> str:
        raise NotImplementedError

    @classmethod
    def from_logs(cls: type[LanguageOutput], logs: list[tuple[float, bytes]]) -> LanguageOutput:
        "Alternative constructor, creating an output from timed docker logs."

        output = b""
        for delta, char in logs:
            rounded_delta = round(delta)
            if rounded_delta == 0:
                output += char
            else:
                output += bytes(f"<~{rounded_delta}s>\n", "utf-8")
                output += char

        decoded_output = output.decode("utf-8")
        decoded_output = decoded_output.replace("\r\n", "\n")
        return cls(decoded_output)


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

    def normalise(self, output: str) -> str:
        output = self.normalise_memory_addresses(output)
        output = self.normalise_traceback(output)
        output = self.normalise_location_info(output)

        return output

    def normalise_memory_addresses(self, output: str) -> str:
        addresses = (hex(i) for i in count(0x100, 0x100))  # nice-looking, easily distinguished fake memory addresses
        seen = set()
        normalised = output
        for match in re.finditer(self.memory_address, output):
            address = match.group()
            if address in seen:
                continue
            seen.add(address)
            normalised = normalised.replace(address, next(addresses))

        return normalised

    def normalise_traceback(self, output: str) -> str:
        normalised = re.sub(self.traceback_except_for_last_line, "Traceback (most recent call last):\n  ...\n", output)

        return normalised

    def normalise_location_info(self, output: str) -> str:
        normalised = re.sub(self.location_info, "", output)
        return normalised


class GoOutput(Output):
    "A representation of a Go snippet's output."

    memory_address = re.compile(r"\b0x[0-9A-Fa-f]+\b")
    panic = re.compile(
        r"(panic: .*?\n)"  # the line we want
        r".*",  # the rest
        re.DOTALL,
    )
    stack_overflow = re.compile(
        r"runtime: goroutine stack exceeds.*limit\n"
        r"runtime:.*\n"
        r"(fatal error: stack overflow\n)"  # the line we want
        r".*",  # the rest
        re.DOTALL,
    )

    def __init__(self, output: str) -> None:
        super().__init__(output)

    def normalise_memory_addresses(self, output: str) -> str:
        addresses = (hex(i) for i in count(0x100, 0x100))  # nice-looking, easily distinguished fake memory addresses
        seen = set()
        normalised = output
        for match in re.finditer(self.memory_address, output):
            address = match.group()
            if address in seen:
                continue
            seen.add(address)
            normalised = normalised.replace(address, next(addresses))

        return normalised

    def normalise(self, output: str) -> str:
        output = self.normalise_memory_addresses(output)
        output = self.normalise_panic(output)
        output = self.normalise_stack_overflow(output)

        return output

    def normalise_panic(self, output: str) -> str:
        normalised = re.sub(self.panic, r"\1", output)
        return normalised

    def normalise_stack_overflow(self, output: str) -> str:
        normalised = re.sub(self.stack_overflow, r"\1", output)
        return normalised
