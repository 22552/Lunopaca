# Lunopaca

A tiny, standard-library-only Python framework for the Gemini protocol.

Lunopaca aims to stay small without being toy-only: routing, dynamic path parameters, middleware, mounts, named routes, response helpers, TLS serving, client-certificate metadata, logging hooks, and lightweight error handling all live in a single module.

## Example

```python
from lunopaca import Lunopaca, Input, Redirect

app = Lunopaca()

@app.use
def timing(request, next_handler):
    return next_handler(request)

@app.route("/", name="home")
def index(request):
    return """# Lunopaca

A tiny Gemini framework for Python.

=> /hello/world Dynamic route
=> /search Search
"""

@app.route("/hello/<name>", name="hello")
def hello(request):
    return f"# Hello, {request.params['name']}!"

@app.route("/search")
def search(request):
    if not request.query:
        return Input("Search query")
    return f"# Search\n\nYou searched for: {request.query}"

@app.route("/old")
def old(request):
    return Redirect("gemini://example.com/new")

@app.logger
def log(request, response):
    print(request.path, response.status)

app.run(
    host="0.0.0.0",
    port=1965,
    certfile="cert.pem",
    keyfile="key.pem",
)
```

## Routing

Dynamic route parameters use `<name>` syntax:

```python
@app.route("/users/<name>", name="user")
def user(request):
    return f"# {request.params['name']}"
```

Named routes can be reversed:

```python
app.url_for("user", name="Luna Opaca")
# /users/Luna%20Opaca
```

A sub-application can be mounted under a prefix:

```python
api = Lunopaca()

@api.route("/status")
def status(request):
    return "# OK"

app.mount("/api", api)
```

## Request

Each handler receives a `Request` object with:

- `url`
- `scheme`
- `host`
- `port`
- `path`
- `query`
- `params`
- `client_address`
- `client_certificate`

`client_certificate` is populated when a TLS peer certificate is available. Certificate policy and trust remain application concerns.

## Middleware

Middleware wraps route handlers in registration order:

```python
@app.use
def middleware(request, next_handler):
    response = next_handler(request)
    return response
```

Middleware may return either a `Response` or a plain string.

## Responses

Returning a plain string automatically creates a successful `20 text/gemini; charset=utf-8` response.

Helpers:

- `Response(body, status=20, meta="text/gemini; charset=utf-8")`
- `Input(prompt)` → `10`
- `SensitiveInput(prompt)` → `11`
- `Success(body, mime="text/gemini; charset=utf-8")` → `20`
- `Redirect(target, permanent=False)` → `30` / `31`
- `TemporaryFailure(message, status=40)` → any `4x` status
- `PermanentFailure(message, status=50)` → any `5x` status
- `ClientCertificateRequired(message, status=60)` → any `6x` status

Lunopaca validates response status codes and prevents CR/LF injection in response metadata.

## Errors and logging

```python
@app.errorhandler
def errors(exc, request):
    return "# Error\n\nSomething went wrong."

@app.logger
def logger(request, response):
    print(request.host, request.path, response.status)
```

Logging-hook failures are ignored so they cannot break request handling.

## TLS and client certificates

`run()` creates a TLS Gemini server using Python's `ssl` module.

```python
app.run(
    certfile="cert.pem",
    keyfile="key.pem",
    request_client_certificates=True,
)
```

An optional `cafile` may be supplied when configuring client-certificate verification.

## Design

- Gemini only
- Python standard library only
- One-file core
- No ASGI or WSGI abstraction
- Synchronous handlers
- Dynamic routes without a separate router dependency
- Middleware and mountable sub-apps
- TLS server included
- Client-certificate metadata exposed without imposing an authentication model

## Testing

```bash
python -m unittest discover -s tests -v
```

GitHub Actions runs the suite on Python 3.11, 3.12, and 3.13.

## Install

Once published to PyPI:

```bash
pip install lunopaca
```

For local development:

```bash
pip install -e .
```

## Status

Lunopaca is intentionally compact, but the core API is intended to be useful for real Gemini capsules. It is not yet published on PyPI.
