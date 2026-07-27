"""The specimen server: listing, serving, and the upload guard rails.

Standard library only, matching the thing it tests:

    python -m unittest discover tests
"""

import importlib.util
import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("fm_server", ROOT / "web" / "server.py")
fm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fm)

# Smallest thing that passes the sfnt magic check.
FAKE_TTF = b"\x00\x01\x00\x00" + b"\x00" * 2000


def get(url, **kw):
    return urllib.request.urlopen(url, timeout=5, **kw)


def post(url, body, ctype="application/octet-stream"):
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": ctype})
    return urllib.request.urlopen(req, timeout=5)


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="fm-test-")
        cls.uploads = os.path.join(cls.tmp, "uploads")
        os.makedirs(cls.uploads)
        fm.Config.bundled = str(ROOT / "web" / "fonts")
        fm.Config.uploads = cls.uploads
        fm.Config.read_only = False

        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), fm.Handler)
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_port
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.thread.join(timeout=5)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # -- serving ---------------------------------------------------------
    def test_pages_and_assets_are_served(self):
        html = get(self.base + "/").read().decode()
        self.assertIn("app.js", html)
        self.assertIn("style.css", html)
        self.assertIn("showcase.html", html)
        for asset in ("app.js", "fontkit.js", "showcase.js"):
            self.assertIn("text/javascript",
                          get(self.base + "/" + asset).headers["Content-Type"])
        self.assertIn("demo-blog", get(self.base + "/showcase.html").read().decode())

    def test_source_next_to_the_page_is_not_served(self):
        for path in ("/server.py", "/../server.py", "/web/server.py"):
            with self.assertRaises(urllib.error.HTTPError, msg=path) as e:
                get(self.base + path)
            self.assertEqual(e.exception.code, 404, path)

    def test_listing_reports_the_bundled_fonts(self):
        data = json.loads(get(self.base + "/api/fonts").read())
        names = [f["file"] for f in data["fonts"]]
        on_disk = sorted(p.name for p in (ROOT / "web" / "fonts").glob("*.ttf"))
        self.assertTrue(on_disk, "no fonts bundled to test against")
        for name in on_disk:
            self.assertIn(name, names)

    def test_a_listed_font_downloads_intact(self):
        data = json.loads(get(self.base + "/api/fonts").read())
        first = data["fonts"][0]["file"]
        payload = get(self.base + "/fonts/" + first).read()
        self.assertEqual(payload,
                         (ROOT / "web" / "fonts" / first).read_bytes())

    # -- upload guard rails ----------------------------------------------
    def test_upload_round_trips(self):
        res = post(self.base + "/api/fonts?name=Probe.ttf", FAKE_TTF)
        self.assertEqual(res.status, 201)
        self.assertTrue(os.path.isfile(os.path.join(self.uploads, "Probe.ttf")))
        self.assertEqual(get(self.base + "/fonts/Probe.ttf").read(), FAKE_TTF)
        names = [f["file"] for f in
                 json.loads(get(self.base + "/api/fonts").read())["fonts"]]
        self.assertIn("Probe.ttf", names)

    def test_non_font_bytes_are_refused(self):
        with self.assertRaises(urllib.error.HTTPError) as e:
            post(self.base + "/api/fonts?name=evil.ttf", b"<?php echo 1; ?>")
        self.assertEqual(e.exception.code, 415)

    def test_traversal_and_odd_names_are_refused(self):
        for name in ("../../evil.ttf", "evil.php", "..%2Fevil.ttf", ""):
            with self.assertRaises(urllib.error.HTTPError, msg=name) as e:
                post(self.base + "/api/fonts?name=" + name, FAKE_TTF)
            self.assertEqual(e.exception.code, 400, name)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "evil.ttf")))
        self.assertFalse(os.path.exists(os.path.join(self.uploads, "evil.ttf")))

    def test_oversize_upload_is_refused(self):
        big = b"\x00\x01\x00\x00" + b"\x00" * (fm.MAX_UPLOAD + 10)
        with self.assertRaises(urllib.error.HTTPError) as e:
            post(self.base + "/api/fonts?name=Big.ttf", big)
        self.assertEqual(e.exception.code, 413)

    def test_fetching_outside_the_font_dirs_is_refused(self):
        for path in ("/fonts/..%2F..%2Fserver.py", "/fonts/server.py",
                     "/../server.py"):
            with self.assertRaises(urllib.error.HTTPError, msg=path) as e:
                get(self.base + path)
            self.assertEqual(e.exception.code, 404, path)

    def test_a_full_upload_directory_refuses_new_names_but_allows_replacing(self):
        original = fm.MAX_UPLOADS
        fm.MAX_UPLOADS = 2
        try:
            post(self.base + "/api/fonts?name=Cap1.ttf", FAKE_TTF)
            post(self.base + "/api/fonts?name=Cap2.ttf", FAKE_TTF)
            with self.assertRaises(urllib.error.HTTPError) as e:
                post(self.base + "/api/fonts?name=Cap3.ttf", FAKE_TTF)
            self.assertEqual(e.exception.code, 507)
            # replacing something already there is still fine
            self.assertEqual(
                post(self.base + "/api/fonts?name=Cap1.ttf", FAKE_TTF).status, 201)
        finally:
            fm.MAX_UPLOADS = original
            for n in ("Cap1.ttf", "Cap2.ttf"):
                p = os.path.join(self.uploads, n)
                if os.path.exists(p):
                    os.unlink(p)

    def test_read_only_mode_refuses_uploads(self):
        fm.Config.read_only = True
        try:
            with self.assertRaises(urllib.error.HTTPError) as e:
                post(self.base + "/api/fonts?name=Nope.ttf", FAKE_TTF)
            self.assertEqual(e.exception.code, 403)
        finally:
            fm.Config.read_only = False


if __name__ == "__main__":
    unittest.main()
