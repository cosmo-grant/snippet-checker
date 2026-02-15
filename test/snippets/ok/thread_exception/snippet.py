from threading import Thread


def bad():
    raise Exception


thread = Thread(target=bad)
thread.start()
thread.join()
print("here")
