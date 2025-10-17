import os
import re
import subprocess
import sys
import time
from argparse import ArgumentParser
from functools import cached_property
from pathlib import Path

import docker
from anki.storage import Collection


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
    "A python code snippet."

    def __init__(self, code: str, python_version: str = "3.13"):
        os.environ["DOCKER_HOST"] = f"unix://{Path.home()}/.docker/run/docker.sock"
        self.client = docker.from_env()
        self.code = code
        self.python_version = python_version

    @cached_property
    def output(self) -> Output:
        container = self.client.containers.run(
            f"python:{self.python_version}",
            command=["python", "-u", "-c", self.code],
            detach=True,
            auto_remove=True,
        )

        logs = {}
        start = time.perf_counter()
        for line in container.logs(stream=True):  # blocks until \n
            now = time.perf_counter()
            delta = now - start
            logs[delta] = line

        return Output.from_logs(logs)

    def format(self, compressed: bool = False) -> str | None:
        called_process = subprocess.run(
            ["ruff", "format", "-"],
            input=self.code,
            stdout=subprocess.PIPE,
            text=True,
        )
        if called_process.returncode == 0:
            formatted = called_process.stdout
            if compressed:
                formatted = formatted.strip().replace("\n\n\n", "\n\n")
        else:
            formatted = None

        return formatted


class Question:
    def __init__(self, id: str, code: str, expected_output: str):
        self.id = id
        self.snippet = Snippet(code)
        self.output = Output(expected_output)

    def has_ok_output(self) -> bool:
        return self.snippet.output.normalised == self.output.normalised


def should_fix() -> bool:
    response = input("Enter 'y' to overwrite: ")
    return response == "y"


class AnkiQuestions:
    def __init__(self, tag: str):
        path = Path.home() / "Library/Application Support/Anki2/cosmo/collection.anki2"
        self.collection = Collection(str(path))

        self.failed: list[Question] = []
        self.fixed: list[Question] = []

        print(f"Looking for notes tagged '{tag}'.")
        note_ids = self.collection.find_notes("")
        notes = [self.collection.get_note(id) for id in note_ids]
        self.notes = [note for note in notes if tag in note.tags]
        print(f"Found {len(self.notes)} notes")

        questions: list[Question] = []
        for note in self.notes:
            code, output, _, _ = note.fields
            code = self.pre_process(code)
            code = self.html_to_plain(code)
            output = self.html_to_plain(output)
            id = note.id
            questions.append(Question(str(id), code, output))
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
        return code.removeprefix('<pre><code class="lang-python">').removesuffix("</code></pre>")

    def post_process(self, code: str) -> str:
        return f'<pre><code class="lang-python">{code}</code></pre>'

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
        formatted = self.escape_html(formatted)
        formatted = self.post_process(formatted)
        note.fields[0] = formatted
        self.collection.update_note(note)
        self.fixed.append(question)

    def check_output(self, offer_fix: bool) -> None:
        for question in self.questions:
            if not question.has_ok_output():
                print(f"\N{CROSS MARK} unexpected output for {question.id}")
                print("Code:")
                colour_print(question.snippet.code, colour="cyan")
                print("Output (normalised):")
                colour_print(question.snippet.output.normalised, colour="green")
                print("Given (normalised):")
                colour_print(question.output.normalised, colour="red")
                self.failed.append(question)
                if offer_fix:
                    response = should_fix()
                    if response:
                        self.fix_output(question)
                        print("\N{SPARKLES} Fixed.", end="\n\n")
                    else:
                        print("Leaving as is.")

    def check_formatting(self, offer_fix: bool) -> None:
        for question in self.questions:
            formatted = question.snippet.format(compressed=True)
            if formatted is None:
                # error when trying to format snippet
                print(f"\N{CROSS MARK} error when formatting {question.id}")
                print("Given:")
                colour_print(question.snippet.code, colour="red")
                self.failed.append(question)
            elif formatted != question.snippet.code:
                print(f"\N{CROSS MARK} unexpected formatting for {question.id}")
                print("Formatted:")
                colour_print(question.snippet.format(compressed=True), colour="green")
                print("Given:")
                colour_print(question.snippet.code, colour="red")
                self.failed.append(question)
                if offer_fix:
                    response = should_fix()
                    if response:
                        self.fix_formatting(question)
                        print("\N{SPARKLES} Fixed.", end="\n\n")
                    else:
                        print("Leaving as is.")


def check_output(args) -> int:
    questions = AnkiQuestions(tag=args.tag)
    questions.check_output(args.fix)
    if questions.failed:
        print(
            f"{len(questions.failed)} questions had unexpected output "
            f"({len(questions.fixed)} fixed, {len(questions.failed) - len(questions.fixed)} remaining)."
        )
        return 1
    else:
        print("All good.")
        return 0


def check_formatting(args) -> int:
    questions = AnkiQuestions(tag=args.tag)
    questions.check_formatting(args.fix)
    if questions.failed:
        print(
            f"{len(questions.failed)} questions had unexpected formatting "
            f"({len(questions.fixed)} fixed, {len(questions.failed) - len(questions.fixed)} remaining)."
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
    subparsers = parser.add_subparsers()

    check_parser = subparsers.add_parser("check", help="check snippet output")
    check_parser.add_argument("--fix", action="store_true")
    check_parser.set_defaults(func=check_output)

    format_parser = subparsers.add_parser("format", help="check snippet formatting")
    format_parser.add_argument("--fix", action="store_true")
    format_parser.set_defaults(func=check_formatting)

    args = parser.parse_args()

    exit_code = args.func(args)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
