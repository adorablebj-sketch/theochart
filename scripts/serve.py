#!/usr/bin/env python3
"""개발용 정적 서버: 브라우저 캐시를 끄고 site/를 서빙한다.

사용법: python3 scripts/serve.py [포트]   (기본 8765)
"""
import functools
import http.server
import pathlib
import sys

SITE = pathlib.Path(__file__).resolve().parent.parent / "site"


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, *args):
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    handler = functools.partial(NoCacheHandler, directory=str(SITE))
    print(f"http://localhost:{port}  (캐시 끔, Ctrl+C로 종료)")
    http.server.ThreadingHTTPServer(("", port), handler).serve_forever()


if __name__ == "__main__":
    main()
