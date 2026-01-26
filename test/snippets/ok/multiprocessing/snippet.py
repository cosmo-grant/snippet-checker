# see #21

from multiprocessing import Process
from time import sleep


def io_bound():
    sleep(1)
    print("done")


if __name__ == "__main__":
    # we're assuming multicore machine
    proc1, proc2 = Process(target=io_bound), Process(target=io_bound)

    proc1.start()
    proc2.start()
    print("here")
