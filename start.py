import importlib
import os
from conf import server, root, initers, start_soon
import trio


async def main():
    print(os.listdir(os.path.join(root, "paths")))
    for file in os.listdir(os.path.join(root, "paths")):
        print(file)
        if file.startswith(".") or file.startswith("_"):
            continue

        print(f"loading {file}")
        print(initers)
        importlib.import_module(f"paths.{file[:-3]}")

    print("loaded everything!")

    async with trio.open_nursery() as nurs:
        for initer in initers:
            print(initer)
            start_soon(nurs, initer)
        await server.start()

trio.run(main)