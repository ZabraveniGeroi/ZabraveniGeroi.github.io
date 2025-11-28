import trio
import os
import mimetypes
import urllib.parse
import traceback

split = lambda path: path.strip('/').split('/')


class Request:
    def __init__(self) -> None:
        self.method: str
        self.path: str
        self.stream: trio.SocketStream
        self.headers: dict[str, str]
        self.args: dict[str, list[str]]
        self.server: Server
        self.contentLength: int

    async def readBody(self, n=None):
        return self.stream.receive_some(n)

    async def sendRaw(self, cont: bytes):
        await self.stream.send_all(cont)

    async def send(self, status: int, headers: dict[str, str], cont: bytes):
        await self.sendRaw(self.server.buildReq(status, headers, cont))


class Server:
    def __init__(self, host='0.0.0.0', port=8080, headers: None | dict = None):
        self.tree = {}
        self.host = host
        self.port = port
        self.headers = headers or {}

    async def fail(self, r: Request):
        await r.sendRaw('HTTP/1.1 404 Not Found'.encode())

    async def serverError(self, r: Request):
        await r.sendRaw('HTTP/1.1 505 Internal Server Error'.encode())

    async def start(self):
        await trio.serve_tcp(self.handle, port=self.port, host=self.host)

    def handler(self, path):
        def fn(f):
            parts = split(path)
            cur = self.tree

            for part in parts:
                if part not in cur:
                    cur[part] = {}
                cur = cur[part]

            # NOTE: '' indicates that this is the handler if we end up here
            cur[''] = f

        return fn

    def unserve(self, path):
        parts = split(path)
        cur = self.tree

        for part in parts:
            cur = cur[part]

        del cur['']

    def getHandler(self, path: str):
        cur = self.tree
        for part in path.split('/'):
            # first we check if there is an exact match
            # afterwards, we check for a '%' wildcard (single part is wildcard-ed)
            if not (new := cur.get(part)) and not (new := cur.get('%')):
                # if that also fails, we check for a '%%', which captures everything
                # NOTE: we set cur here, because we break, and so we will not reach ``cur = new``
                if not (cur := cur.get('%%')):
                    return None  # give up if that also doesnt exist
                break
            cur = new
        return cur.get('')

    def serving(self, path):
        return self.getHandler(path) is not None

    def buildReq(
        self, status: int, headers: dict[str, str], cont: bytes, l: int | None = None
    ):
        headers = {**self.headers, **headers}
        # TODO: support up to http v3
        return (
            f'HTTP/1.1 {status} OK\nContent-Length: {l or len(cont)}\n'
            + (
                '\n'.join([name + ': ' + val for name, val in headers.items()]) + '\n'
                if headers
                else ''
            )
            + '\n'
        ).encode() + cont

    async def handle(self, stream: trio.SocketStream):
        buf = b''
        lines = []
        headers = {}

        try:
            while c := await stream.receive_some(1):
                if c == b'\n':
                    if buf[-1] == ord('\r'):
                        buf = buf[:-1]

                    if not buf:
                        break

                    lines.append(buf)
                    buf = b''
                    continue

                buf += c

            # parse headers
            for l in lines[1:]:
                parts = l.decode().split(':')
                header = parts[0].strip().lower()
                value = ':'.join(parts[1:]).strip().lower()
                headers[header] = value

            method, path, ver = lines[0].decode().split(' ')
            parsed = urllib.parse.urlparse(path)
            path = urllib.parse.unquote_plus(parsed.path).strip('/')
            print(f'{method} {"/" + path} {ver}')

            r = Request()
            r.method = method
            r.path = parsed.path
            r.stream = stream
            r.headers = headers
            r.args = urllib.parse.parse_qs(parsed.query)
            r.contentLength = int(headers.get('content-length', '0'))
            r.server = self

            try:
                await (self.getHandler(path) or self.fail)(r)
            except BaseException as e:
                # this is a different try just because we might get an error in the handler
                await self.serverError(r)
                # traceback.print_exception(e)

            await stream.send_eof()
            await stream.aclose()
            return

        except:
            traceback.print_exc()
            print('connection closed')

    def genericServe(self, cont, path, fpath='', headers={}):
        send = self.buildReq(
            200, {**mtype(fpath or path, getEncoding(cont)), **headers}, cont
        )

        @self.handler(path)
        async def fn(r: Request):
            await r.sendRaw(send)

    def streamServe(self, path, url, fpath='', headers={}):
        s = os.path.getsize(path)
        send = self.buildReq(200, {**mtype(fpath or path, None), **headers}, b'', s)
        chunks = 4000000

        async def read(send, f, s):
            b = await f.read(s)
            await send.send(b)

        @self.handler(url)
        async def fn(r: Request):
            si = s
            await r.sendRaw(send)
            async with await trio.open_file(path, 'rb') as f:
                async with trio.open_nursery() as nurs:
                    dat = await f.read(chunks)
                    _send, recv = trio.open_memory_channel(chunks)
                    while si > 0:
                        nurs.start_soon(read, _send, f, min(si, chunks))
                        si -= chunks
                        await r.sendRaw(dat)
                        dat = await recv.receive()
                    await _send.aclose()

    async def serve(self, fpath, url=None, headers={}):
        url = url or fpath
        if os.path.getsize(fpath) > 16000000:  # 16mb
            self.streamServe(fpath, url, headers=headers)
        else:
            file = await trio.open_file(fpath, 'rb')
            self.genericServe(await file.read(), url, headers=headers)


def mtype(path, enc=None):
    return {
        'Content-Type': (mimetypes.guess_type(path, strict=True)[0] or 'text/html')
        + (f'; charset={enc}' if enc else '')
    }


def getEncoding(cont: bytes):
    encodings = ['utf-8', 'ascii']
    for e in encodings:
        try:
            cont.decode(e)
            return e
        except:
            pass
