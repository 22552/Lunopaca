from __future__ import annotations

import inspect
import ssl
from dataclasses import dataclass
from socketserver import StreamRequestHandler, ThreadingTCPServer
from typing import Callable
from urllib.parse import urlsplit


__all__ = [
    "Lunopaca",
    "Request",
    "Response",
    "Input",
    "SensitiveInput",
    "Redirect",
]


@dataclass(slots=True, frozen=True)
class Request:
    url: str
    path: str
    query: str


@dataclass(slots=True, frozen=True)
class Response:
    body: str = ""
    status: int = 20
    meta: str = "text/gemini; charset=utf-8"

    def encode(self) -> bytes:
        head = f"{self.status:02d} {self.meta}\r\n"
        if self.status // 10 == 2:
            return head.encode("utf-8") + self.body.encode("utf-8")
        return head.encode("utf-8")


class Input(Response):
    def __init__(self, prompt: str = "Input"):
        super().__init__(status=10, meta=prompt)


class SensitiveInput(Response):
    def __init__(self, prompt: str = "Input"):
        super().__init__(status=11, meta=prompt)


class Redirect(Response):
    def __init__(self, target: str, *, permanent: bool = False):
        super().__init__(status=31 if permanent else 30, meta=target)


Handler = Callable[[Request], Response | str]


class Lunopaca:
    def __init__(self) -> None:
        self._routes: dict[str, Handler] = {}

    def route(self, path: str):
        if not path.startswith("/"):
            raise ValueError("route paths must start with '/'")

        def decorator(func: Handler) -> Handler:
            self._routes[path] = func
            return func

        return decorator

    def dispatch(self, url: str) -> Response:
        parsed = urlsplit(url)
        request = Request(url=url, path=parsed.path or "/", query=parsed.query)
        handler = self._routes.get(request.path)

        if handler is None:
            return Response(status=51, meta="Not found")

        try:
            result = handler(request)
            if inspect.isawaitable(result):
                return Response(status=42, meta="Async handlers are not supported")
            if isinstance(result, Response):
                return result
            if isinstance(result, str):
                return Response(result)
            return Response(status=42, meta="Handler returned an invalid response")
        except Exception:
            return Response(status=42, meta="Temporary failure")

    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 1965,
        *,
        certfile: str,
        keyfile: str,
    ) -> None:
        app = self
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile, keyfile)

        class GeminiHandler(StreamRequestHandler):
            def handle(self) -> None:
                raw = self.rfile.readline(1025)
                if len(raw) > 1024 or not raw.endswith(b"\r\n"):
                    self.wfile.write(Response(status=59, meta="Bad request").encode())
                    return

                try:
                    url = raw[:-2].decode("utf-8")
                except UnicodeDecodeError:
                    self.wfile.write(Response(status=59, meta="Bad request").encode())
                    return

                parsed = urlsplit(url)
                if parsed.scheme != "gemini" or not parsed.hostname:
                    self.wfile.write(Response(status=59, meta="Bad request").encode())
                    return

                self.wfile.write(app.dispatch(url).encode())

        class GeminiServer(ThreadingTCPServer):
            allow_reuse_address = True

            def get_request(self):
                sock, addr = super().get_request()
                try:
                    return context.wrap_socket(sock, server_side=True), addr
                except Exception:
                    sock.close()
                    raise

        with GeminiServer((host, port), GeminiHandler) as server:
            print(f"Lunopaca serving Gemini on gemini://{host}:{port}")
            server.serve_forever()
