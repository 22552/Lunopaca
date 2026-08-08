from __future__ import annotations

import inspect
import re
import ssl
from dataclasses import dataclass
from socketserver import StreamRequestHandler, ThreadingTCPServer
from typing import Callable, Mapping
from urllib.parse import unquote, urlsplit

__all__ = [
    "Lunopaca",
    "Request",
    "Response",
    "Input",
    "SensitiveInput",
    "Redirect",
    "TemporaryFailure",
    "PermanentFailure",
    "ClientCertificateRequired",
]


_GEMINI_MAX_REQUEST = 1024
_GEMINI_MAX_META = 1024
_ROUTE_PARAM = re.compile(r"<([A-Za-z_][A-Za-z0-9_]*)>")


@dataclass(slots=True, frozen=True)
class Request:
    url: str
    scheme: str
    host: str
    port: int
    path: str
    query: str
    params: Mapping[str, str]


@dataclass(slots=True, frozen=True)
class Response:
    body: str = ""
    status: int = 20
    meta: str = "text/gemini; charset=utf-8"

    def __post_init__(self) -> None:
        if not 10 <= self.status <= 69:
            raise ValueError("Gemini status must be between 10 and 69")
        if "\r" in self.meta or "\n" in self.meta:
            raise ValueError("response meta must not contain CR or LF")
        if len(self.meta.encode("utf-8")) > _GEMINI_MAX_META:
            raise ValueError("response meta exceeds 1024 bytes")

    def encode(self) -> bytes:
        head = f"{self.status:02d} {self.meta}\r\n".encode("utf-8")
        if self.status // 10 == 2:
            return head + self.body.encode("utf-8")
        return head


class Input(Response):
    def __init__(self, prompt: str = "Input"):
        super().__init__(status=10, meta=prompt)


class SensitiveInput(Response):
    def __init__(self, prompt: str = "Input"):
        super().__init__(status=11, meta=prompt)


class Redirect(Response):
    def __init__(self, target: str, *, permanent: bool = False):
        super().__init__(status=31 if permanent else 30, meta=target)


class TemporaryFailure(Response):
    def __init__(self, message: str = "Temporary failure", *, status: int = 40):
        if status // 10 != 4:
            raise ValueError("temporary failure status must be 4x")
        super().__init__(status=status, meta=message)


class PermanentFailure(Response):
    def __init__(self, message: str = "Permanent failure", *, status: int = 50):
        if status // 10 != 5:
            raise ValueError("permanent failure status must be 5x")
        super().__init__(status=status, meta=message)


class ClientCertificateRequired(Response):
    def __init__(self, message: str = "Client certificate required", *, status: int = 60):
        if status // 10 != 6:
            raise ValueError("certificate status must be 6x")
        super().__init__(status=status, meta=message)


Handler = Callable[[Request], Response | str]
ErrorHandler = Callable[[Exception, Request], Response | str]


@dataclass(slots=True, frozen=True)
class _Route:
    pattern: str
    regex: re.Pattern[str]
    handler: Handler


def _compile_route(path: str) -> re.Pattern[str]:
    cursor = 0
    parts: list[str] = ["^"]
    for match in _ROUTE_PARAM.finditer(path):
        parts.append(re.escape(path[cursor : match.start()]))
        parts.append(fr"(?P<{match.group(1)}>[^/]+)")
        cursor = match.end()
    parts.append(re.escape(path[cursor:]))
    parts.append("$")
    return re.compile("".join(parts))


class Lunopaca:
    def __init__(self) -> None:
        self._static_routes: dict[str, Handler] = {}
        self._dynamic_routes: list[_Route] = []
        self._error_handler: ErrorHandler | None = None

    def route(self, path: str):
        if not path.startswith("/"):
            raise ValueError("route paths must start with '/'")

        def decorator(func: Handler) -> Handler:
            if _ROUTE_PARAM.search(path):
                self._dynamic_routes.append(_Route(path, _compile_route(path), func))
            else:
                self._static_routes[path] = func
            return func

        return decorator

    def errorhandler(self, func: ErrorHandler) -> ErrorHandler:
        self._error_handler = func
        return func

    def _resolve(self, path: str) -> tuple[Handler | None, dict[str, str]]:
        handler = self._static_routes.get(path)
        if handler is not None:
            return handler, {}

        for route in self._dynamic_routes:
            match = route.regex.fullmatch(path)
            if match:
                return route.handler, {k: unquote(v) for k, v in match.groupdict().items()}
        return None, {}

    def dispatch(self, url: str) -> Response:
        parsed = urlsplit(url)
        if parsed.scheme != "gemini" or not parsed.hostname:
            return PermanentFailure("Bad request", status=59)

        try:
            port = parsed.port or 1965
        except ValueError:
            return PermanentFailure("Bad request", status=59)

        handler, params = self._resolve(parsed.path or "/")
        request = Request(
            url=url,
            scheme=parsed.scheme,
            host=parsed.hostname,
            port=port,
            path=parsed.path or "/",
            query=parsed.query,
            params=params,
        )

        if handler is None:
            return PermanentFailure("Not found", status=51)

        try:
            result = handler(request)
            if inspect.isawaitable(result):
                return TemporaryFailure("Async handlers are not supported", status=42)
            return self._coerce_response(result)
        except Exception as exc:
            if self._error_handler is not None:
                try:
                    return self._coerce_response(self._error_handler(exc, request))
                except Exception:
                    pass
            return TemporaryFailure()

    @staticmethod
    def _coerce_response(result: Response | str) -> Response:
        if isinstance(result, Response):
            return result
        if isinstance(result, str):
            return Response(result)
        return TemporaryFailure("Handler returned an invalid response", status=42)

    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 1965,
        *,
        certfile: str,
        keyfile: str,
        backlog: int = 128,
    ) -> None:
        app = self
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile, keyfile)

        class GeminiHandler(StreamRequestHandler):
            def handle(self) -> None:
                raw = self.rfile.readline(_GEMINI_MAX_REQUEST + 1)
                if len(raw) > _GEMINI_MAX_REQUEST or not raw.endswith(b"\r\n"):
                    self.wfile.write(PermanentFailure("Bad request", status=59).encode())
                    return

                try:
                    url = raw[:-2].decode("utf-8")
                except UnicodeDecodeError:
                    self.wfile.write(PermanentFailure("Bad request", status=59).encode())
                    return

                parsed = urlsplit(url)
                if parsed.scheme != "gemini" or not parsed.hostname:
                    self.wfile.write(PermanentFailure("Bad request", status=59).encode())
                    return

                self.wfile.write(app.dispatch(url).encode())

        class GeminiServer(ThreadingTCPServer):
            allow_reuse_address = True
            request_queue_size = backlog
            daemon_threads = True

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
