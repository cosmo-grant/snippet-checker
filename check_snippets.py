import difflib
import os
import re
import subprocess
import sys
import time
from argparse import ArgumentParser
from pathlib import Path

import docker
from anki.storage import Collection
from tqdm import tqdm


def canonicalize(output: str) -> str:
    # TODO: ""File "<string>", line 3 SyntaxError: no binding for nonlocal 'x' found"
    output = output.rstrip("\n")
    output = canonicalize_memory_addresses(output)
    output = canonicalize_traceback(output)
    return output


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


def canonicalize_traceback(output: str) -> str:
    traceback_except_for_last_line = re.compile(
        r"Traceback \(most\ recent\ call\ last\):\n"  # start of traceback
        r"(\s.*\n)+",  # one or more lines starting with unicode whitespace and ending with newline
    )
    # a traceback's last line doesn't start with whitespace so won't be captured
    canonicalized = re.sub(traceback_except_for_last_line, "", output)

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

    def run(self) -> Output:
        container = self.client.containers.run(
            f"python:{self.python_version}",
            command=["python", "-u", "-c", self.code],
            detach=True,
            auto_remove=True,
        )

        raw_output = {}
        start = time.perf_counter()
        for line in container.logs(stream=True):  # blocks until \n
            now = time.perf_counter()
            delta = now - start
            raw_output[delta] = line
        return Output(raw_output)

    def format(self, compress: bool = False) -> str:
        called_process = subprocess.run(
            ["ruff", "format", "-"],
            check=True,
            input=self.code,
            stdout=subprocess.PIPE,
            text=True,
        )
        return called_process.stdout


class Question:
    def __init__(self, id: str, code: str, expected_output: str):
        self.id = id
        self.snippet = Snippet(code)
        self.output = expected_output

    def diff_formatting(self, compress: bool = False) -> str:
        actual = self.snippet.code
        formatted = self.snippet.format(compress)
        if compress:
            formatted = formatted.strip().replace("\n\n\n", "\n\n")
        diff = difflib.unified_diff(
            actual.splitlines(keepends=True),
            formatted.splitlines(keepends=True),
            fromfile="actual",
            tofile="formatted",
        )
        return "".join(diff)

    def diff_output(self) -> str:
        """
        Return the diff of canonicalized actual and expected output.

        The returned string should be empty if the canonicalized outputs are equal.
        Not all diff formats do this!
        """
        actual_output = str(self.snippet.run())
        canonicalized_actual_output = canonicalize(actual_output)
        canonicalized_expected_output = canonicalize(self.output)
        diff = difflib.unified_diff(
            canonicalized_actual_output.splitlines(keepends=True),
            canonicalized_expected_output.splitlines(keepends=True),
            fromfile="actual (canonicalized)",
            tofile="expected (canonicalized)",
        )
        return "".join(diff)


def should_fix() -> bool:
    response = input("Enter 'y' to overwrite: ")
    return response == "y"


class AnkiQuestions:
    def __init__(self, note_type: str, tag: str):
        path = Path.home() / "Library/Application Support/Anki2/cosmo/collection.anki2"
        self.collection = Collection(str(path))

        self.failed: list[Question] = []
        self.fixed: list[Question] = []

        print(f"Looking for notes with type '{note_type}' and tag '{tag}'.")
        note_ids = self.collection.find_notes("")
        notes = [self.collection.get_note(id) for id in note_ids]
        self.notes = [
            note
            for note in notes
            if tag in note.tags and note.note_type()["name"] == note_type  # type: ignore[index]
        ]
        print(f"Found {len(self.notes)} notes")

        questions = []
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

    def plain_to_html(self, plain: str) -> str:
        return plain.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

    def pre_process(self, code: str) -> str:
        return code.removeprefix('<pre><code class="lang-python">').removesuffix("</code></pre>")

    def post_process(self, code: str) -> str:
        return f'<pre><code class="lang-python">{code}</code></pre>'

    def fix_output(self, question: Question) -> None:
        "Write a canonicalized output of the given question's snippet to the anki database."

        note = self.collection.get_note(int(question.id))  # type: ignore[arg-type]  # TODO: more systematic type conversion
        output = note.fields[1]
        output = str(question.snippet.run())
        output = self.plain_to_html(output)
        output = canonicalize_traceback(output)
        note.fields[1] = output
        self.collection.update_note(note)
        self.fixed.append(question)
        print("\N{SPARKLES} Fixed.")

    def fix_formatting(self, question: Question) -> None:
        "Write a formatted version of the given question's snippet to the anki database."
        note = self.collection.get_note(int(question.id))  # type: ignore[arg-type]  # TODO: more systematic type conversion
        formatted = question.snippet.format(compress=True)  # compressed looks better in anki notes
        formatted = self.post_process(formatted)
        formatted = self.plain_to_html(formatted)
        note.fields[0] = formatted
        self.collection.update_note(note)
        self.fixed.append(question)
        print("\N{SPARKLES} Fixed.")

    def check_output(self, offer_fix: bool) -> None:
        for question in tqdm(self.questions):
            diff = question.diff_output()
            if diff:
                print(f"\N{CROSS MARK} unexpected output for {question.id}")
                print(diff)
                self.failed.append(question)
                if offer_fix:
                    response = should_fix()
                    if response:
                        self.fix_output(question)
                    else:
                        print("Leaving as is.")

    def check_formatting(self, offer_fix: bool) -> None:
        for question in tqdm(self.questions):
            diff = question.diff_formatting(compress=True)
            if diff:
                print(f"\N{CROSS MARK} unexpected formatting for {question.id}")
                print(diff)
                self.failed.append(question)
                if offer_fix:
                    response = should_fix()
                    if response:
                        self.fix_formatting(question)
                    else:
                        print("Leaving as is.")


def check_output(args) -> int:
    questions = AnkiQuestions(note_type=args.note_type, tag=args.tag)
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
    questions = AnkiQuestions(note_type=args.note_type, tag=args.tag)
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


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("note_type")
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
