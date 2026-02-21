from pathlib import Path
from textwrap import dedent

from pytest import mark

from src.snippet_checker.output import PythonOutput
from src.snippet_checker.snippet import PythonSnippet


def get_snippets(dir):
    snippets = []
    outputs = []
    target_dir = Path("./test/snippets") / dir

    for dir in target_dir.iterdir():
        with open(dir / "snippet.py") as f:
            snippets.append(f.read())
        with open(dir / "output.txt") as f:
            outputs.append(f.read())

    return zip(snippets, outputs, strict=True)


@mark.parametrize("source_code, expected_output", get_snippets("ok"))
def test_ok_snippet(source_code, expected_output):
    snippet = PythonSnippet(source_code, "python:3.13", traceback_verbosity=1)
    actual_output = snippet.output
    assert expected_output == actual_output.normalised


@mark.xfail
@mark.parametrize("source_code, expected_output", get_snippets("limitations"))
def test_limitations_snippet(source_code, expected_output):
    snippet = PythonSnippet(source_code, "python:3.13", traceback_verbosity=1)
    actual_output = snippet.output
    assert expected_output == actual_output.raw


def test_format_no_change():
    source_code = 'print("hello")\n'
    snippet = PythonSnippet(source_code, "python:3.13", traceback_verbosity=0)
    assert snippet.format(compress=True) == source_code


def test_format_change():
    source_code = 'print("hello")'  # new newline at eof
    snippet = PythonSnippet(source_code, "python:3.13", traceback_verbosity=0)
    assert snippet.format(compress=True) == 'print("hello")\n'


def test_normalise_memory_address():
    output = PythonOutput(
        dedent("""
        <__main__.C object at 0x104cfa450>
        <__main__.D object at 0x104cfa5d0>
        <__main__.C object at 0x104cfa450>
        """).strip(),
        traceback_verbosity=0,
    )
    expected_normalised = (
        dedent("""
        <__main__.C object at 0x100>
        <__main__.D object at 0x200>
        <__main__.C object at 0x100>
        """).strip()
    )

    assert expected_normalised == output.normalised


def test_normalise_traceback():
    output = PythonOutput(
        dedent("""
        Traceback (most recent call last):
          File "<string>", line 1, in <module>
            1 / 0
            ~~^~~
        ZeroDivisionError: division by zero
        """).strip(),
        traceback_verbosity=1,
    )
    expected_normalised = dedent("""
        Traceback (most recent call last):
          ...
        ZeroDivisionError: division by zero
        """).strip()

    assert output.normalised == expected_normalised
