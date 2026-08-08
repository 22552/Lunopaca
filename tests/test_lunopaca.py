import unittest

from lunopaca import (
    Input,
    Lunopaca,
    PermanentFailure,
    Redirect,
    Response,
    SensitiveInput,
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

    def test_helpers(self):
        self.assertEqual(Input("q").status, 10)
        self.assertEqual(SensitiveInput("q").status, 11)
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
