import os

import trio

import genweb as w
from md2html import Page, md2html

curdir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
blogPath = os.path.join(curdir, "content")
generatedBlogPath = os.path.join(curdir, "static")


def transform(p: Page):
    p.body.children = [
        w.div({"class": '"bg"', "id": '"bg1"'}, [w.Content(" ")]),
        w.div({"class": '"bg"', "id": '"bg2"'}, [w.Content(" ")]),
        w.div({"class": '"content"'}, p.body.children),
    ]


async def makePost(path, force=False):
    outPath = os.path.join(generatedBlogPath, os.path.basename(path))[:-3] + ".html"
    async with await trio.open_file(path, "r") as f:
        out = md2html(await f.read())
        transform(out)
    if not force and os.path.exists(outPath):
        return outPath
    async with await trio.open_file(outPath, "w+") as f:
        await f.write(out.generate())
    return outPath


async def getAttrs(fpath):
    # this is jank
    out: dict[str, str] = {}
    f = await trio.open_file(fpath)
    for l in await f.readlines():
        if l.startswith("-attr:"):
            l = l.removeprefix("-attr:").strip()
            field, val = (a.strip(" ") for a in l.split("="))
            out[field] = val
    await f.aclose()

    return out


async def trav(origin=blogPath):
    for file in sorted(os.listdir(origin)):
        print(f"generated {file}")
        fpath = os.path.join(origin, file)
        fpath = await makePost(fpath, force=True)


trio.run(trav)
