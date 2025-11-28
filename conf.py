import os
from srv import Server
import traceback

root = os.path.dirname(os.path.abspath(__file__))
server = Server(port=8080)
initers = []


def start_soon(nurs, fn, *a):
    async def new():
        try:
            await fn(*a)
        except:
            traceback.print_exc()

    nurs.start_soon(new)


def initer(fn):
    initers.append(fn)
    return fn
