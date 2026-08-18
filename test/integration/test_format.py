from __future__ import annotations

from snippet_checker.snippet import Snippet


class TestPythonFormat:
    def test_no_change(self):
        code = 'print("hello")\n'
        snippet = Snippet(code, "python:3.13", "test-ruff")
        assert snippet.format(compress=False) == code

    def test_converts_quotes(self):
        code = "print('hello')\n"
        snippet = Snippet(code, "python:3.13", "test-ruff")
        assert snippet.format(compress=False) == 'print("hello")\n'


class TestGoFormat:
    def test_no_change(self):
        code = 'package main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println("hello")\n}\n'
        snippet = Snippet(code, "golang:1.24", "test-gofmt")
        assert snippet.format(compress=False) == code

    def test_fixes_indentation(self):
        code = 'package main\n\nimport "fmt"\n\nfunc main() {\nfmt.Println("hello")\n}\n'
        snippet = Snippet(code, "golang:1.24", "test-gofmt")
        expected = 'package main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println("hello")\n}\n'
        assert snippet.format(compress=False) == expected


class TestNodeFormat:
    def test_no_change(self):
        code = 'console.log("hello");\n'
        snippet = Snippet(code, "node:24.13", "test-prettier")
        assert snippet.format(compress=False) == code

    def test_adds_semicolon(self):
        code = 'console.log("hello")\n'
        snippet = Snippet(code, "node:24.13", "test-prettier")
        assert snippet.format(compress=False) == 'console.log("hello");\n'


class TestRubyFormat:
    def test_no_change(self):
        code = "puts 'hello'\n"
        snippet = Snippet(code, "ruby:3.4", "test-rubocop")
        assert snippet.format(compress=False) == code

    def test_converts_quotes(self):
        code = 'puts "hello"\n'
        snippet = Snippet(code, "ruby:3.4", "test-rubocop")
        assert snippet.format(compress=False) == "puts 'hello'\n"


class TestRustFormat:
    def test_no_change(self):
        code = 'fn main() {\n    println!("hello");\n}\n'
        snippet = Snippet(code, "rust:1.93", "test-rustfmt")
        assert snippet.format(compress=False) == code

    def test_fixes_indentation(self):
        code = 'fn main() {\nprintln!("hello");\n}\n'
        snippet = Snippet(code, "rust:1.93", "test-rustfmt")
        expected = 'fn main() {\n    println!("hello");\n}\n'
        assert snippet.format(compress=False) == expected
