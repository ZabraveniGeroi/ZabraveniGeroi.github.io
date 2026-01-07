class Generatable:
    def generate(self) -> str:
        raise NotImplementedError()


class Tag(Generatable):
    def __init__(self, name, attrs=None, children: list[Generatable] = None):
        self.name = name
        self.attrs = attrs or {}
        self.children = children or []

    def generate(self):
        attrs = (
            " " + " ".join([f"{a}={b}" for a, b in self.attrs.items()])
            if self.attrs
            else ""
        )
        children = "".join([c.generate() for c in self.children])
        if children:
            return f"<{self.name}{attrs}>{children}</{self.name}>"
        return f"<{self.name}{attrs}/>"

    def __eq__(self, other):
        return self.attrs == other.attrs and self.children == other.children


class Content(Generatable):
    def __init__(self, cont: str = ""):
        self.cont = cont
        self.children = []

    def generate(self):
        return self.cont

    def __eq__(self, other):
        return self.cont == other.cont


class Comment(Generatable):
    def __init__(self, cont: str):
        self.cont = cont
        self.children = []

    def generate(self) -> str:
        return f"<!--{self.cont}-->"


class Joined(Generatable):
    def __init__(self, cont: list[Generatable]):
        self.children = cont

    def generate(self):
        return "".join([g.generate() for g in self.children])


create = lambda n: lambda *a, **kwa: Tag(n, *a, **kwa)

p = create("p")
h1 = create("h1")
h2 = create("h2")
h3 = create("h3")
h4 = create("h4")
body = create("body")
br = create("br")
hr = create("hr")
style = create("style")
strong = create("strong")
a = create("a")
code = create("code")
pre = create("pre")
i = create("i")
s = create("s")
u = create("u")
sup = create("sup")
sub = create("sub")
abbr = create("abbr")
link = create("link")
meta = create("meta")
head = create("head")
img = create("img")
bqoute = create("blockquote")
ul = create("ul")
ol = create("ol")
li = create("li")
div = create("div")
span = create("span")
details = create("details")
summary = create("summary")
figure = create("figure")
figcaption = create("figcaption")
svg = create("svg")
polyline = create("polyline")
path = create("path")
inp = create("input")
lable = create("lable")
title = create("title")


def chart(w, h, data, width, color):
    return svg(
        {"viewBox": f'"-{width} 0 {w} {h}"'},
        [
            polyline(
                {
                    "fill": '"none"',
                    "stroke": f'"{color}"',
                    "stroke-width": f'"{width}px"',
                    "points": '"' + " ".join([f"{a}, {b}" for (a, b) in data]) + '"',
                },
                [],
            )
        ],
    )


def smoothChart(w, h, data, width, color, coords=False):
    s = svg(
        {"viewBox": f'"-{width} 0 {w} {h}"'},
        [
            path(
                {
                    "fill": '"none"',
                    "stroke": f'"{color}"',
                    "stroke-width": f'"{width}px"',
                    "d": f'"M {data[0][0]} {data[0][1]} C {data[0][0]} {data[0][1]}, {data[0][0]} {data[0][1]}, {data[0][0]} {data[0][1]} S '
                    + " S ".join(
                        [
                            f"{a1} {a2}, {b1} {b2}"
                            for ((a1, a2), (b1, b2)) in zip(data[1::2], data[2::2])
                        ]
                    )
                    + (
                        ""
                        if not len(data) % 2
                        else f" S {data[-2][0]} {data[-2][0]}, {data[-1][0]} {data[-1][1]}"
                    )
                    + '"',
                },
                [],
            )
        ],
    )

    if coords:
        s.children.append(
            path(
                {
                    "fill": '"none"',
                    "stroke": f'"{color}"',
                    "stroke-dasharray": f'"{width / 4},{width / 4}"',
                    "stroke-width": f'"{width}px"',
                    "d": '"M 0 0 l 100 0"',
                },
                [],
            )
        )

    return s


def codeBlock(cont):
    c = code({}, cont)
    p = pre({}, [c])
    return p
