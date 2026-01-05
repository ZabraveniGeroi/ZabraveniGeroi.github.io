import html

import genweb as w


class ListIO:
    def __init__(self, l: list):
        self.l = l
        self.c = 0

    def read(self, n: int):
        self.c += n
        return self.l[self.c - n : self.c]

    def back(self, n: int):
        self.c -= n

    def ended(self):
        return self.c >= len(self.l)


# token strings

# TODO

# tokens


class Token:
    def __init__(self, name: str):
        self.name = name
        self.data = ""

    def create(self, data: str):
        obj = Token(self.name)
        obj.data = data
        return obj

    def __eq__(self, obj):
        if not isinstance(obj, Token):
            raise BaseException(
                f"comparing token to object of different type ({type(obj)})"
            )
        return obj.name == self.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return f"<Token {self.name}, {self.data}>"


ib = Token("***")
b = Token("**")
i = Token("*")
st = Token("~~")
u = Token("__")
cb = Token("```")
sc = Token("``")
vsep = Token("|")
sup = Token("^")
h4 = Token("####")
h3 = Token("###")
h2 = Token("##")
h1 = Token("#")
# hr = Token('---')
le = Token("-")
c = Token("c")  # char - used for pass-through when no rule matches
details = Token("///")
exp = Token("//")
br = Token("\\n")
attr = Token("attr")
# FIXME: the [] is a hack because im too lazy to fix this
url = Token("url[")
uclose = Token("]")
img = Token("img(")
close = Token(")")
idStart = Token("{")
idEnd = Token("}")
refStart = Token("[")
refEnd = Token("]")
sub = Token("~")
fishl = Token("|->")
fishr = Token("<-|")
bqoute = Token(">")
backslash = Token("\\")
space = Token(" ")

# TODO: popup on hover (with some iframe magic)
# TODO: tables
# TODO: automatic toc
# TODO: buttons
# TODO: use pygments for cb and maybe sc?
# TODO: link references that go to the bottom
# TODO: page refrencing mechanism?
# TODO: comments (that will show up as small text elsewhere)
# TODO: highlighting
# TODO: numbered lists
# TODO: dot spaces

# tokenizer

tokens = {}


def token(tok: Token):
    def deco(fn):
        tokens[tok] = fn

    return deco


def simpleTok(tok: Token, s: str):
    @token(tok)
    def check(buf: ListIO):
        return buf.read(len(s)) == s


def quoteTok(tok: Token, q: str):
    @token(tok)
    def check(buf: ListIO):
        if buf.read(len(q)) != q:
            return False

        o = ""
        while not o.endswith(q):
            if buf.ended():
                return False
            o += buf.read(1)[0]

        return True


simpleTok(ib, "***")
simpleTok(b, "**")
simpleTok(i, "*")
simpleTok(st, "~~")
simpleTok(sub, "~")
simpleTok(u, "__")
simpleTok(sup, "^")
simpleTok(details, "///")
simpleTok(exp, "//")
simpleTok(br, "\n")
simpleTok(cb, "```")
quoteTok(sc, "``")
simpleTok(refStart, "[")
simpleTok(refEnd, "]")
simpleTok(h4, "####")
simpleTok(h3, "###")
simpleTok(h2, "##")
simpleTok(h1, "#")
# simpleTok(hr, '---')
simpleTok(fishl, "&lt;-|")  # <-|
simpleTok(fishr, "|-&gt;")  # |->
simpleTok(attr, "-attr:")
simpleTok(le, "-")
simpleTok(url, "url[")
simpleTok(uclose, "]")
simpleTok(img, "img(")
simpleTok(close, ")")
simpleTok(idStart, "{")
simpleTok(idEnd, "}")
simpleTok(bqoute, "&gt;")  # >
simpleTok(vsep, "|")
simpleTok(space, " ")


@token(backslash)
def _bs(buf: ListIO):
    if buf.read(1) != "\\":
        return False
    buf.read(1)
    return True


@token(c)
def _c(buf: ListIO):
    buf.read(1)
    return True


def tokenize(cont: str) -> list[Token]:
    buf = ListIO(cont)
    toks = []

    while not buf.ended():
        for tok, check in tokens.items():
            oldc = buf.c

            if check(buf):
                newc = buf.c
                # print('read', buf.l[oldc: newc], 'as', tok)
                toks.append(tok.create(buf.l[oldc:newc]))
                break

            buf.c = oldc

    return toks


# rule parser

import math
from typing import Iterable, Optional


class Rule:
    def __init__(self, back=0):
        self.back = back

    def check(self, toks) -> tuple[bool, Iterable]:
        raise NotImplemented()


class Is(Rule):
    def __init__(self, tok: Token, **kwa):
        super().__init__(**kwa)
        self.tok = tok

    def check(self, toks: ListIO):
        if (tok := toks.read(1)[0]) == self.tok:
            return True, [tok]
        return False, None


class All(Rule):
    def __init__(self, *rules: list[Rule], **kwa):
        super().__init__(**kwa)
        self.rules = rules

    def check(self, toks: ListIO):
        datas = []
        for rule in self.rules:
            if toks.ended():
                return False, None
            matches, data = rule.check(toks)
            if not matches:
                return False, None

            datas.append(data)

        return True, datas


class Until(Rule):
    def __init__(self, tok: Token, no=[], only=[], **kwa):
        super().__init__(**kwa)
        self.tok = tok
        self.no = no
        self.only = only

    def check(self, toks: ListIO):
        data = []
        while (tok := toks.read(1)[0]) != self.tok:
            # check if token is not allowed, because of blacklist
            # check if we have a whitelist, and if the token is not allowed because of it
            # check if the buffer ran out
            if tok in self.no or (self.only and tok not in self.only) or toks.ended():
                return False, None
            data.append(tok)

        # here we also return the token that ended the rule (just to match the behaviour of the rest
        # of the rules)
        return True, (data, tok)


class Repeating(Rule):
    def __init__(self, rule: Rule, **kwa):
        super().__init__(**kwa)
        self.rule = rule

    def check(self, toks: ListIO):
        datas = []
        while True:
            oldc = toks.c
            matching, data = self.rule.check(toks)
            if not matching:
                toks.c = oldc
                if datas:
                    return True, datas
                return False, None
            datas.append(data)


class Shortest(Rule):
    def __init__(self, *rules, **kwa):
        self.rules = rules
        super().__init__(**kwa)

    def check(self, toks: ListIO) -> tuple[bool, Iterable]:
        out = None
        minc = math.inf
        startc = toks.c

        for r in self.rules:
            matches, data = r.check(toks)
            if matches and toks.c < minc:
                out = data
                minc = toks.c

            toks.c = startc

        toks.c = minc

        if out is not None:
            return True, out
        return False, None


class First(Rule):
    def __init__(self, *rules, **kwa):
        super().__init__(**kwa)
        self.rules = rules

    def check(self, toks: ListIO) -> tuple[bool, Iterable]:
        for r in self.rules:
            start = toks.c
            matches, data = r.check(toks)
            if matches:
                return True, data
            toks.c = start
        return False, None


class Pass(Rule):
    def __init__(self, **kwa):
        super().__init__(**kwa)

    def check(self, toks: ListIO):
        return True, None


Optional = lambda rule: First(rule, Pass())


rules = {}


def rule(r: Rule):
    def deco(fn):
        rules[r] = fn

    return deco


def srule(tok, tag, parse=True, back=0):
    # make a tag with everything between ``tok``
    def _parse(page, _, data):
        cont, _ = data
        return tag(page, buildTree(cont, page).children if parse else cont)

    rules[All(Is(tok), Until(tok), back=back)] = _parse


def drule(tok, tag):
    # directly turn tok into tag
    def parse(page, tok):
        # TODO: move this to ``tag({}, [tok])`` or something along those lines
        return tag(page, tok.data)

    rules[Is(tok)] = parse


def lrule(tok, tag, title=True, level=-1):
    # a rule matching a whole line, that starts with tok
    def parse(page, _1, _2, *a):
        _id = None
        if len(a[0]) == 2:  # here we dont have an id
            cont = a[0][0]
        else:  # here len = 3 and we have an id
            cont = a[0][0][0]
            _id = tostr(a[0][1][0])
        if title:
            page.titles.append((level, tostr(cont)))
        children = buildTree(cont, page).children
        if _id:
            children += [
                w.a({"class": '"hide"', "href": f'"#{_id}"'}, [w.Content("¶")])
            ]
        return tag(page, children, _id)

    rules[
        All(
            Is(br),
            Is(tok),
            First(All(Until(idStart, no=[br]), Until(idEnd), Is(br)), Until(br)),
            back=1,
        )
    ] = parse


def buildTree(toks, page):
    buf = ListIO(toks)
    body = w.body()

    while not buf.ended():
        matches = False
        for rule, fn in rules.items():
            oldc = buf.c
            matches, datas = rule.check(buf)
            if matches:
                out = fn(page, *datas)
                if out:
                    # print(f'matched "{buf.l[oldc:buf.c]}" to {fn} with {datas}')
                    body.children.append(out)
                    buf.back(rule.back)
                    break
            buf.c = oldc

        # print(f'c is {buf.c}, tok is {buf.l[buf.c]}')

        if not matches:
            body.children.append(w.Content(buf.read(1)[0].data))
            # i think this is how you should handle unmatched stuff?

        # print(body.generate())

    return body


def tostr(toks):
    o = ""
    for tok in toks:
        o += tok.data
    return o


# a little page class!


class Page:
    def __init__(self) -> None:
        self.head: w.Tag
        self.body: w.Tag
        self.anims = 0
        self.titles = []
        self.attrs: dict[str, str] = {}

    def generate(self):
        return w.Joined([self.head, self.body]).generate()


# rules

srule(b, lambda page, children: w.strong({}, children))
srule(i, lambda page, children: w.i({}, children))


@rule(
    All(
        Is(ib),
        Shortest(
            All(Until(i), Until(b)),
            All(Until(b), Until(i)),
            All(
                Until(ib),
            ),  # this is a hack to get it to follow the same style as the other 2
        ),
    )
)
def _ib(page, _, a):
    if len(a) == 1:
        return w.strong({}, [w.i({}, buildTree(a[0][0], page).children)])
    else:
        if a[0][-1] == i:
            # print('saw ***a*b**')
            return w.strong(
                {},
                [
                    w.i({}, buildTree(a[0][0], page).children),
                    *buildTree(a[1][0], page).children,
                ],
            )
        else:
            # print('saw ***a**b*')
            return w.i(
                {},
                [
                    w.strong({}, buildTree(a[0][0], page).children),
                    *buildTree(a[1][0], page).children,
                ],
            )


# lrule(hr, lambda page, children: w.hr({}, children))
@rule(All(Is(br), Is(le), Is(le), Is(le), Is(br), back=1))
def hr(page, *_):
    return w.hr()


@rule(All(Is(br), Repeating(All(Is(le), Until(br)), back=1)))
def list(page, _, data):
    root = w.ul()
    cur = root
    stack = [cur]
    for e in data:
        _, (data, _) = e
        l = 0

        for tok in data:
            if tok != le:
                break
            l += 1

        if len(stack) != l + 1:
            for _ in range(len(stack) - l - 1):
                stack.pop()  # remove ended inner lists

            for _ in range(l + 1 - len(stack)):
                cur.children.append(cur := w.ul())
                stack.append(cur)

            cur = stack[-1]

        cur.children.append(w.li({}, buildTree(data[l:], page).children))

    return root


srule(st, lambda page, children: w.s({}, children))
srule(sup, lambda page, children: w.sup({}, children))
srule(sub, lambda page, children: w.sub({}, children))
srule(u, lambda page, children: w.u({}, children))
srule(cb, lambda page, c: w.codeBlock([w.Content(tostr(c).strip("\n"))]), parse=False)
drule(c, lambda page, children: w.Content(children))
drule(sc, lambda page, c: w.code({}, [w.Content(c[2:-2].strip(" "))]))
lrule(
    h4,
    lambda page, children, id: w.h4(
        {"id": f'"{id}"', "class": '"show"'} if id else {}, children
    ),
    level=3,
)
lrule(
    h3,
    lambda page, children, id: w.h3(
        {"id": f'"{id}"', "class": '"show"'} if id else {}, children
    ),
    level=2,
)
lrule(
    h2,
    lambda page, children, id: w.h2(
        {"id": f'"{id}"', "class": '"show"'} if id else {}, children
    ),
    level=1,
)
lrule(
    h1,
    lambda page, children, id: w.h1(
        {"id": f'"{id}"', "class": '"show"'} if id else {}, children
    ),
    level=0,
)


@rule(All(Is(img), Until(close)))
def _img(page, _1, cont):
    cont, _ = cont
    outs = [a for a in tostr(cont).split(",")]
    text = None
    path = outs[0]
    if len(outs) >= 2:
        text = ",".join(outs[1:]).replace("\\", "")
    print(text)
    args = {"src": f'"{path}"', "loading": '"lazy"'}
    if text:
        # https://stackoverflow.com/a/26290604
        args["alt"] = f'"{text}"'
        args["title"] = f'"{text}"'
    img = w.img(args, [])
    return (
        w.div(
            {"class": '"figcontainer"'},
            [w.figure({}, [img, w.figcaption({}, [w.i({}, [w.Content(text)])])])],
        )
        if text
        else img
    )


@rule(
    All(
        Is(br),
        Shortest(
            All(Is(fishl), Is(br), Until(fishl)), All(Is(fishr), Is(br), Until(fishr))
        ),
        Is(br),
        back=1,
    )
)
def scissors(page, _1, cont, _2):
    fish, _n, (cont, _fish) = cont
    inside = buildTree(cont, page)
    fish = fish[0]
    return w.div(
        {
            "style": f'"width:44%;float:{"left" if fish == fishl else "right"};margin: 3%;"'
        },
        [inside],
    )


@rule(All(Is(url), Until(uclose)))
def _url(page, _1, cont):
    cont, _ = cont
    outs = [a for a in tostr(cont).split(",")]
    path = outs[0]
    cont = ",".join(outs[1:])
    print(cont)
    args = {"href": f'"{path}"'}
    return w.a(args, [_md2html(cont, page)])


@rule(All(Is(details), Until(details), Until(details)))
def _details(page, _1, d1, d2):
    d1, _ = d1
    d2, _ = d2
    d1c = buildTree(d1, page).children
    d2c = buildTree(d2, page).children
    tag = w.details({}, [w.summary({}, d1c), *d2c])
    return tag


@rule(All(Is(exp), Until(exp), Until(exp)))
def _exp(page, _1, d1, d2):
    d1, _ = d1
    d2, _ = d2
    d1c = buildTree(d1, page).children
    return w.abbr({"title": f'"{tostr(d2)}"', "tabindex": '"-1"'}, d1c)


@rule(All(Is(br), Is(br), back=1))
def _br(page, _1, _2):
    return w.br()


@rule(Is(backslash))
def _br(page, data):
    # TODO: should this work token-wise sometimes?
    return w.Content(data.data[-1])


# @rule(
# All(
# Is(br),
# Optional(
# All(Is(idStart), Until(idEnd, no=[br]), Is(br))
# ),  # possibly match {lable, x, y}
# Repeating(
# All(Is(vsep), Until(br, only=[space, point]))  # match |  # read until \n
# ),
# Is(vsep),
# Repeating(Is(le)),  # match the final ------
# First(
# All(Until(idStart, no=[br]), Until(idEnd), Is(br)), Is(br)
# ),  # same as above, but also consume br
# back=1,
# )
# )
# def chart(page, _1, id1, data, _2, bottom, id2):
# if id1:
# id1p = [a.strip(" ") for a in tostr(id1[1][0]).split(",")]
# topx, topy, topstep = [id1p[i] if i < len(id1p) else None for i in range(3)]
#
# if len(id2) > 1:
# id1p = [a.strip(" ") for a in tostr(id1[1][0]).split(",")]
# bottomx, bottomy, bottomstep = [
# id1p[i] if i < len(id1p) else None for i in range(3)
# ]
# print(tostr(id2[1][0]))
#
# yscale = 2
# h = len(data) * yscale
# l = len(bottom)  # the --- part from the bottom header
#
# points = []
#
# for y, line in enumerate(data):
# for x, tok in enumerate(line[1][0]):
# if tok == point:
# points.append((x, y * yscale))
#
# points.sort(key=lambda e: e[0])
#
# # len/width should be static (= k)
# # => 1/width = k/len
# # => len/k = width
# k = 200
#
# return w.smoothChart(l, h, points, f"{l/k}", "#000")


@rule(All(Is(br), Repeating(All(Repeating(Until(vsep, no=[br])), Until(br))), back=1))
def vertical(page, _, data):
    #    print(len(data), data)
    parts = {}
    # TODO: validate this - this will accept stuff that isnt correct like:
    # asd | fgh | jkl
    # asd | fgh   jkl

    for l in data:
        left, right = (
            l  # left might be more than one seperated parts, but right is always single
        )
        for i, part in enumerate([*[lef[0] for lef in left], right[0]]):
            parts[i] = [*parts.get(i, []), part, [br.create("\n")]]

    fbox = w.div(
        {"style": '"justify-content:space-between;flex-wrap:wrap;display:flex"'}, []
    )
    # TODO: same todo as the one below

    for part in parts.values():
        flat = []
        for l in part:
            flat += l
        body = buildTree(flat, page)
        # ... this style is so shit
        # TODO: why not just export this style elsewhere lol
        fbox.children.append(
            w.div(
                {
                    "style": f"'max-width:min(100%, max(min(50em, {round(100 / len(parts), 3)}%), 10em))'"
                },
                [*body.children, w.br()],
            )
        )
    return fbox


def _attr(page, cont, _):
    # i hate this
    text = w.Joined(cont).generate()
    field, val = (a.strip(" ") for a in text.split("="))
    page.attrs[field] = val
    return w.Comment(f"{field}: {val}")


lrule(attr, _attr, title=False)


@rule(All(Is(br), Repeating(All(Is(bqoute), Until(br))), back=1))
def _bquote(page, _, a):
    c = []
    for l in a:
        c += l[1][0]
        c += [br.create("\n")]
        # this is a little hack to keep new lines

    return w.bqoute({}, buildTree(c, page).children)


@rule(Is(br))
def _br(page, _1):
    return w.Content("")
    # dont include br in the left-over tokens - this renders as a space in web browsers :/


def _md2html(cont, page):
    toks = tokenize(
        "\n" + cont + "\n"
    )  # a little hack to get #, ##, ---, etc. working if they are at the top/bottom of the document
    return buildTree(toks, page)


def postproc(cont):
    return html.escape(cont)


# TODO: make a preview version of md2html
def preview(cont):
    page = Page()
    page.idLink = False
    cont = postproc(cont)
    toks = tokenize("\n" + cont + "\n")
    reading = False
    # jankily extract attrs at the top :^)
    for i, tok in enumerate(toks):
        if tok == attr:
            reading = True
            continue
        if tok == br:
            reading = False
            continue
        if not reading:
            break
    buildTree(toks[:i], page)  # this sets the attrs to the page
    page.body = buildTree(toks[i:], page)
    # print(page.attrs.get('tags'))
    # TODO: cut until preview lines
    return page


def toc(page: Page):
    root = w.ul()
    cur = root
    stack = [cur]
    for l, data in page.titles:
        if len(stack) != l + 1:
            for _ in range(len(stack) - l - 1):
                stack.pop()  # remove ended inner lists

            for _ in range(l + 1 - len(stack)):
                cur.children.append(cur := w.ul())
                stack.append(cur)

            cur = stack[-1]

        cur.children.append(w.li({}, buildTree(tokenize(data), page).children))

    return root


def md2html(cont):
    page = Page()
    cont = postproc(cont)
    page.head = w.head(
        {},
        [
            w.link({"rel": '"stylesheet"', "href": '"/style.css"'}),
            w.meta(
                {
                    "name": '"viewport"',
                    "content": '"width=device-width, initial-scale=1.0"',
                }
            ),
        ],
    )
    page.body = _md2html(cont, page)

    if int(page.attrs.get("toc", "0")):
        page.body = w.Joined([toc(page), page.body])

    return page
