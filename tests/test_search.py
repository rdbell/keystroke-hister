import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.parse import parse_qs, urlsplit

spec = importlib.util.spec_from_file_location("hister_search", Path(__file__).parents[1] / "bin/search.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        self.server.seen.append((self.path, dict(self.headers)))
        query = json.loads(parse_qs(urlsplit(self.path).query)["query"][0])
        text = query["text"]
        status, body = 200, {"total": 1, "documents": [
            {"title": "Example Domain", "url": "https://example.com/", "html": "excluded", "text": "excluded"}]}
        if text == "empty":
            body = {"total": 0, "documents": None}
        elif text == "auth":
            status, body = 401, {"secret": "must not appear in errors"}
        elif text == "bad":
            status, body = 400, {}
        elif text == "broken":
            body = "not JSON"
        elif text == "huge":
            body = "x" * (helper.MAX_RESPONSE + 1)
        elif text == "redirect":
            self.send_response(302)
            self.send_header("Location", "/should-not-be-requested")
            self.end_headers()
            return
        elif text == "slow":
            time.sleep(0.2)
        raw = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.daemon_threads = True
        cls.server.seen = []
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_query_encoding_and_minimal_result(self):
        text = 'café + "linux" & $(echo nope)'
        result = helper.search(self.url + "/base", text, 3)
        self.assertEqual(result, {"results": [{"title": "Example Domain", "url": "https://example.com/"}]})
        path, headers = self.server.seen[-1]
        self.assertTrue(path.startswith("/base/search?"))
        query = json.loads(parse_qs(urlsplit(path).query)["query"][0])
        self.assertEqual(query["text"], text)
        self.assertEqual(query["limit"], 3)
        self.assertFalse(query["include_html"])
        self.assertFalse(query["include_text"])
        self.assertEqual(headers["Accept"], "application/json")

    def test_token_is_header_only(self):
        with tempfile.TemporaryDirectory() as temp:
            token = Path(temp) / "token"
            token.write_text("synthetic-test-token\n")
            helper.search(self.url, "example", token_file=str(token))
        path, headers = self.server.seen[-1]
        self.assertEqual(headers["X-Access-Token"], "synthetic-test-token")
        self.assertNotIn("synthetic-test-token", path)

    def test_empty_archive(self):
        self.assertEqual(helper.search(self.url, "empty"), {"results": []})

    def test_errors_are_actionable_and_do_not_echo_bodies(self):
        for query, expected in [("auth", "requires authentication"), ("bad", "parse this query"),
                                ("broken", "unreadable"), ("huge", "too large")]:
            with self.subTest(query=query):
                with self.assertRaisesRegex(helper.SearchError, expected) as error:
                    helper.search(self.url, query)
                self.assertNotIn("secret", str(error.exception))

    def test_redirect_is_not_followed(self):
        before = len(self.server.seen)
        with self.assertRaisesRegex(helper.SearchError, "HTTP 302"):
            helper.search(self.url, "redirect")
        self.assertEqual(len(self.server.seen), before + 1)

    def test_timeout(self):
        with self.assertRaisesRegex(helper.SearchError, "timed out"):
            helper.search(self.url, "slow", timeout=0.03)

    def test_invalid_server_urls(self):
        for url in ["file:///etc/passwd", "https://user:pass@example.com", "http://localhost:bad",
                    "http://localhost/#fragment", "http://localhost/?token=secret", "not-a-url"]:
            with self.subTest(url=url), self.assertRaises(helper.SearchError):
                helper.search(url, "example")

    def test_document_safety_and_order(self):
        docs = [
            {"url": "javascript:alert(1)", "title": "bad"},
            {"url": "file:///etc/passwd"}, {"url": "https://user:pass@example.com"},
            {"url": "https://example.com/", "title": " First\n page "},
            {"url": "https://example.com/", "title": "duplicate"},
            {"url": "https://example.org/", "title": None},
            {"url": "https://example.net/", "title": "third"},
        ]
        self.assertEqual(helper.normalize({"documents": docs}, 2)["results"], [
            {"url": "https://example.com/", "title": "First page"},
            {"url": "https://example.org/", "title": "https://example.org/"}])

    def test_invalid_schema(self):
        for value in [[], {}, {"documents": "not-a-list"}]:
            with self.assertRaises(helper.SearchError):
                helper.normalize(value, 12)


if __name__ == "__main__":
    unittest.main()
