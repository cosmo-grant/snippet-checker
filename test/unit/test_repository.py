from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from typing import Any

import pytest

from snippet_checker.config import FieldConfig, NoteTypeConfig
from snippet_checker.question import Question, Tag
from snippet_checker.repository import (
    AnkiConfig,
    DirectoryRepository,
    _find_config,
    escape_html,
    extract_target,
    note_to_question,
    replace_target,
    unescape_html,
)


def test_unescape_html():
    assert unescape_html("<br> &lt; &gt; &nbsp; &amp; &apos; &quot;") == "\n < >   & ' \""


def test_escape_html():
    assert escape_html("& < >") == "&amp; &lt; >"


@pytest.mark.parametrize(
    "text",
    [
        "plain text",
        "x > 1 & y < 2",
        "a\nb d'e\"f",
    ],
)
def test_escape_unescape_roundtrip(text):
    assert unescape_html(escape_html(text)) == text


def test_extract_target():
    actual = extract_target(
        re.compile(r'(?s)^<pre><code class="lang-\w+">(?P<target>.*)</code></pre>$'),
        '<pre><code class="lang-python">print(1 + 1)</code></pre>',
    )
    expected = "print(1 + 1)"
    assert actual == expected


def test_extract_target_unescapes_html():
    actual = extract_target(
        re.compile(r'(?s)^<pre><code class="lang-\w+">(?P<target>.*)</code></pre>$'),
        '<pre><code class="lang-python">print(1 &lt; 2)</code></pre>',
    )
    expected = "print(1 < 2)"
    assert actual == expected


def test_replace_target():
    actual = replace_target(
        re.compile(r'(?s)^<pre><code class="lang-\w+">(?P<target>.*)</code></pre>$'),
        '<pre><code class="lang-python">print(1+1)</code></pre>',
        "print(1 + 1)",
    )
    expected = '<pre><code class="lang-python">print(1 + 1)</code></pre>'

    assert actual == expected


def test_replace_target_escapes_html():
    actual = replace_target(
        re.compile(r'(?s)^<pre><code class="lang-\w+">(?P<target>.*)</code></pre>$'),
        '<pre><code class="lang-python">x&lt;1</code></pre>',
        "x < 1",
    )
    expected = '<pre><code class="lang-python">x &lt; 1</code></pre>'
    assert actual == expected


@pytest.mark.parametrize(
    "original",
    [
        '<pre><code class="lang-python">x = 1</code></pre>',
        '<pre><code class="lang-python">def foo():\n    pass</code></pre>',
        '<pre><code class="lang-python">print("&lt;html>")</code></pre>',
    ],
)
def test_target_roundtrip(original):
    pattern = re.compile(r'(?s)^<pre><code class="lang-\w+">(?P<target>.*)</code></pre>$')
    assert replace_target(pattern, original, extract_target(pattern, original)) == original


def test_anki_config_defaults():
    config = AnkiConfig(["image:python:3.13"])
    assert config.image == "python:3.13"
    assert config.check_output is True
    assert config.check_format is True
    assert config.output_verbosity == 0
    assert config.compress is True


def test_anki_config_flags_override_defaults():
    config = AnkiConfig(["image:golang:1.25", "no_check_output", "no_check_format", "output_verbosity:2", "no_compress"])
    assert config.image == "golang:1.25"
    assert config.check_output is False
    assert config.check_format is False
    assert config.output_verbosity == 2
    assert config.compress is False


@dataclass
class FakeNote:
    """Minimal note structure matching anki.notes.Note protocol."""

    id: int
    fields: list[str]
    tags: list[str]

    def note_type(self) -> dict[str, Any]:
        return {"name": "code_output"}

    def keys(self) -> list[str]:
        return ["code", "output", "explanation", "context"]


def test_note_to_question():
    note = FakeNote(
        id=123,
        fields=[
            '<pre><code class="lang-python">print(1 + 1 == 2)</code></pre>',
            "<pre><samp>True</samp></pre>",
            "See Principia.",
            "Python",
        ],
        tags=["snip:image:python:3.13"],
    )
    note_type_configs = [
        NoteTypeConfig(
            name="code_output",
            code_field=FieldConfig(name="code", pattern=re.compile(r'(?s)^<pre><code class="lang-\w+">(?P<target>.*)</code></pre>$')),
            output_field=FieldConfig(name="output", pattern=re.compile(r"(?s)^<pre><samp>(?P<target>.*)</samp></pre>$")),
        ),
    ]
    q = note_to_question(note_type_configs, note)
    assert q.id == 123
    assert q.snippet.code == "print(1 + 1 == 2)"
    assert q.given_output == "True"
    assert q.image == "python:3.13"
    assert q.check_output is True
    assert q.check_formatting is True
    assert q.compress is True
    assert q.output_verbosity == 0


def test_note_to_question_respects_config_tags():
    note = FakeNote(
        id=456,
        fields=[
            '<pre><code class="lang-python">print(1)</code></pre>',
            "<pre><samp>1\n</samp></pre>",
            "Printing 1 prints 1.",
            "Python",
        ],
        tags=[
            "snip:image:python:3.13",
            "snip:no_check_output",
            "snip:no_check_format",
            "snip:no_compress",
            "snip:output_verbosity:2",
        ],
    )
    note_type_configs = [
        NoteTypeConfig(
            name="code_output",
            code_field=FieldConfig(name="code", pattern=re.compile(r'(?s)^<pre><code class="lang-\w+">(?P<target>.*)</code></pre>$')),
            output_field=FieldConfig(name="output", pattern=re.compile(r"(?s)^<pre><samp>(?P<target>.*)</samp></pre>$")),
        ),
    ]
    q = note_to_question(note_type_configs, note)
    assert q.check_output is False
    assert q.check_formatting is False
    assert q.compress is False
    assert q.output_verbosity == 2


def test_directory_repository_get(tmp_path):
    (tmp_path / "snippet_checker.toml").write_text('[images]\npy = "python:3.13"\ngo = "golang:1.25"\n')

    q1 = tmp_path / "q1"
    q1.mkdir()
    (q1 / "snippet.py").write_text("print(1)")
    (q1 / "output.txt").write_text("1\n")

    q2 = tmp_path / "nested" / "q2"
    q2.mkdir(parents=True)
    (q2 / "main.go").write_text("package main")

    repo = DirectoryRepository(tmp_path)
    questions = repo.get()

    assert len(questions) == 2

    py_q = next(q for q in questions if q.id == q1 / "snippet.py")
    go_q = next(q for q in questions if q.id == q2 / "main.go")

    assert py_q.snippet.code == "print(1)"
    assert py_q.given_output == "1\n"
    assert py_q.image == "python:3.13"

    assert go_q.snippet.code == "package main"
    assert go_q.given_output == ""
    assert go_q.image == "golang:1.25"
    assert (q2 / "output.txt").exists()


def test_directory_repository_per_question_config_overrides_root(tmp_path):
    (tmp_path / "snippet_checker.toml").write_text('[images]\npy = "python:3.13"\ncheck_output = true\n')

    q1 = tmp_path / "q1"
    q1.mkdir()
    (q1 / "snippet.py").write_text("print(1)")
    (q1 / "snippet_checker.toml").write_text("check_output = false\n")

    repo = DirectoryRepository(tmp_path)
    questions = repo.get()

    assert len(questions) == 1
    assert questions[0].check_output is False


def test_directory_repository_multiple_snippets_raises(tmp_path):
    (tmp_path / "snippet_checker.toml").write_text('[images]\npy = "python:3.13"\n')

    (tmp_path / "snippet.py").write_text("x = 1")
    (tmp_path / "main.py").write_text("y = 2")

    repo = DirectoryRepository(tmp_path)
    with pytest.raises(Exception, match="multiple snippets"):
        repo.get()


def test_directory_repository_add_tag_creates_config(tmp_path):
    question = Question(
        id=tmp_path / "main.py",
        code="",
        image="python:3.13",
        given_output="",
        check_output=True,
        check_formatting=True,
        output_verbosity=0,
        compress=False,
    )

    repo = DirectoryRepository(tmp_path)
    repo.add_tag(question, Tag.REVIEW)

    with open(tmp_path / "snippet_checker.toml", "rb") as f:
        config = tomllib.load(f)

    assert config == {"review": True}


def test_directory_repository_add_tag_idempotent(tmp_path):
    (tmp_path / "snippet_checker.toml").write_text("review = true\n")
    question = Question(
        id=tmp_path / "main.py",
        code="",
        image="python:3.13",
        given_output="",
        check_output=True,
        check_formatting=True,
        output_verbosity=0,
        compress=False,
    )
    repo = DirectoryRepository(tmp_path)
    repo.add_tag(question, Tag.REVIEW)

    with open(tmp_path / "snippet_checker.toml", "rb") as f:
        config = tomllib.load(f)

    assert config == {"review": True}


def test_directory_repository_add_tag_merges_existing(tmp_path):
    (tmp_path / "snippet_checker.toml").write_text("compress = true\n")
    question = Question(
        id=tmp_path / "main.py",
        code="",
        image="python:3.13",
        given_output="",
        check_output=True,
        check_formatting=True,
        output_verbosity=0,
        compress=False,
    )
    repo = DirectoryRepository(tmp_path)
    repo.add_tag(question, Tag.REVIEW)

    with open(tmp_path / "snippet_checker.toml", "rb") as f:
        config = tomllib.load(f)

    assert config == {"compress": True, "review": True}


def test_find_config_in_given_directory(tmp_path):
    config_file = tmp_path / "snippet_checker.toml"
    config_file.touch()
    assert _find_config(tmp_path) == config_file


def test_find_config_in_parent_directory(tmp_path):
    config_file = tmp_path / "snippet_checker.toml"
    config_file.touch()
    child = tmp_path / "child"
    child.mkdir()
    assert _find_config(child) == config_file


def test_find_config_returns_none_when_no_config(tmp_path):
    assert _find_config(tmp_path) is None


def test_directory_repository_finds_config_in_parent(tmp_path):
    (tmp_path / "snippet_checker.toml").write_text('[images]\npy = "python:3.13"\n')
    child = tmp_path / "child"
    child.mkdir()
    (child / "snippet.py").write_text("print(1)")
    (child / "output.txt").write_text("1\n")

    repo = DirectoryRepository(child)
    questions = repo.get()

    assert len(questions) == 1
    assert questions[0].image == "python:3.13"
