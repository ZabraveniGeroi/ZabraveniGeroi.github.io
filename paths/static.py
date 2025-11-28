import os

import inotify.adapters
import trio

from conf import initer, server, start_soon

parent = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
srvDir = os.path.join(parent, "static")


def inotifyLoop(dir):
    print(f"watching {dir}")
    i = inotify.adapters.Inotify()

    i.add_watch(dir)

    for event in i.event_gen(yield_nones=False):
        (_, types, path, filename) = event

        # print(f"PATH=[{path}] FILENAME=[{filename}] EVENT_TYPES={types}")
        for etype in types:
            if etype in {
                "IN_CREATE",
                "IN_DELETE",
                "IN_MOVED_FROM",
                "IN_MOVED_TO",
                "IN_CLOSE_WRITE",
            }:
                place = os.path.join(path, filename)
                path = place[len(srvDir) :]
                if server.serving(path):
                    print(f"unserving {place} on {path}")
                    server.unserve(path)
                if etype not in {"IN_DELETE", "IN_MOVED_TO"} and not os.path.isdir(
                    place
                ):
                    print(f"reserving {place} on {path}")
                    trio.from_thread.run(server.serve, place, path)


# TODO: just add a ctx with a nursery ffs


@initer
async def trav():
    async def w(nurs):
        await _trav(nurs=nurs, origin=srvDir)

    async with trio.open_nursery() as nurs:
        start_soon(nurs, w, nurs)


async def _trav(nurs: trio.Nursery, origin):
    for file in sorted(os.listdir(origin)):
        fpath = os.path.join(origin, file)
        isdir = os.path.isdir(fpath)

        if isdir:
            await _trav(nurs, fpath)
            continue

        print(fpath[len(srvDir) :])
        await server.serve(fpath, fpath[len(srvDir) :])
    start_soon(nurs, trio.to_thread.run_sync, inotifyLoop, origin)
