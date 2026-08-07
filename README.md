# Lunopaca

A tiny Python framework for the Gemini protocol.

Lunopaca keeps the surface intentionally small: routes, requests, responses, and a TLS Gemini server using only the Python standard library.

## Example

```python
from lunopaca import Lunopaca, Input, Redirect

app = Lunopaca()

@app.route("/")
def index(request):
    return """# Lunopaca

A tiny Gemini framework for Python.

=> /hello Hello
=> /search Search
"""

@app.route("/hello")
def hello(request):
    return "# Hello, Gemini!"

@app.route("/search")
def search(request):
    if not request.query:
        return Input("Search query")
    return f"# Search\n\nYou searched for: {request.query}"

@app.route("/old")
def old(request):
    return Redirect("gemini://example.com/new")

app.run(
    host="0.0.0.0",
    port=1965,
    certfile="cert.pem",
    keyfile="key.pem",
)
```

## Response helpers

- `Response(body, status=20, meta="text/gemini; charset=utf-8")`
- `Input(prompt)` → status `10`
- `SensitiveInput(prompt)` → status `11`
- `Redirect(target, permanent=False)` → status `30` or `31`

Returning a plain string from a route automatically produces a successful `20 text/gemini` response.

## Philosophy

- Gemini only
- Standard-library only
- Small, readable core
- No ASGI or WSGI abstraction
- No HTML-oriented concepts

## Status

Lunopaca is experimental and not yet released on PyPI.
