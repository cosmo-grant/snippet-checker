from check_snippets import Snippet


def test_snippet():
    snippet = Snippet("print('hello')")
    expected_output = {0: "hello\n"}
    actual_output = snippet.run()
    assert expected_output == actual_output
