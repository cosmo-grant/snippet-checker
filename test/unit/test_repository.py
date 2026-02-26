from __future__ import annotations

from dataclasses import dataclass

import pytest

from snippet_checker.repository import (
    AnkiConfig,
    DirectoryRepository,
    escape_html,
    markdown_code,
    markdown_output,
    markup_code,
    markup_output,
    note_to_question,
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


def test_markdown_code():
    html = '<pre><code class="lang-python">x &lt; 1 &amp; y &gt; 2</code></pre>'
    assert markdown_code(html) == "x < 1 & y > 2"


def test_markup_code():
    assert markup_code("x < 1 & y > 2", "python") == '<pre><code class="lang-python">x &lt; 1 &amp; y > 2</code></pre>'


@pytest.mark.parametrize(
    "code",
    [
        "x = 1",
        "def foo():\n    pass",
        "print('<html>')",
    ],
)
def test_code_roundtrip(code):
    assert markdown_code(markup_code(code, "python")) == code


def test_markdown_output():
    html = "<pre><samp>&lt;class 'int'&gt;</samp></pre>"
    assert markdown_output(html) == "<class 'int'>"


def test_markup_output():
    assert markup_output("<class 'int'>") == "<pre><samp>&lt;class 'int'></samp></pre>"


@pytest.mark.parametrize(
    "output",
    [
        "plain text",
        "ValueError: list.remove(x): x not in list",
        "[1, 2, 3]\nTrue",
    ],
)
def test_output_roundtrip(output):
    assert markdown_output(markup_output(output)) == output


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
    """Minimal note structure matching AnkiNote protocol."""

    id: int
    fields: list[str]
    tags: list[str]


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
    q = note_to_question(note)
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
    q = note_to_question(note)
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
