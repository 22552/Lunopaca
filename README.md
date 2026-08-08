# Lunopaca

A tiny, standard-library-only Python framework for the Gemini protocol.

Lunopaca intentionally keeps the surface small: routing, requests, responses, TLS serving, dynamic path parameters, and lightweight error handling.

## Example

```python
from lunopaca import Lunopaca, Input, Redirect

app = Lunopaca()

@app.route("/")
def index(request):
    return """# Lunopaca

A tiny Gemini framework for Python.

=> /hello/world Dynamic route
=> /search Search
"""

@app.route("/hello/<name>")
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

@app.errorhandler
def errors(exc, request):
    return f"# Error\n\nSomething went wrong at {request.path}."

app.run(
    host="0.0.0.0",
    port=1965,
    certfile="cert.pem",
    keyfile="key.pem",
)
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

Dynamic route parameters use `<name>` syntax:

```python
@app.route("/users/<name>")
def user(request):
    return f"# {request.params['name']}"
```

## Responses

Returning a plain string automatically creates a successful `20 text/gemini; charset=utf-8` response.

Helpers:

- `Response(body, status=20, meta="text/gemini; charset=utf-8")`
- `Input(prompt)` → `10`
- `SensitiveInput(prompt)` → `11`
- `Redirect(target, permanent=False)` → `30` / `31`
- `TemporaryFailure(message, status=40)` → any `4x` status
- `PermanentFailure(message, status=50)` → any `5x` status
- `ClientCertificateRequired(message, status=60)` → any `6x` status

Lunopaca validates response status codes and prevents CR/LF injection in response metadata.

## Design

- Gemini only
- Python standard library only
- One-file core
- No ASGI or WSGI abstraction
- Synchronous handlers
- Dynamic routes without a separate router dependency
- TLS server included

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

Lunopaca is small by design, but the core API is usable as a complete Gemini micro-framework. It is not yet published on PyPI.
