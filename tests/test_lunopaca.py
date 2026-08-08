import unittest

from lunopaca import (
    Input,
    Lunopaca,
    PermanentFailure,
    Redirect,
    Response,
    SensitiveInput,
    Success,
    TemporaryFailure,
)


class LunopacaTests(unittest.TestCase):
    def test_plain_string_response(self):
        app = Lunopaca()

        @app.route("/")
        def index(request):
            return "# Hello"

        response = app.dispatch("gemini://example.com/")
        self.assertEqual(response.status, 20)
        self.assertEqual(response.body, "# Hello")

    def test_not_found(self):
        app = Lunopaca()
        response = app.dispatch("gemini://example.com/missing")
        self.assertEqual(response.status, 51)

    def test_dynamic_route(self):
        app = Lunopaca()

        @app.route("/hello/<name>")
        def hello(request):
            return request.params["name"]

        response = app.dispatch("gemini://example.com/hello/Luna")
        self.assertEqual(response.body, "Luna")

    def test_url_for(self):
        app = Lunopaca()

        @app.route("/users/<name>", name="user")
        def user(request):
            return request.params["name"]

        self.assertEqual(app.url_for("user", name="Luna Opaca"), "/users/Luna%20Opaca")

    def test_mount(self):
        root = Lunopaca()
        child = Lunopaca()

        @child.route("/hello")
        def hello(request):
            return "mounted"

        root.mount("/api", child)
        response = root.dispatch("gemini://example.com/api/hello")
        self.assertEqual(response.body, "mounted")

    def test_middleware(self):
        app = Lunopaca()
        calls = []

        @app.use
        def middleware(request, next_handler):
            calls.append("before")
            response = next_handler(request)
            calls.append("after")
            return response

        @app.route("/")
        def index(request):
            calls.append("handler")
            return "ok"

        response = app.dispatch("gemini://example.com/")
        self.assertEqual(response.body, "ok")
        self.assertEqual(calls, ["before", "handler", "after"])

    def test_logger(self):
        app = Lunopaca()
        logged = []

        @app.logger
        def log(request, response):
            logged.append((request.path, response.status))

        @app.route("/")
        def index(request):
            return "ok"

        app.dispatch("gemini://example.com/")
        self.assertEqual(logged, [("/", 20)])

    def test_client_metadata(self):
        app = Lunopaca()

        @app.route("/")
        def index(request):
            self.assertEqual(request.client_address, ("127.0.0.1", 12345))
            self.assertEqual(request.client_certificate, {"subject": "test"})
            return "ok"

        response = app.dispatch(
            "gemini://example.com/",
            client_address=("127.0.0.1", 12345),
            client_certificate={"subject": "test"},
        )
        self.assertEqual(response.status, 20)

    def test_helpers(self):
        self.assertEqual(Input("q").status, 10)
        self.assertEqual(SensitiveInput("q").status, 11)
        self.assertEqual(Success("ok").status, 20)
        self.assertEqual(Redirect("gemini://example.com").status, 30)
        self.assertEqual(Redirect("gemini://example.com", permanent=True).status, 31)
        self.assertEqual(TemporaryFailure().status, 40)
        self.assertEqual(PermanentFailure().status, 50)

    def test_response_meta_rejects_newlines(self):
        with self.assertRaises(ValueError):
            Response(status=20, meta="text/gemini\r\n59 injected")

    def test_error_handler(self):
        app = Lunopaca()

        @app.route("/")
        def broken(request):
            raise RuntimeError("boom")

        @app.errorhandler
        def errors(exc, request):
            return Response("# handled")

        response = app.dispatch("gemini://example.com/")
        self.assertEqual(response.status, 20)
        self.assertEqual(response.body, "# handled")


if __name__ == "__main__":
    unittest.main()
