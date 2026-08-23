from __future__ import annotations

from snippet_checker.snippet import Snippet


class TestPythonFormat:
    def test_no_change(self):
        code = 'print("hello")\n'
        snippet = Snippet(code, "", "snip-ruff:0.16")
        assert snippet.format(compress=False) == code

    def test_converts_quotes(self):
        code = "print('hello')\n"
        snippet = Snippet(code, "", "snip-ruff:0.16")
        assert snippet.format(compress=False) == 'print("hello")\n'


class TestGoFormat:
    def test_no_change(self):
        code = 'package main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println("hello")\n}\n'
        snippet = Snippet(code, "", "snip-gofmt:1.22")
        assert snippet.format(compress=False) == code

    def test_fixes_indentation(self):
        code = 'package main\n\nimport "fmt"\n\nfunc main() {\nfmt.Println("hello")\n}\n'
        snippet = Snippet(code, "", "snip-gofmt:1.22")
        expected = 'package main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println("hello")\n}\n'
        assert snippet.format(compress=False) == expected


class TestNodeFormat:
    def test_no_change(self):
        code = 'console.log("hello");\n'
        snippet = Snippet(code, "", "snip-prettier:3.9")
        assert snippet.format(compress=False) == code

    def test_adds_semicolon(self):
        code = 'console.log("hello")\n'
        snippet = Snippet(code, "", "snip-prettier:3.9")
        assert snippet.format(compress=False) == 'console.log("hello");\n'


class TestRubyFormat:
    def test_no_change(self):
        code = "puts 'hello'\n"
        snippet = Snippet(code, "", "snip-rubocop:1.89")
        assert snippet.format(compress=False) == code

    def test_converts_quotes(self):
        code = 'puts "hello"\n'
        snippet = Snippet(code, "", "snip-rubocop:1.89")
        assert snippet.format(compress=False) == "puts 'hello'\n"


class TestRustFormat:
    def test_no_change(self):
        code = 'fn main() {\n    println!("hello");\n}\n'
        snippet = Snippet(code, "", "snip-rustfmt:1.97")
        assert snippet.format(compress=False) == code

    def test_fixes_indentation(self):
        code = 'fn main() {\nprintln!("hello");\n}\n'
        snippet = Snippet(code, "", "snip-rustfmt:1.97")
        expected = 'fn main() {\n    println!("hello");\n}\n'
        assert snippet.format(compress=False) == expected
