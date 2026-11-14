"""Tiny test-only service modelling a process-local wedged runtime."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
WEDGED = False


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global WEDGED
        if self.path == "/__test__/wedge":
            # The harness reaches this only through kubectl exec to localhost.
            WEDGED = True
            logging.error("process-local worker state wedged; requests are failing")
            self._reply(202, {"injected": True})
        elif self.path == "/health":
            self._reply(503 if WEDGED else 200, {"healthy": not WEDGED, "state": "wedged" if WEDGED else "ready"})
        elif self.path == "/api/data":
            self._reply(500 if WEDGED else 200, {"error": "worker unavailable"} if WEDGED else {"value": "ok"})
        else:
            self._reply(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        logging.info("%s - %s", self.address_string(), fmt % args)

    def _reply(self, code, body):
        payload = json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)


HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
