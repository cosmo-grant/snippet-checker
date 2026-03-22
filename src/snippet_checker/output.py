from __future__ import annotations

import re
from abc import ABC, abstractmethod
from itertools import count


class Output(ABC):
    def __init__(self, logs: list[tuple[float, bytes]]):
        output = self._to_string(logs)
        self.raw = output

    @abstractmethod
    def normalise(self, output: str, output_verbosity: int) -> str:
        raise NotImplementedError

    def _to_string(self, logs: list[tuple[float, bytes]]) -> str:
        output = b""
        for delta, char in logs:
            rounded_delta = round(delta)
            if rounded_delta == 0:
                output += char
            else:
                output += bytes(f"<~{rounded_delta}s>\n", "utf-8")
                output += char

        return output.decode("utf-8").replace("\r\n", "\n")


class PythonOutput(Output):
    "A representation of a Python snippet's output."

    memory_address = re.compile(r"\b0x[0-9A-Fa-f]+\b")

    traceback_except_for_last_line = re.compile(
        r"Traceback \(most\ recent\ call\ last\):\n"  # start of traceback
        r"(\s.*\n)+",  # one or more lines starting with unicode whitespace and ending with newline
    )  # a traceback's last line doesn't start with whitespace so won't be captured

    # e.g. syntax errors include location info
    location_info = re.compile(
        r'  File "[^"]*", line.*\n'  # file and line number
        r".*\n"  # line
        r".*\n"  # carets
    )

    @classmethod
    def normalise(cls, output: str, output_verbosity: int) -> str:
        normalised = cls.normalise_memory_addresses(output)
        normalised = cls.normalise_traceback(normalised, output_verbosity)
        normalised = cls.normalise_location_info(normalised, output_verbosity)

        return normalised

    @classmethod
    def normalise_memory_addresses(cls, output: str) -> str:
        addresses = (hex(i) for i in count(0x100, 0x100))  # nice-looking, easily distinguished fake memory addresses
        seen = set()
        normalised = output
        for match in re.finditer(cls.memory_address, output):
            address = match.group()
            if address in seen:
                continue
            seen.add(address)
            normalised = normalised.replace(address, next(addresses))

        return normalised

    @classmethod
    def normalise_traceback(cls, output: str, output_verbosity: int) -> str:
        if output_verbosity == 0:
            normalised = re.sub(cls.traceback_except_for_last_line, "", output)
        elif output_verbosity == 1:
            normalised = re.sub(cls.traceback_except_for_last_line, "Traceback (most recent call last):\n  ...\n", output)
        elif output_verbosity == 2:
            normalised = output

        return normalised

    @classmethod
    def normalise_location_info(cls, output: str, output_verbosity: int) -> str:
        normalised = re.sub(cls.location_info, "", output) if output_verbosity < 2 else output
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

    @classmethod
    def normalise_memory_addresses(cls, output: str) -> str:
        addresses = (hex(i) for i in count(0x100, 0x100))  # nice-looking, easily distinguished fake memory addresses
        seen = set()
        normalised = output
        for match in re.finditer(cls.memory_address, output):
            address = match.group()
            if address in seen:
                continue
            seen.add(address)
            normalised = normalised.replace(address, next(addresses))

        return normalised

    @classmethod
    def normalise(cls, output: str, output_verbosity: int) -> str:
        normalised = cls.normalise_memory_addresses(output)
        normalised = cls.normalise_panic(normalised)
        normalised = cls.normalise_stack_overflow(normalised)

        return normalised

    @classmethod
    def normalise_panic(cls, output: str) -> str:
        normalised = re.sub(cls.panic, r"\1", output)
        return normalised

    @classmethod
    def normalise_stack_overflow(cls, output: str) -> str:
        normalised = re.sub(cls.stack_overflow, r"\1", output)
        return normalised


class NodeOutput(Output):
    "A representation of a Node snippet's output."

    traceback = re.compile(
        r"(?P<location>/tmp/main.js:\d+\n)"
        r"(?P<offending_line>.*\n)"
        r"(?P<pointer>.*\n)"
        r"\n"  # empty line
        r"(?P<key_line>.*\n)"
        r"(.*\n)*"  # stack trace and empty line
        r"(?P<version>Node.js v.*\n)"  # version
    )

    @classmethod
    def normalise(cls, output: str, output_verbosity: int) -> str:
        normalised = cls.normalise_traceback(output, output_verbosity)
        return normalised

    @classmethod
    def normalise_traceback(cls, output: str, output_verbosity: int) -> str:
        if output_verbosity == 0:
            normalised = re.sub(cls.traceback, r"\g<key_line>", output)
        elif output_verbosity == 1:
            pass
        elif output_verbosity == 2:
            normalised = output

        return normalised


class RubyOutput(Output):
    "A representation of a Ruby snippet's output."

    @classmethod
    def normalise(cls, output: str, output_verbosity: int) -> str:
        return output  # TODO:


class RustOutput(Output):
    "A representation of a Rust snippet's output."

    @classmethod
    def normalise(cls, output: str, output_verbosity: int) -> str:
        return output  # TODO:
