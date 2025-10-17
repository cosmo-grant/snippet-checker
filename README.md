# snippet-checker

I have many anki notes consisting of a code snippet, e.g.

```python
from asyncio import create_task, run

async def main():
    create_task(foo())
    print("in main")

async def foo():
    print("in foo")

run(main())
```

the output

```
in main
in foo
```

and an explanation

```
`create_task()` schedules the coroutine for execution.

No await, so the `main()` coroutine runs to completion first.
```

I'd like to develop a tool that can verify the output and format the code.

It should be able to verify snippets in various languages, both interpreted and compiled: python, go, ruby, javascript, ...

The code is not arbitrary (I wrote it) but does need to be sandboxed (e.g. it may write to disk).

Sometimes it matters not just _what_ is printed, but _when_ it's printed, e.g.

```python
from threading import Thread
from time import sleep, time

def io_bound(): sleep(3); print("done")

thread1, thread2 = Thread(target=io_bound), Thread(target=io_bound)
t1 = time()
thread1.start()
thread2.start()
t2 = time()
print("%d" % (t2 - t1))
```


```
0
<~3s>
done
done
```

The tool should cope with this.

It should be able to read from my anki deck directly, or also from a directory with structure something like

```
questions
├── 00
│   ├── explanation.txt
│   ├── output.txt
│   └── snippet.py
├── 01
│   ├── explanation.txt
│   ├── output.txt
│   └── snippet.py
├── 02
│   ├── explanation.txt
│   ├── output.txt
│   └── snippet.py
```


## What if my question fails the check?

When checking outputs, the checker runs the question's snippet, gets the docker logs, represents those logs as a string (call that the _docker output_), and normalises the string.
It compares the normalised docker output with the normalised given output.
If these are different, it complains.

When checking formatting, the checker runs the question's snippet through a formatter, perhaps does some further formatting of its own, and compares the result to what it started with.
If they're different, it complains.

What to do when it complains?
If you agree, the checker has done its job and you can update the question accordingly.
If you disagree, you can:
  1. adapt the checker to handle the question
  2. adapt the question to something the checker can handle
  3. tag the question as to be permanently ignored

The right response depends on the case.

### Examples

#### Checking formatting

```python
print("foo" "bar")
```

`ruff` changes this to `print("foobar")`, but the point of the question is to show implicit string concatenation, so ignore.

```python
x = ()
print(type(x))
x = (1)
print(type(x))
x = (1,)
print(type(x))
```

`ruff` changes the middle assignment to `x = 1`, but the point of the question is that these are equivalent, so ignore.

```python
def func(x, y, z):
    return (x - y) * z

print(func(x=1, 0, 2))
```

`ruff` can't parse, but the point of the question is _args before kwargs_, so ignore.

```python
from collections import deque

d = deque(range(5))
print(d)
d.rotate(2); print(d)
d.rotate(-2); print(d)
d.rotate(-2); print(d)
```

`ruff` wants the prints on their own lines, but I think same-lines makes the point of the question clearer.

```python
matrix = [
    [1, 2], 
    [3, 4]
]

flattened = [
    entry 
    for row in matrix 
    for entry in row
]

print(flattened)
```

`ruff` wants to collapse into single lines, but a point of the note is implicit line continuation.

#### Checking output

```
with open("my_file.txt") as f:
    for x in f:
        print(x)

assuming my_file.txt is "first\nsecond\nthird"
```

This is not Python so the checker can't handle it, but we can easily adapt it:

```python
with open("my_file.txt", "w") as f:
    f.write("first\nsecond\nthird"

with open("my_file.txt") as f:
    for x in f:
        print(x)
```

Similarly, the checker can't handle

```python
try:
    x = input()
    # user enters Ctrl-C
except Exception as exception:
    print("exception")
finally:
    print("finally")
```

but I don't see how to adapt the question, so ignore.

The checker can't handle this either at the moment:

```
% echo 'print("gotcha")' > pip.py
% python -m pip install requests
```

but it could be adapted to handle it.
