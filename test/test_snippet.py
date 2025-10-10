from pathlib import Path

from pytest import mark

from check_snippets import Snippet


def get_snippets(dir):
    snippets = []
    outputs = []
    target_dir = Path("./test/snippets") / dir

    for dir in target_dir.iterdir():
        with open(dir / "snippet.py") as f:
            snippets.append(f.read())
        with open(dir / "output.txt") as f:
            outputs.append(f.read())

    return zip(snippets, outputs)


@mark.parametrize("source_code, expected_output", get_snippets("ok"))
def test_ok_snippet(source_code, expected_output):
    snippet = Snippet(source_code)
    actual_output = snippet.run()
    assert expected_output == str(actual_output)


@mark.xfail
@mark.parametrize("source_code, expected_output", get_snippets("limitations"))
def test_limitations_snippet(source_code, expected_output):
    snippet = Snippet(source_code)
    actual_output = snippet.run()
    assert expected_output == str(actual_output)


def test_format_no_change():
    source_code = 'print("hello")\n'
    snippet = Snippet(source_code)
    assert snippet.format() == source_code


def test_format_change():
    source_code = 'print("hello")'  # new newline at eof
    snippet = Snippet(source_code)
    assert snippet.format() == 'print("hello")\n'
