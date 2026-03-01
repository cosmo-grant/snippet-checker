from __future__ import annotations

from snippet_checker.snippet import GoSnippet, NodeSnippet, PythonSnippet, RubySnippet, RustSnippet


class TestPythonFormat:
    def test_no_change(self):
        code = 'print("hello")\n'
        snippet = PythonSnippet(code, "python:3.13")
        assert snippet.format(compress=False) == code

    def test_converts_quotes(self):
        code = "print('hello')\n"
        snippet = PythonSnippet(code, "python:3.13")
        assert snippet.format(compress=False) == 'print("hello")\n'


class TestGoFormat:
    def test_no_change(self):
        code = 'package main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println("hello")\n}\n'
        snippet = GoSnippet(code, "golang:1.24")
        assert snippet.format(compress=False) == code

    def test_fixes_indentation(self):
        code = 'package main\n\nimport "fmt"\n\nfunc main() {\nfmt.Println("hello")\n}\n'
        snippet = GoSnippet(code, "golang:1.24")
        expected = 'package main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println("hello")\n}\n'
        assert snippet.format(compress=False) == expected


class TestNodeFormat:
    def test_no_change(self):
        code = 'console.log("hello");\n'
        snippet = NodeSnippet(code, "node:24")
        assert snippet.format(compress=False) == code

    def test_adds_semicolon(self):
        code = 'console.log("hello")\n'
        snippet = NodeSnippet(code, "node:24")
        assert snippet.format(compress=False) == 'console.log("hello");\n'


class TestRubyFormat:
    def test_no_change(self):
        code = "# frozen_string_literal: true\n\nputs 'hello'\n"
        snippet = RubySnippet(code, "ruby:3.4")
        assert snippet.format(compress=False) == code

    def test_adds_frozen_string_literal_and_converts_quotes(self):
        code = 'puts "hello"\n'
        snippet = RubySnippet(code, "ruby:3.4")
        assert snippet.format(compress=False) == "# frozen_string_literal: true\n\nputs 'hello'\n"


class TestRustFormat:
    def test_no_change(self):
        code = 'fn main() {\n    println!("hello");\n}\n'
        snippet = RustSnippet(code, "rust:1.93")
        assert snippet.format(compress=False) == code

    def test_fixes_indentation(self):
        code = 'fn main() {\nprintln!("hello");\n}\n'
        snippet = RustSnippet(code, "rust:1.93")
        expected = 'fn main() {\n    println!("hello");\n}\n'
        assert snippet.format(compress=False) == expected
