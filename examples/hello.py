from lunopaca import Lunopaca

app = Lunopaca()


@app.route("/")
def index(request):
    return """# Lunopaca

Hello from Gemini.

=> /hello Say hello
"""


@app.route("/hello")
def hello(request):
    return "# Hello, Gemini!"


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=1965,
        certfile="cert.pem",
        keyfile="key.pem",
    )
