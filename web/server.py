"""Static server for the specimen page, plus a .ttf upload endpoint.

Python standard library only - no pip install, no build step. Run it:

    python web/server.py                    # http://127.0.0.1:8000
    python web/server.py --port 8080 --uploads /var/lib/fontmaker

Fonts are served from two directories: the ones bundled in the repo, and an
uploads directory that is the only thing that needs to be writable (and the
only thing worth putting on a volume).
"""

import argparse
import json
import os
import posixpath
import re
import shutil
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

HERE = os.path.dirname(os.path.abspath(__file__))

MAX_UPLOAD = 8 * 1024 * 1024
# Uploads are open to whoever can reach the page, so the directory needs a
# ceiling as well as a per-file one. Replacing an existing name is always
# allowed; only growing past this is refused.
MAX_UPLOADS = 250
SAFE_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._ -]{0,79}$')
FONT_EXT = ('.ttf', '.otf')
# sfnt magic: TrueType, Apple TrueType, CFF/OpenType, TrueType collection
FONT_MAGIC = (b'\x00\x01\x00\x00', b'true', b'OTTO', b'ttcf')

# Static assets are matched by shape, not listed by name: a bare filename in
# this directory with one of these extensions. Anything else - server.py, a
# stray note, a key someone dropped alongside it - is not reachable.
STATIC = re.compile(r'^[A-Za-z0-9_-]+\.(html|js|css|svg|ico|png)$')

TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.json': 'application/json',
    '.ttf': 'font/ttf',
    '.otf': 'font/otf',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.ico': 'image/x-icon',
}


class Config(object):
    bundled = os.path.join(HERE, 'fonts')
    uploads = os.path.join(HERE, 'fonts')
    read_only = False


def font_dirs():
    dirs = [Config.bundled]
    if os.path.abspath(Config.uploads) != os.path.abspath(Config.bundled):
        dirs.append(Config.uploads)
    return dirs


def list_fonts():
    """Every font on offer. Uploads shadow bundled files of the same name."""
    found = {}
    for d in font_dirs():
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.lower().endswith(FONT_EXT):
                continue
            path = os.path.join(d, fn)
            if not os.path.isfile(path):
                continue
            st = os.stat(path)
            found[fn] = {
                'file': fn,
                'name': os.path.splitext(fn)[0],
                'size': st.st_size,
                'mtime': int(st.st_mtime),
            }
    return sorted(found.values(), key=lambda f: f['name'].lower())


def resolve_font(name):
    """Locate a font by filename, refusing anything that escapes the dirs."""
    if not SAFE_NAME.match(name) or not name.lower().endswith(FONT_EXT):
        return None
    for d in reversed(font_dirs()):
        path = os.path.join(d, name)
        if os.path.isfile(path) and os.path.dirname(os.path.abspath(path)) \
                == os.path.abspath(d):
            return path
    return None


class Handler(BaseHTTPRequestHandler):
    server_version = 'fontmaker'
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (time.strftime('%H:%M:%S'), fmt % args))

    # -- helpers ---------------------------------------------------------
    def send(self, code, body=b'', ctype='text/plain; charset=utf-8',
             extra=None):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def send_json(self, code, obj):
        self.send(code, json.dumps(obj), 'application/json')

    def refuse(self, code, error):
        """Reject a request whose body we are not going to read.

        Drains what the client is already sending, capped so a declared 10 GB
        cannot tie us up, then closes rather than leaving a partly-read body on
        a keep-alive connection.
        """
        try:
            length = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            length = 0
        self.drain(min(max(length, 0), MAX_UPLOAD + 65536))
        self.close_connection = True
        return self.send_json(code, {'error': error})

    def drain(self, n, chunk=65536):
        """Read and discard n bytes, so a rejected request still gets its
        response instead of a reset connection. A client that gives up
        mid-send is fine - we are throwing the bytes away regardless."""
        try:
            while n > 0:
                got = self.rfile.read(min(chunk, n))
                if not got:
                    break
                n -= len(got)
        except OSError:
            pass

    def send_file(self, path, cache='no-cache'):
        try:
            with open(path, 'rb') as fh:
                body = fh.read()
        except OSError:
            return self.send(404, 'not found')
        ext = os.path.splitext(path)[1].lower()
        self.send(200, body, TYPES.get(ext, 'application/octet-stream'),
                  {'Cache-Control': cache})

    # -- routes ----------------------------------------------------------
    def do_GET(self):
        url = urlparse(self.path)
        path = unquote(url.path)

        if path == '/api/fonts':
            return self.send_json(200, {
                'fonts': list_fonts(),
                'readOnly': Config.read_only,
            })

        if path.startswith('/fonts/'):
            name = posixpath.basename(path)
            target = resolve_font(name)
            if not target:
                return self.send(404, 'no such font')
            return self.send_file(target, 'public, max-age=60')

        if path in ('/', '/index.html'):
            return self.send_file(os.path.join(HERE, 'index.html'))

        name = posixpath.basename(path)
        if path == '/' + name and STATIC.match(name):
            local = os.path.join(HERE, name)
            if os.path.isfile(local):
                return self.send_file(local)
        return self.send(404, 'not found')

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        url = urlparse(self.path)
        if unquote(url.path) != '/api/fonts':
            return self.send(404, 'not found')
        if Config.read_only:
            return self.refuse(403, 'uploads are disabled')

        try:
            length = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            return self.refuse(400, 'bad length')
        if length <= 0:
            return self.send_json(400, {'error': 'empty body'})
        if length > MAX_UPLOAD:
            return self.refuse(413, 'over %d bytes' % MAX_UPLOAD)

        # The body is read before anything else is judged, because a response
        # sent while the client is still uploading arrives as a reset
        # connection rather than as the error it is.
        body = self.rfile.read(length)
        if len(body) != length:
            return self.send_json(400, {'error': 'short read'})

        # Reject anything path-shaped outright rather than quietly basenaming
        # it: a caller asking for ../x.ttf has misunderstood the endpoint.
        name = unquote((parse_qs(url.query).get('name') or [''])[0])
        if ('/' in name or '\\' in name or name != posixpath.basename(name)
                or not SAFE_NAME.match(name)
                or not name.lower().endswith(FONT_EXT)):
            return self.send_json(400, {'error': 'bad filename'})
        if not body.startswith(FONT_MAGIC):
            return self.send_json(415, {'error': 'not a TrueType/OpenType file'})

        os.makedirs(Config.uploads, exist_ok=True)
        dest = os.path.join(Config.uploads, name)
        if not os.path.exists(dest):
            held = sum(1 for f in os.listdir(Config.uploads)
                       if f.lower().endswith(FONT_EXT))
            if held >= MAX_UPLOADS:
                return self.send_json(507, {
                    'error': 'upload directory is full (%d)' % MAX_UPLOADS})
        fd, tmp = tempfile.mkstemp(dir=Config.uploads, suffix='.part')
        try:
            with os.fdopen(fd, 'wb') as fh:
                fh.write(body)
            # mkstemp gives 0600, which on a bind-mounted host directory means
            # nobody outside the container can read what was uploaded.
            os.chmod(tmp, 0o644)
            os.replace(tmp, dest)
        except OSError as exc:
            if os.path.exists(tmp):
                os.unlink(tmp)
            return self.send_json(500, {'error': str(exc)})

        self.log_message('stored %s (%d bytes)', name, len(body))
        return self.send_json(201, {'file': name,
                                    'name': os.path.splitext(name)[0]})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--host', default='0.0.0.0')
    ap.add_argument('--port', type=int, default=8000)
    ap.add_argument('--fonts', default=Config.bundled,
                    help='directory of fonts shipped with the app')
    ap.add_argument('--uploads', default=None,
                    help='writable directory for uploads (default: --fonts)')
    ap.add_argument('--read-only', action='store_true',
                    help='serve the page but refuse uploads')
    args = ap.parse_args()

    Config.bundled = os.path.abspath(args.fonts)
    Config.uploads = os.path.abspath(args.uploads or args.fonts)
    Config.read_only = args.read_only
    os.makedirs(Config.uploads, exist_ok=True)

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print("fonts   : %s" % ', '.join(font_dirs()))
    print("uploads : %s" % ('disabled' if Config.read_only else Config.uploads))
    print("serving : http://%s:%d" % (
        '127.0.0.1' if args.host in ('0.0.0.0', '') else args.host, args.port))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
