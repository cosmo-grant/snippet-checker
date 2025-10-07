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

