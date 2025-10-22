import os
import re
import subprocess
import sys
import tempfile
import time
from argparse import ArgumentParser
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Literal

import docker
from anki.storage import Collection


class Tag(Enum):
    "Question label, used to signal special treatment."

    NO_CHECK_FORMATTING = "no_check_formatting"
    NO_CHECK_OUTPUT = "no_check_output"


class Output:
    "A representation of a snippet's output."

    memory_address = re.compile(r"\b0x[0-9A-Fa-f]+\b")
    traceback_except_for_last_line = re.compile(
        r"Traceback \(most\ recent\ call\ last\):\n"  # start of traceback
        r"(\s.*\n)+",  # one or more lines starting with unicode whitespace and ending with newline
    )  # a traceback's last line doesn't start with whitespace so won't be captured
    location_info = re.compile(r'  File "<string>", line.*\n')

    def __init__(self, output: str) -> None:
        self.raw = output
        self.normalised = self.normalise(output)

    @classmethod
    def from_logs(cls, logs: dict[float, bytes]) -> "Output":
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

        return Output(output)

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


class Snippet:
    "A code snippet."

    def __init__(self, language: str, code: str):
        os.environ["DOCKER_HOST"] = f"unix://{Path.home()}/.docker/run/docker.sock"
        self.client = docker.from_env()
        self.language = language
        self.code = code

    @cached_property
    def output(self) -> Output:
        if self.language == "python":
            container = self.client.containers.run(
                "python:3.13",
                command=["python", "-u", "-c", self.code],
                detach=True,
            )
            logs = {}
            start = time.perf_counter()
            for line in container.logs(stream=True):  # blocks until \n
                now = time.perf_counter()
                delta = now - start
                logs[delta] = line

        elif self.language == "go":
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
                )
                container = self.client.containers.run(
                    "golang:1.25",
                    command=["./main"],
                    volumes={tmpdirname: {"bind": "/mnt/vol1", "mode": "rw"}},
                    working_dir="/mnt/vol1",
                    detach=True,
                )

                logs = {}
                start = time.perf_counter()
                for line in container.logs(stream=True):  # blocks until \n
                    now = time.perf_counter()
                    delta = now - start
                    logs[delta] = line

        container.remove()

        return Output.from_logs(logs)

    def format(self, compressed: bool = False) -> str | None:
        if self.language == "python":
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

        elif self.language == "go":
            with tempfile.TemporaryDirectory() as tmpdirname:
                with open(Path(tmpdirname) / "main.go", "w") as f:
                    f.write(self.code)
                try:
                    self.client.containers.run(
                        "golang:1.25",
                        command=["gofmt", "main.go"],
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


class Question:
    def __init__(self, id: str, language: str, code: str, expected_output: str, check_output: bool, check_formatting: bool):
        self.id = id
        self.language = language
        self.snippet = Snippet(language, code)
        self.output = Output(expected_output)
        self.check_output = check_output
        self.check_formatting = check_formatting

    def has_ok_output(self) -> bool:
        return self.snippet.output.normalised == self.output.normalised


def get_user_input() -> Literal["REPLACE", "IGNORE", "LEAVE"]:
    response = input("Enter 'r' to replace, 'i' to permanently ignore, anything else to leave as is: ")
    if response == "r":
        return "REPLACE"
    elif response == "i":
        return "IGNORE"
    else:
        return "LEAVE"


class AnkiQuestions:
    def __init__(self, tag: str):
        path = Path.home() / "Library/Application Support/Anki2/cosmo/collection.anki2"
        self.collection = Collection(str(path))

        self.failed: list[Question] = []
        self.fixed: list[Question] = []
        self.ignored: list[Question] = []

        print(f"Looking for notes tagged '{tag}'.")
        note_ids = self.collection.find_notes("")
        notes = [self.collection.get_note(id) for id in note_ids]
        self.notes = [note for note in notes if tag in note.tags]
        print(f"Found {len(self.notes)} notes")

        questions: list[Question] = []
        for note in self.notes:
            code, output, _, context = note.fields
            language = "go" if context.startswith("Go") else "python"
            code = self.pre_process(code)
            code = self.html_to_plain(code)
            output = self.html_to_plain(output)
            check_output = Tag.NO_CHECK_OUTPUT.value not in note.tags
            check_format = Tag.NO_CHECK_FORMATTING.value not in note.tags
            id = note.id
            questions.append(Question(str(id), language, code, output, check_output, check_format))
        self.questions = questions

    def html_to_plain(self, html: str) -> str:
        """
        Replace html tags or entity names with text equivalents.

        Anki note fields are html.
        Code output notes' output field should have minimal markup.
        Replace this markup with text equivalents, e.g. <br> -> \\n.
        """
        # quotation mark and apostrophe are html reserved characters
        # but in my notes we use " and ' seemingly without issue, not &quot; or &apos;
        # so we don't need to replace those
        # also, some &nbsp; linger, so just clean them ad hoc here
        # TODO: think about where these cleaning methods live
        return html.replace("<br>", "\n").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ").replace("&amp;", "&")

    def escape_html(self, plain: str) -> str:
        return plain.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def pre_process(self, code: str) -> str:
        return (
            code.removeprefix('<pre><code class="lang-python">').removeprefix('<pre><code class="lang-go">').removesuffix("</code></pre>")
        )

    def post_process(self, code: str, question: Question) -> str:
        return f'<pre><code class="lang-{question.language}">{code}</code></pre>'

    def fix_output(self, question: Question) -> None:
        "Write the normalised, marked up output of the given question's snippet to the anki database."

        note = self.collection.get_note(int(question.id))  # type: ignore[arg-type]  # TODO: more systematic type conversion
        output = question.snippet.output
        note_output = self.escape_html(output.normalised)
        note.fields[1] = note_output
        self.collection.update_note(note)
        self.fixed.append(question)

    def fix_formatting(self, question: Question) -> None:
        "Write a formatted version of the given question's snippet to the anki database."
        note = self.collection.get_note(int(question.id))  # type: ignore[arg-type]  # TODO: more systematic type conversion
        formatted = question.snippet.format(compressed=True)  # compressed looks better in anki notes
        assert formatted is not None  # we only fix if no error when formatting
        formatted = self.escape_html(formatted)
        formatted = self.post_process(formatted, question)
        note.fields[0] = formatted
        self.collection.update_note(note)
        self.fixed.append(question)

    def no_check_formatting(self, question: Question) -> None:
        """
        Add a tag to the given question's note, indicating this note should be ignored
        when checking formatting, and write it to the anki database.
        """
        note = self.collection.get_note(int(question.id))  # type: ignore[arg-type]  # TODO: more systematic type conversion
        note.tags.append(Tag.NO_CHECK_FORMATTING.value)
        self.collection.update_note(note)
        self.ignored.append(question)

    def no_check_output(self, question: Question) -> None:
        """
        Add a tag to the given question's note, indicating this note should be ignored
        when checking outputs, and write it to the anki database.
        """
        note = self.collection.get_note(int(question.id))  # type: ignore[arg-type]  # TODO: more systematic type conversion
        note.tags.append(Tag.NO_CHECK_OUTPUT.value)
        self.collection.update_note(note)
        self.ignored.append(question)

    def check_output(self, interactive: bool) -> None:
        questions_to_check = [question for question in self.questions if question.check_output]
        print("----------")

        for question in questions_to_check:
            if not question.has_ok_output():
                print(f"\N{CROSS MARK} Unexpected output for {question.id}.", end="\n\n")
                print("Code:")
                colour_print(question.snippet.code, colour="cyan", end="\n\n")
                print("Output (normalised):")
                colour_print(question.snippet.output.normalised, colour="green", end="\n\n")
                print("Given (normalised):")
                colour_print(question.output.normalised, colour="red", end="\n\n")
                self.failed.append(question)
                if interactive:
                    response = get_user_input()
                    if response == "REPLACE":
                        self.fix_output(question)
                        print("\N{SPARKLES} Replaced.", end="\n\n")
                    elif response == "IGNORE":
                        self.no_check_output(question)
                        print("\N{SEE-NO-EVIL MONKEY} Permanently ignored.", end="\n\n")
                    else:
                        print("\N{FACE WITHOUT MOUTH} Leaving as is.", end="\n\n")
                print("----------", end="\n\n")

    def check_formatting(self, interactive: bool) -> None:
        questions_to_check = [question for question in self.questions if question.check_formatting]
        print("----------")

        for question in questions_to_check:
            formatted = question.snippet.format(compressed=True)
            if formatted is None:
                # error when trying to format snippet
                # treat as non-fixable failure
                print(f"\N{CROSS MARK} Error when formatting {question.id}.", end="\n\n")
                print("Given:")
                colour_print(question.snippet.code, colour="red", end="\n\n")
                self.failed.append(question)
                print("----------", end="\n\n")
            elif formatted != question.snippet.code:
                print(f"\N{CROSS MARK} Unexpected formatting for {question.id}.", end="\n\n")
                print("Formatted:")
                colour_print(formatted, colour="green", end="\n\n")
                print("Given:")
                colour_print(question.snippet.code, colour="red", end="\n\n")
                self.failed.append(question)
                if interactive:
                    response = get_user_input()
                    if response == "REPLACE":
                        self.fix_formatting(question)
                        print("\N{SPARKLES} Replaced.", end="\n\n")
                    elif response == "IGNORE":
                        self.no_check_formatting(question)
                        print("\N{SEE-NO-EVIL MONKEY} Permanently ignored.", end="\n\n")
                    else:
                        print("\N{FACE WITHOUT MOUTH} Leaving as is.", end="\n\n")
                print("----------", end="\n\n")


def check_output(args) -> int:
    questions = AnkiQuestions(tag=args.tag)
    questions.check_output(args.interactive)
    if questions.failed:
        print(
            f"{len(questions.failed)} questions had unexpected output "
            "("
            f"{len(questions.fixed)} fixed, "
            f"{len(questions.ignored)} permanently ignored, "
            f"{len(questions.failed) - len(questions.fixed) - len(questions.ignored)} left"
            ")"
        )
        return 1
    else:
        print("All good.")
        return 0


def check_formatting(args) -> int:
    questions = AnkiQuestions(tag=args.tag)
    questions.check_formatting(args.interactive)
    if questions.failed:
        print(
            f"{len(questions.failed)} questions had unexpected formatting "
            "("
            f"{len(questions.fixed)} fixed, "
            f"{len(questions.ignored)} permanently ignored, "
            f"{len(questions.failed) - len(questions.fixed) - len(questions.ignored)} left"
            ")"
        )
        return 1
    else:
        print("All good.")
        return 0


def colour_print(string: str, colour: str, **kwargs) -> None:
    if colour == "green":
        print("\033[92m" + string + "\033[0m", **kwargs)
    elif colour == "red":
        print("\033[91m" + string + "\033[0m", **kwargs)
    elif colour == "cyan":
        print("\033[96m" + string + "\033[0m", **kwargs)
    else:
        raise ValueError(f"unsupported colour: {colour}")


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("tag")
    subparsers = parser.add_subparsers(required=True)

    check_output_parser = subparsers.add_parser("check-output", help="check snippet output")
    check_output_parser.add_argument(
        "-i", "--interactive", action="store_true", help="get user input for whether to fix, ignore in future, or leave as is"
    )
    check_output_parser.set_defaults(func=check_output)

    check_formatting_parser = subparsers.add_parser("check-formatting", help="check snippet formatting")
    check_formatting_parser.add_argument(
        "--interactive", action="store_true", help="get user input for whether to fix, ignore in future, or leave as is"
    )
    check_formatting_parser.set_defaults(func=check_formatting)

    args = parser.parse_args()

    exit_code = args.func(args)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
