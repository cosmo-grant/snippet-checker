# snippet-checker

Check code snippets in anki or files via docker.

## Quickstart

Install:

```
uv tool install snippet-checker
```

Requires Docker.

### How to check anki

In `~/.snippet-checker/` or `$XDG_CONFIG_HOME/snippet-checker/` write `snippet-checker.toml`:

```toml
# Name of your anki profile.
profile = "cosmo"

# Tell the tool how to extract the code and output from your notes.
[[notes]]
note_type = "Code output"

# The field containing the code.
[notes.code_field]
name = "Code"
# Your field may contain markup, as well as the code.
# The pattern should be a Python regex with a group named "target", which matches just the code.
# The pattern below works for fields like '<pre><code class="lang-python">print(1 + 1)</code></pre>'.
# The markup is added back when the tool writes to anki.
pattern = '(?s)^<pre><code class="lang-\w+">(?P<target>.*)</code></pre>$'

# The field containing the output.
[notes.output_field]
name = "Output"
# As above.
# This pattern works for fields like '<pre><samp>2\n</samp></pre>'.
pattern = "(?s)^<pre><samp>(?P<target>.*)</samp></pre>$"

# Same again for each note type you want to check.
```

In anki:
- add a tag to the notes you want to check
  - e.g. `check_me`
- add suitable tags `snip:image:<image tag>` to the notes which have snippets
  - e.g. `snip:image:python:3.13`
  - sets the image in which the tool runs that note's snippet
  - the image is pulled via `docker image pull <image tag>`
- add other tags to customize how the tool treats them
  - `snip:no_check_format` to skip when checking formatting
  - `snip:no_check_output` to skip when checking outputs
  - `snip:output_verbosity:0` or `1` or `2`
  - `snip:no_compress` to keep double blank lines in code
  - more details on these below

(Anki lets you batch edit tags: select the notes, right click, Notes > Add/Remove Tags.)

Check outputs:

```
uv tool run snippet-checker --anki output check_me
```

Check formatting:

```
uv tool run snippet-checker --anki format check_me
```

Pass `--interactive` to fix interactively.
Pass `--fix` to auto-fix (back up your collection first).

### Checking files

Structure your directory something like

```
your_dir
├── a_snippet
│   ├── main.py
│   └── output.txt
├── more_snippets
│   ├── extra_files_anywhere_are_ok
│   ├── a_go_snippet
│   │   ├── go.mod
│   │   ├── main.go
│   │   └── output.txt
│   ├── a_javascript_snippet
│   │   ├── main.js
│   │   └── output.txt
│   └── another_python_snippet
│       ├── main.py
│       └── output.txt
```

Write a `snippet_checker.toml` file at `your_dir`'s root:

```toml
# Set how tracebacks, panics etc. are abbreviated.
output_verbosity = 0  # Or 1 or 2.

# Set image tags.
[images]
js = "node:22"
rb = "ruby:2.7"
py = "python:3.14"
go = "golang:1.23"
rs = "rust:1.93"
```

To override a setting for a particular snippet, add another `snippet_checker.toml` alongside it:

```toml
check_format = false

[images]
go = "golang:1.21"
```

Check outputs:

```
uv tool run snippet-checker output your_dir
```

Check formatting:

```
uv tool run snippet-checker --anki format your_dir
```

Pass `--interactive` to fix interactively.
Pass `--fix` to auto-fix (version control your collection first).

## Examples

`snippet-checker` runs the code as though at the command line
(`python main.py`, `node main.js`, `go build main.go` then `/main`, etc)
then constructs _timed, normalised_ outputs.

### Hello world

```python
print("hello world")
```

```text
hello world
```

Trailing newline included.

### Timing

```python
from threading import Thread
from time import sleep


def io_bound():
    sleep(3)
    print("done")


thread1 = Thread(target=io_bound)
thread2 = Thread(target=io_bound)
thread1.start()
thread2.start()
print("here")
```

```text
here
<~3s>
done
done
```

Timing matters, so it's included in the output.
Gaps are rounded to the nearest second,
are only included if at least 1s after rounding,
and are always included in the form "<~Xs>".

### Normalising exceptions

```python
1 / 0
```

Output verbosity 0:

```text
ZeroDivisionError: division by zero
```

Output verbosity 1

```text
Traceback (most recent call last):
  ...
ZeroDivisionError: division by zero
```

Output verbosity 2:

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    1 / 0
    ~~^~~
ZeroDivisionError: division by zero
```

Similar for exceptions in other languages.

### Normalising memory locations

```python
class C:
    pass


class D:
    pass


c = C()
d = D()
print(c)
print(d)
print(c)
```

```text
<__main__.C object at 0x100>
<__main__.D object at 0x200>
<__main__.C object at 0x100>
```

Memory addresses vary from run to run.
The tool replaces them by consistent, simpler addresses.

## Q&A

### Which languages does it support?

Python and Go robustly.
JavaScript (Node), Ruby and Rust somewhat, but output normalisation is wip.

### How sandboxed?

The snippets run in Docker containers.
No mounts or volumes.

### What to do when `snippet-checker` complains?

If you agree, then it's done its job and you can update the snippet or output.

If you disagree, then you have options:
  1. open an issue to adapt `snippet-checker` to handle your snippet
  2. adapt your snippet to something `snippet-checker` can handle
  3. tag your snippet so `snippet-checker` ignores it

Some examples.

`snippet-checker` can't handle

```python
with open("my_file.txt") as f:
    for x in f:
        print(x)

# assuming my_file.txt is "first\nsecond\nthird"
```

but we can adapt the snippet to something it can handle:

```python
with open("my_file.txt", "w") as f:
    f.write("first\nsecond\nthird"

with open("my_file.txt") as f:
    for x in f:
        print(x)
```

It can't handle this either

```python
try:
    x = input()
    # user enters Ctrl-C
except Exception:
    print("exception")
finally:
    print("finally")
```

and I don't see how to adapt the snippet or the tool.
Better just add a tag so `snippet-checker` ignores it.

Or a formatting example:

```python
print("foo" "bar")
```

`ruff` formats this as `print("foobar")`.
But if the point of the question is to show implicit string concatenation,
again better to add a tag so `snippet-checker` ignores it.

### What formatters does it use?

A fixed formatter with default configuration for each language:
`ruff`, `prettier`, `gofmt`, `rubocop`, `rustfmt`.
I'm thinking about how to make this customizable.

### What's no_compress?

`ruff` likes double blank lines, e.g. between class definitions.
But space is at a premium in anki notes.
So by default double blanks are replaced by single blanks after formatting.
If you don't want this add a `snip:no_compress` tag.
