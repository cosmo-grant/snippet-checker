from pathlib import Path

from pytest import mark

from check_snippets import Snippet


def get_snippets():
    snippets = []
    outputs = []
    snippets_dir = Path("./test/snippets")

    for dir in snippets_dir.iterdir():
        with open(dir / "snippet.py") as f:
            snippets.append(f.read())
        with open(dir / "output.txt") as f:
            outputs.append(f.read())

    return zip(snippets, outputs)


@mark.parametrize("source_code, expected_output", get_snippets())
def test_snippet(source_code, expected_output):
    snippet = Snippet(source_code)
    actual_output = snippet.run()
    assert expected_output == str(actual_output)
