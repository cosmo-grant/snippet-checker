from __future__ import annotations

import re
from itertools import count


class OutputNormaliser:
    """
    Normalises code snippet outputs in various languages (e.g. prunes tracebacks, canonicalises memory addresses).

    Implementation note: instead of detecting the runtime, and running only normalisations
    designed for it (e.g. Python traceback pruning for Python; Node traceback pruning for Node) I just run
    all normalisations every time, trusting that normalisations designed for one runtime won't collide with
    normalisations designed for another (e.g. the Python traceback normaliser will never modify a Node snippet
    output.
    """

    memory_address = re.compile(r"\b0x[0-9A-Fa-f]+\b")

    python_traceback_except_for_last_line = re.compile(
        r"Traceback \(most\ recent\ call\ last\):\n"  # start of traceback
        r"(\s.*\n)+",  # one or more lines starting with unicode whitespace and ending with newline
    )  # a traceback's last line doesn't start with whitespace so won't be captured

    # e.g. syntax errors include location info
    python_location_info = re.compile(
        r'  File "[^"]*", line.*\n'  # file and line number
        r".*\n"  # line
        r".*\n"  # carets
    )

    python_errno = re.compile(r"\[Errno \d+\]")

    go_panic = re.compile(
        r"(panic: .*?\n)"  # the line we want
        r".*",  # the rest
        re.DOTALL,
    )
    go_stack_overflow = re.compile(
        r"runtime: goroutine stack exceeds.*limit\n"
        r"runtime:.*\n"
        r"(fatal error: stack overflow\n)"  # the line we want
        r".*",  # the rest
        re.DOTALL,
    )

    node_traceback = re.compile(
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
        normalised = cls.normalise_memory_addresses(output)

        normalised = cls.normalise_python_traceback(normalised, output_verbosity)
        normalised = cls.normalise_python_location_info(normalised, output_verbosity)
        normalised = cls.normalise_python_errnos(normalised)

        normalised = cls.normalise_go_panic(normalised)
        normalised = cls.normalise_go_stack_overflow(normalised)

        normalised = cls.normalise_node_traceback(normalised, output_verbosity)

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
    def normalise_python_traceback(cls, output: str, output_verbosity: int) -> str:
        if output_verbosity == 0:
            normalised = re.sub(cls.python_traceback_except_for_last_line, "", output)
        elif output_verbosity == 1:
            normalised = re.sub(cls.python_traceback_except_for_last_line, "Traceback (most recent call last):\n  ...\n", output)
        elif output_verbosity == 2:
            normalised = output

        return normalised

    @classmethod
    def normalise_python_location_info(cls, output: str, output_verbosity: int) -> str:
        normalised = re.sub(cls.python_location_info, "", output) if output_verbosity < 2 else output
        return normalised

    @classmethod
    def normalise_python_errnos(cls, output: str) -> str:
        normalised = re.sub(cls.python_errno, "[Errno NN]", output)
        return normalised

    @classmethod
    def normalise_go_panic(cls, output: str) -> str:
        normalised = re.sub(cls.go_panic, r"\1", output)
        return normalised

    @classmethod
    def normalise_go_stack_overflow(cls, output: str) -> str:
        normalised = re.sub(cls.go_stack_overflow, r"\1", output)
        return normalised

    @classmethod
    def normalise_node_traceback(cls, output: str, output_verbosity: int) -> str:
        if output_verbosity == 0 or output_verbosity == 1:  # TODO:
            normalised = re.sub(cls.node_traceback, r"\g<key_line>", output)
        elif output_verbosity == 2:
            normalised = output

        return normalised
