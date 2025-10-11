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


def canonicalize(output: str) -> str:
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

    def format(self) -> str:
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


class AnkiQuestions:
    def __init__(self, note_type: str, tag: str):
        path = Path.home() / "Library/Application Support/Anki2/cosmo/collection.anki2"
        self.collection = Collection(str(path))

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
            code = code.removeprefix('<pre><code class="lang-python">').removesuffix("</code></pre>")
            output = self.clean(output)
            id = note.id
            questions.append(Question(str(id), code, output))
        self.questions = questions

    def clean(self, output: str) -> str:
        """
        Replace html tags with text equivalents.

        Anki note fields are html.
        Code output notes' output field should have minimal markup.
        Replace this markup with text equivalents, e.g. <br> -> newline.
        """
        return output.replace("<br>", "\n").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")


def main() -> int:
    argument_parser = ArgumentParser()
    argument_parser.add_argument("note_type")
    argument_parser.add_argument("tag")
    args = argument_parser.parse_args()

    anki_questions = AnkiQuestions(note_type=args.note_type, tag=args.tag)

    failed_output = []
    for question in anki_questions.questions:
        print(f"Checking output of {question.id}...", end="", flush=True)
        diff = question.diff_output()
        if diff:
            print("❌")
            print(diff)
            failed_output.append(question)
        else:
            print("✅")

    if failed_output:
        print(f"Unexpected output for {len(failed_output)} questions: {', '.join(str(qu.id) for qu in failed_output)}")
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
