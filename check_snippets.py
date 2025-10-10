import difflib
import os
import re
import subprocess
import time
from argparse import ArgumentParser
from pathlib import Path

import docker
from anki.storage import Collection


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
        self.expected_output = expected_output


def get_anki_notes(note_type: str, tag: str) -> list:
    path = Path.home() / "Library/Application Support/Anki2/cosmo/collection.anki2"
    collection = Collection(str(path))
    note_ids = collection.find_notes("")
    all_notes = [collection.get_note(id) for id in note_ids]
    notes = [
        note
        for note in all_notes
        if tag in note.tags and note.note_type()["name"] == note_type  # type: ignore[index]
    ]
    return notes


def main():
    argument_parser = ArgumentParser()
    argument_parser.add_argument("note_type")
    argument_parser.add_argument("tag")
    args = argument_parser.parse_args()

    print(f"Looking for notes with type '{args.note_type}' and tag '{args.tag}'.")
    notes = get_anki_notes(note_type=args.note_type, tag=args.tag)
    print(f"Found {len(notes)} notes")

    questions = []
    for note in notes:
        code, output, _, _ = note.fields
        code = code.removeprefix('<pre><code class="lang-python">').removesuffix("</code></pre>")
        id = note.id
        questions.append(Question(id, code, output))

    failed_output = []
    for question in questions:
        print(f"Checking output of {question.id}...", end="", flush=True)
        actual_output = str(question.snippet.run())
        if question.expected_output != actual_output:
            print("❌")
            diff = difflib.ndiff(
                question.expected_output.splitlines(keepends=True),
                actual_output.splitlines(keepends=True),
            )
            print("".join(diff))
            failed_output.append(question)
        else:
            print("✅")

    if failed_output:
        print(f"Unexpected output for {len(failed_output)} questions: {', '.join(str(qu.id) for qu in failed_output)}")


if __name__ == "__main__":
    main()
