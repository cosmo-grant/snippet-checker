# snippet-checker

Check code snippets in anki or files via docker.

<!--toc:start-->
- [snippet-checker](#snippet-checker)
  - [Install](#install)
  - [How to check anki](#how-to-check-anki)
    - [Write config](#write-config)
    - [Add tags](#add-tags)
    - [Run](#run)
  - [How to check files](#how-to-check-files)
    - [Structure your directory](#structure-your-directory)
    - [Write config](#write-config-1)
    - [Run](#run-1)
  - [Bring your own images](#bring-your-own-images)
    - [Runner images](#runner-images)
    - [Formatter images](#formatter-images)
  - [Examples](#examples)
    - [Hello world](#hello-world)
    - [Timing](#timing)
    - [Normalising exceptions](#normalising-exceptions)
    - [Normalising memory locations](#normalising-memory-locations)
    - [Normalising errnos](#normalising-errnos)
    - [Normalising hangs](#normalising-hangs)
  - [Q&A](#qa)
    - ["The" output?](#the-output)
    - [What to do when `snippet-checker` complains?](#what-to-do-when-snippet-checker-complains)
    - [Which languages can it check?](#which-languages-can-it-check)
    - [Can I check snippets which use third-party packages?](#can-i-check-snippets-which-use-third-party-packages)
    - [How sandboxed?](#how-sandboxed)
    - [What formatters does it use?](#what-formatters-does-it-use)
    - [What's no_compress?](#whats-nocompress)
<!--toc:end-->

## Install

For example:

```text
uv tool install snippet-checker
```

## How to check anki

### Write config

In `~/.snippet-checker/` or `$XDG_CONFIG_HOME/snippet-checker/` write `snippet-checker.toml`, e.g.

```toml
profile = "cosmo"  # Name of your anki profile, used to locate your collection.
# You can set `collection_path = "/path/to/collection"` instead of setting the profile if you like.
timeout = 10.0  # Seconds. The tool assumes any snippet that runs for longer than this is hanging.

# The [[notes]] blocks describe how to extract the code and output from your notes.
[[notes]]
note_type = "Code output"  # Must match anki exactly.

# Information about the field containing the code.
[notes.code_field]
name = "Code"
# Your field may contain markup, as well as the code.
# The pattern should be a Python regex with a group named "target", which matches just the code.
# The pattern below works for fields like '<pre><code class="lang-python">print(1 + 1)</code></pre>'.
# The markup is added back when the tool writes to anki.
pattern = '(?s)^<pre><code class="lang-\w+?">(?P<target>.*)</code></pre>$'

# Information about the field containing the output.
[notes.output_field]
name = "Output"
# This pattern works for fields like '<pre><samp>2\n</samp></pre>'.
pattern = "(?s)^<pre><samp>(?P<target>.*)</samp></pre>$"

# More [[notes]] blocks if needed, one per target note type.
```

### Add tags

In anki:

- add a tag to the notes you want to check
  - e.g. `check_me`
- to check the outputs, add a tag `snip:runner_image:<image tag>` to the notes
  - e.g. `snip:runner_image:my-python-runner:3.13`
- to check formatting, add a tag `snip:formatter_image:<image tag>` to the notes
  - e.g. `snip:formatter_image:my-python-formatter:1.2.3`
- the images must satisfy a contract - see [Bring your own images](#bring-your-own-images)
- add other tags to customize how the tool treats them
  - `snip:no_check_format` to skip when checking formatting
  - `snip:no_check_output` to skip when checking outputs
  - `snip:output_verbosity:0` or `1` or `2`
  - `snip:no_compress` to keep double blank lines in code
  - more details on these below

(Anki lets you batch edit tags: select the notes, right click, Notes > Add/Remove Tags.)

### Run

Ensure Docker is running.

Check outputs:

```text
snippet-checker --anki output check_me
```

Check formatting:

```text
snippet-checker --anki format check_me
```

Pass `--interactive` to fix interactively.
Pass `--fix` to auto-fix (back up your collection first).

## How to check files

### Structure your directory

Something like

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

### Write config

At `your_dir`'s root write `snippet_checker.toml`, e.g.

```toml
# Set how tracebacks, panics etc. are abbreviated.
output_verbosity = 0  # Or 1 or 2.

# Set runner image tags (the snippets are executed using these)
[runner_images]
js = "my-javascript-runner:24.13"
py = "my-python-runner:3.14"
go = "my-go-runner:1.23"

# Set formatter image tags (the snippets are formatted using these)
[formatter_images]
js = "my-javascript-formatter:1.2"
py = "my-python-formatter:1.2"
go = "my-go-formatter:1.2"
```

To override a setting for a particular snippet, add another `snippet_checker.toml` alongside it:

```toml
check_format = false

[runner_images]
go = "my-alternative-go-runner:1.21"
```

### Run

Ensure Docker is running.

Check outputs:

```text
snippet-checker output your_dir
```

Check formatting:

```text
snippet-checker format your_dir
```

Pass `--interactive` to fix interactively.
Pass `--fix` to auto-fix (version control your collection first).

## Bring your own images

You must create your own runner and formatter images.
A hassle, yes.
But it means you can check snippets in any language, at any version, with any dependencies,
and can control runtime and formatting configuration.

### Runner images

Contract:

- The image must have `prepare.sh`, `run.sh` scripts which can be executed via `./prepare.sh`, `./run.sh`.
- The tool copies the snippet into the image's working directory as `main`.
- `prepare.sh` does any setup, e.g. compilation, install dependencies.
- If it exits non-zero, its output is treated as the snippet's output.
- Else, `run.sh` executes the snippet, and its output is treated as the snippet's output.

For example, to run Go snippets you could create

```text
my-go-runner
├── Dockerfile
└── prepare.sh
└── run.sh
```

where `prepare.sh` is

```sh
#!/bin/sh
set -e
mv main main.go
exec go build main.go
```

and `run.sh` is

```sh
#!/bin/sh
exec ./main
```

and the `Dockerfile` is

```Dockerfile
FROM golang:1.21
WORKDIR /tmp
COPY prepare.sh run.sh ./
```

(More examples in `images/runners/` in the source.)

Then

```sh
chmod +x prepare.sh run.sh
docker image build -t my-go-runner .
```

For anki, tag the target notes `snip:runner_image:my-go-runner`,
or, for files, add

```toml
[formatter_images]
py = "my-go-runner"
```

to the `snippet_checker.toml`.

### Formatter images

Contract:

- The image must have a `format.sh` script
- which can be executed via `./format.sh`
- and which reads `./input` and writes the formatted version to `./output`
- and which exits 0 just if there was no error when formatting (whether or not changes were made).

For example, to format Python snippets you could create

```text
my-python-formatter
├── Dockerfile
└── format.sh
```

where `format.sh` is

```sh
#!/bin/sh
set -e
ruff format ./input
mv ./input ./output
```

and the `Dockerfile` is

```Dockerfile
FROM ghcr.io/astral-sh/ruff:0.16-alpine
WORKDIR /tmp
ENTRYPOINT [ "" ]
COPY format.sh .
```

(More examples in `images/runners/` in the source.)

Then

```sh
chmod +x format.sh
docker image build -t my-python-formatter .
```

For anki, tag the target notes `snip:formatter_image:my-python-formatter`,
or, for files, add

```toml
[formatter_images]
py = "my-python-formatter"
```

to the `snippet_checker.toml`.

## Examples

`snippet-checker` checks your snippet's _timed, normalised_ output
(or, really, `run.sh`'s).

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
and are included in the form "<~Xs>".

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

### Normalising errnos

```python
with open("does_not_exist") as f:
  print(f.read())
```

```text
FileNotFoundError: [Errno NN] No such file or directory: 'does_not_exist'
```

Errnos vary across platforms.
The tool replaces them all with a placeholder.

### Normalising hangs

```python
import socket

srv = socket.create_server(("127.0.0.1", 65432))
print("socket created")
srv.accept()
```

```text
socket created
...
```

For a blocking socket (the default), `accept()` blocks until a connection is available.
So this snippet hangs.
The tool assumes a snippet is hanging if it runs for more than `timeout` seconds.
It kills it, appends `...` on its own line to any output so far, and returns that as the output.

## Q&A

### "The" output?

A snippet's output is not determined by its code.

We saw examples above:
memory addresses vary across runs;
errnos vary across platforms.

There are plenty more:

- `print(os.environ["PWD"])`
- `print(random.random())`
- `socket.bind(('127.0.0.1', 65432))` errors if address is already in use
- `open('foo')` errors if no such file
- timing depends on machine, contention, ...
- whether you run via `python -c 'some code'` or `python some_file.py`
- which Python cli options you set (`-u`, `-v`, `-Wignore`, ...)
- and so on

Some variation you can pin down via your runner image.
But maybe not all,
in which case the tool can only tell you _an_ output, not _the_ output.

### What to do when `snippet-checker` complains?

If you agree, then it's done its job and you can update the snippet or output.

If you disagree, then you have options:

1. adapt your image so the output `snippet-checker` generates matches what you expect
2. open an issue to adapt `snippet-checker` to handle your snippet
3. adapt your snippet to something `snippet-checker` can handle
4. tag your snippet so `snippet-checker` ignores it

Some examples.

`snippet-checker` can't handle

```python
# Assume my_file.txt is "first\nsecond\nthird\n".
with open("my_file.txt") as f:
    for x in f:
        print(x)
```

because it doesn't understand the comment.

But we can adapt the snippet to something it can handle.

```python
with open("my_file.txt", "w") as f:
    f.write("first\nsecond\nthird\n"

with open("my_file.txt") as f:
    for x in f:
        print(x)
```

Similarly, it can't handle

```python
print(({char for char in "a0b2b3" if char}))
```

because set order is non-deterministic.

We could adapt it

```python
print(sorted({char for char in "a0b2b3" if char}))
```

or maybe the underlying points would be better captured differently.

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
Better just tag it so `snippet-checker` ignores it.

Or a formatting example:

```python
print("foo" "bar")
```

`ruff` formats this as `print("foobar")`.
But if the point of the question is to show implicit string concatenation,
again better to tag it so `snippet-checker` ignores it.

### Which languages can it check?

Any, because [Bring your own images](#bring-your-own-images).

However, the tool does output normalisation itself,
so may normalise a lot (Python),
or a little (Go, Ruby, Rust, Node),
or not at all (everything else).

If you want more/different normalisations, open a PR :)

### Can I check snippets which use third-party packages?

Yes, because [Bring your own images](#bring-your-own-images).
Just write a runner image meeting the contract.

For example, to test `numpy` snippets create an image like

```Dockerfile
FROM python:3.13
WORKDIR /tmp
ENV NO_COLOR=true PYTHONWARNINGS=ignore
COPY prepare.sh run.sh ./
RUN <<EOF
python -m venv numpy_env
. numpy_env/bin/activate
python -m pip install --no-cache-dir numpy==2.5
EOF
```

where `prepare.sh` is

```sh
#!/bin/sh
mv main main.py
```

and `run.sh` is

```sh
#!/bin/sh
. numpy_env/bin/activate
python main.py
```

### How sandboxed?

The snippets run in Docker containers.
No mounts or volumes.

Don't point the tool at arbitrary code.
The sandboxing protects against accidents, not attacks.

### What formatters does it use?

Any you like, because [Bring your own images](#bring-your-own-images).

### What's no_compress?

Some formatters like double blank lines, e.g. between class definitions.
But space is at a premium in anki notes.
So by default when formatting anki double blanks are replaced by single.
To keep doubles add a `snip:no_compress` tag.
