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
    def from_logs(cls: type[LanguageOutput], logs: dict[float, bytes]) -> LanguageOutput:
        "Alternative constructor, creating an output from timed reads of an output file."

        rounded_logs: dict[int, str] = {}
        # insertion order should be ascending t, but let's be clear and cautious
        for t in sorted(logs):
            rounded_t = round(t)
            chunk = logs[t]
            rounded_logs[rounded_t] = rounded_logs.get(rounded_t, "") + chunk

        rounded_logs = {k: v for k, v in rounded_logs.items() if v}


        output = ""
        previous = 0
        for t, chunk in rounded_logs.items():
            delta = t - previous
            output += f"<~{delta}s>\n"
            output += chunk
            previous = t
        output = output.removeprefix("<~0s>\n")

        return cls(output)

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
        normalised = re.sub(self.traceback_except_for_last_line, "", output)

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
