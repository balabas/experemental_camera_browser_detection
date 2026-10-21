#!/usr/bin/env python3
"""Dev server: serves this folder + a mock price API, and logs every API request.

    python3 server.py                      # http://localhost:8000
    python3 server.py --delay 0.8          # slower fake API
    python3 server.py --cert cert.pem --key key.pem --host 0.0.0.0   # HTTPS for phones on LAN

API:  GET /api/price/<code>  ->  200 {"name", "price", "currency"}  |  404 {"error"}
Prices come from mock_catalog.json (re-read on every request, so you can edit it live).
"""
import argparse
import http.server
import json
import os
import ssl
import time
from datetime import datetime
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(ROOT, 'mock_catalog.json')


class Handler(http.server.SimpleHTTPRequestHandler):
    delay = 0.3

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        pass  # only API requests are logged, see do_GET

    def do_GET(self):
        if not self.path.startswith('/api/price/'):
            return super().do_GET()
        t0 = time.perf_counter()
        code = unquote(self.path[len('/api/price/'):].split('?')[0])
        time.sleep(self.delay)
        with open(CATALOG, encoding='utf-8') as f:
            item = json.load(f).get(code)
        status, body = (200, item) if item else (404, {'error': 'not found'})
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        ms = (time.perf_counter() - t0) * 1000
        stamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f'{stamp}  {self.client_address[0]}  GET /api/price/{code}  {status}  {ms:.0f} ms  {json.dumps(body, ensure_ascii=False)}',
              flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--host', default='localhost')
    p.add_argument('--port', type=int, default=8000)
    p.add_argument('--delay', type=float, default=0.3, help='fake API latency in seconds')
    p.add_argument('--cert')
    p.add_argument('--key')
    args = p.parse_args()

    Handler.delay = args.delay
    server = http.server.ThreadingHTTPServer((args.host, args.port), Handler)
    scheme = 'http'
    if args.cert:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(args.cert, args.key)
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
        scheme = 'https'
    print(f'Serving {ROOT} on {scheme}://{args.host}:{args.port}  (API delay {args.delay}s)', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
