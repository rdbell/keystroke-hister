#!/usr/bin/env python3
"""Exercise real Hister and Quickshell without opening a personal archive."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hister_search", ROOT / "bin/search.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class Mock(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        query = json.loads(parse_qs(urlsplit(self.path).query)["query"][0])["text"]
        if query == "slow":
            time.sleep(1)
        if query == "auth":
            self.send_response(401)
            self.end_headers()
            return
        body = json.dumps({"documents": [{"title": query, "url": "https://example.com/"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def run():
    if not shutil.which("hister") or not shutil.which("quickshell"):
        raise SystemExit("Install Hister and Quickshell to run the isolated integration test")
    with tempfile.TemporaryDirectory(prefix="keystroke-hister-test-") as temp:
        work = Path(temp)
        (work / "runtime").mkdir(mode=0o700)
        port = free_port()
        url = f"http://127.0.0.1:{port}"
        config = work / "config.yml"
        config.write_text('app:\n  directory: ' + json.dumps(str(work / "data"))
                          + '\nserver:\n  address: ' + json.dumps(f"127.0.0.1:{port}") + '\n')
        env = dict(os.environ, HOME=str(work), XDG_CONFIG_HOME=str(work / "config"),
                   XDG_DATA_HOME=str(work / "share"), XDG_STATE_HOME=str(work / "state"),
                   XDG_RUNTIME_DIR=str(work / "runtime"), HISTER_CONFIG=str(config),
                   HISTER_DATA_DIR=str(work / "data"))
        # Ignore all inherited Hister overrides, including credentials.
        for key in list(env):
            if key.startswith("HISTER__") or key == "HISTER_PORT":
                del env[key]
        log = (work / "server.log").open("w")
        server = subprocess.Popen(["hister", "--config", str(config), "listen"], cwd=work,
                                  env=env, stdout=log, stderr=log)
        mock = ThreadingHTTPServer(("127.0.0.1", 0), Mock)
        mock.daemon_threads = True
        thread = threading.Thread(target=mock.serve_forever, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 20
            while True:
                try:
                    with urlopen(url, timeout=0.3) as response:
                        assert response.status == 200
                    break
                except OSError:
                    if server.poll() is not None or time.monotonic() > deadline:
                        raise AssertionError("Temporary Hister did not start")
                    time.sleep(0.1)
            doc = {"url": "https://example.com/keystroke-hister-test", "title": "Public test page",
                   "text": "Synthetic archive content nebularabbits", "html": "<p>Synthetic archive content nebularabbits</p>"}
            request = Request(url + "/api/add", data=json.dumps(doc).encode(),
                              headers={"Content-Type": "application/json", "Origin": "hister://"})
            with urlopen(request, timeout=10) as response:
                assert response.status == 201, "Synthetic document was not indexed"
            results = helper.search(url, "nebularabbits")["results"]
            assert len(results) == 1 and results[0]["title"] == "Public test page", results

            qml = r'''
import QtQuick
import "EXTENSION" as Extension
QtObject {
  id: test
  property int stage: 0
  property string text: "nebularabbits"
  property string serverUrl: REAL_URL
  property var current: []
  readonly property QtObject service: Extension.Service { extension: ({ id: "keystroke-hister" }) }
  function refresh() {
    current = service.provider.query({ query: "hister " + text, command: { rest: text }, scope: "",
       settings: { serverUrl: serverUrl, limit: 12, tokenFile: "" }, host: test, pending: function() {} })
  }
  function requery(_) {
    refresh()
    if (stage === 0 && current.length && current[0].title === "Public test page") {
      if (current[0].action.type !== "url" || current[0].altAction.type !== "copy") fail("actions")
      service.provider.opened()
      stage = 1; serverUrl = MOCK_URL; text = "slow"; refresh(); replace.start()
    } else if (stage === 2 && current.length && current[0].title === "fast") {
      stage = 3; staleCheck.start()
    } else if (stage === 4 && current.length && current[0].title.indexOf("requires authentication") >= 0) {
      stage = 5; serverUrl = REAL_URL; text = "absentzyxwvutsrqponmlkjihgfedcba"; refresh()
    } else if (stage === 5 && current.length && current[0].title === "No matching pages") {
      service.provider.opened()
      if (Object.keys(service.cache).length || service.active) fail("resources were not cleared")
      console.log("PASS integration: real search, actions, debounce, cancellation, stale responses, authentication, empty results, reset")
      Qt.quit()
    }
  }
  function fail(message) { console.log("FAIL " + message); Qt.quit() }
  readonly property Timer replace: Timer { interval: 400; onTriggered: { test.stage = 2; test.text = "fast"; test.refresh() } }
  readonly property Timer staleCheck: Timer {
    interval: 700
    onTriggered: {
      if (test.current[0].title !== "fast") { test.fail("stale result replaced the latest query"); return }
      test.stage = 4; test.text = "auth"; test.refresh()
    }
  }
  readonly property Timer timeout: Timer { interval: 12000; running: true; onTriggered: test.fail("timeout at stage " + test.stage + ": " + JSON.stringify(test.current)) }
  Component.onCompleted: refresh()
}
'''
            qml = qml.replace("EXTENSION", ROOT.as_uri()).replace("REAL_URL", json.dumps(url))
            qml = qml.replace("MOCK_URL", json.dumps(f"http://127.0.0.1:{mock.server_port}"))
            harness = work / "shell.qml"
            harness.write_text(qml)
            env.update(QT_QPA_PLATFORM="offscreen", QT_QPA_PLATFORMTHEME="generic", QT_QUICK_BACKEND="software")
            env.pop("DISPLAY", None)
            env.pop("WAYLAND_DISPLAY", None)
            result = subprocess.run(["quickshell", "-p", str(harness)], env=env, cwd=work,
                                    capture_output=True, text=True, timeout=20)
            output = result.stdout + result.stderr
            assert result.returncode == 0 and "PASS integration:" in output and "FAIL" not in output, output
            assert "TypeError" not in output and "ReferenceError" not in output, output
            print("PASS isolated Hister + Quickshell integration")
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            log.close()
            mock.shutdown()
            mock.server_close()
            thread.join()


if __name__ == "__main__":
    run()
