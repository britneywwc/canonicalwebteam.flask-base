# Standard library
import os
import unittest
import warnings
from contextlib import contextmanager

# Packages
import talisker.testing
from werkzeug.contrib.fixers import ProxyFix
from werkzeug.debug import DebuggedApplication

# Local modules
from canonicalwebteam.flask_base.app import FlaskBase
from tests.test_app.webapp.app import create_test_app


@contextmanager
def cwd(path):
    """
    Context manager for temporarily changing directory
    """

    oldpwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldpwd)


class TestFlaskBase(unittest.TestCase):
    def setUp(self):
        talisker.testing.configure_testing()

    def create_app(self, debug=False):
        if debug:
            os.environ["FLASK_DEBUG"] = "true"
        else:
            os.environ.pop("FLASK_DEBUG", None)
        app = FlaskBase(__name__, "canonicalwebteam.flask-base")
        return app

    def test_flask_base_inits(self):
        app = self.create_app()
        self.assertEqual(app.service, "canonicalwebteam.flask-base")

    def test_debug_wsgi_app(self):
        app = self.create_app(debug=True)
        self.assertIsInstance(app.wsgi_app, DebuggedApplication)

    def test_wsgi_app(self):
        app = self.create_app()
        self.assertIsInstance(app.wsgi_app, ProxyFix)

    def test_redirects_deleted(self):
        """
        Check test_app/{redirects,permanent-redirects,deleted}.yaml
        are processed correctly
        """

        with create_test_app().test_client() as client:
            redirect_response = client.get("redirect")
            self.assertEqual(302, redirect_response.status_code)
            self.assertEqual(
                redirect_response.headers.get("Location"),
                "https://httpbin.org/",
            )

            permanent_response = client.get("permanent-redirect")
            self.assertEqual(301, permanent_response.status_code)
            self.assertEqual(
                permanent_response.headers.get("Location"),
                "https://example.com/",
            )

            deleted_response = client.get("deleted")
            self.assertEqual(410, deleted_response.status_code)
            self.assertEqual(deleted_response.data, b"Deleted")

    def test_logs_service_name(self):
        with talisker.testing.TestContext() as ctx:
            app = self.create_app()
            app.logger.info("Test")
            ctx.assert_log(
                msg="Test", extra={"service": "canonicalwebteam.flask-base"}
            )

    def test_global_context(self):
        app = self.create_app()
        context_processors = app.template_context_processors[None]

        # Flask adds it's own context_processor so we should have 2
        self.assertEqual(len(context_processors), 2)

        # We retrieve our base context from the second position
        base_context = context_processors[1]()

        self.assertIn("now", base_context.keys())
        self.assertIn("versioned_static", base_context.keys())

    def test_favicon_redirect(self):
        """
        If `favicon_url` is provided, check requests to `/favicon.ico`
        receive a redirect
        """

        external_url = "https://example.com/icos/favcon"
        local_url = "/static/some-image.ico"

        external_app = FlaskBase(
            __name__, "canonicalwebteam.flask-base", favicon_url=external_url
        )
        local_app = FlaskBase(
            __name__, "canonicalwebteam.flask-base", favicon_url=local_url
        )

        with external_app.test_client() as client:
            response = client.get("/favicon.ico")
            self.assertEqual(302, response.status_code)
            self.assertEqual(response.headers.get("Location"), external_url)

        with local_app.test_client() as client:
            response = client.get("/favicon.ico")
            self.assertEqual(302, response.status_code)
            self.assertEqual(
                response.headers.get("Location"),
                "http://localhost" + local_url,
            )

    def test_robots_humans(self):
        """
        If `robots.txt` and `humans.txt` are provided at the root of the
        project, check requests to `/robots.txt` load the content
        """

        with create_test_app().test_client() as client:
            warnings.simplefilter("ignore", ResourceWarning)
            robots_response = client.get("robots.txt")
            humans_response = client.get("humans.txt")
            self.assertEqual(200, robots_response.status_code)
            self.assertEqual(200, humans_response.status_code)
            self.assertEqual(robots_response.data, b"robots!")
            self.assertEqual(humans_response.data, b"humans!")

    def test_error_pages(self):
        """
        If "404.html" and "500.html" are provided as templates,
        check we get the response from those templates when we get an error
        """

        with create_test_app().test_client() as client:
            response = client.get("non-existent-page")
            self.assertEqual(404, response.status_code)
            self.assertEqual(response.data, b"error 404")

            response = client.get("error")
            self.assertEqual(500, response.status_code)
            self.assertEqual(response.data, b"error 500")


if __name__ == "__main__":
    unittest.main()
