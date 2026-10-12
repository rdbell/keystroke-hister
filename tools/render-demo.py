#!/usr/bin/env python3
"""Render the real Keystroke UI offscreen with a dummy Hister HTTP server."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "linux": [
        ("Linux laptop setup notes", "https://example.com/linux/laptop"),
        ("Understanding Thunderbolt docks", "https://example.com/linux/thunderbolt"),
        ("A practical guide to systemd services", "https://example.com/linux/systemd"),
    ],
    "keyboard": [
        ("Building a comfortable keyboard layout", "https://example.com/keyboard/layout"),
        ("Vim navigation beyond the editor", "https://example.com/keyboard/vim"),
        ("Shortcuts worth remembering", "https://example.com/keyboard/shortcuts"),
    ],
    "sourdough": [
        ("A beginner's guide to sourdough", "https://example.com/baking/sourdough"),
        ("Keeping a starter happy", "https://example.com/baking/starter"),
        ("The weekend bread recipe", "https://example.com/baking/weekend"),
    ],
}


class DummyHister(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        query = json.loads(parse_qs(urlsplit(self.path).query)["query"][0])["text"]
        pages = PAGES.get(query, [])
        body = json.dumps({"total": len(pages), "documents": [
            {"title": title, "url": url} for title, url in pages]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keystroke", type=Path,
                        default=Path.home() / ".config/omarchy/plugins/evindor.keystroke")
    parser.add_argument("--output", type=Path, default=ROOT / "assets/demo.gif")
    args = parser.parse_args()
    if not (args.keystroke / "Keystroke.qml").is_file():
        raise SystemExit("Pass --keystroke with a Keystroke source directory")
    server = ThreadingHTTPServer(("127.0.0.1", 0), DummyHister)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="hister-readme-demo-") as temp:
            work = Path(temp)
            project = work / "project"
            shutil.copytree(args.keystroke, project, ignore=shutil.ignore_patterns(
                ".git", ".claude", ".agents", ".codex", "tests", "__pycache__", "experiments"))
            (work / "qs").symlink_to("/usr/share/omarchy/shell")
            source = project / "Keystroke.qml"
            qml = source.read_text().replace("  PanelWindow {", "  Window {\n    transientParent: null\n    width: 1000; height: 800")
            qml = qml.replace("    anchors { top: true; bottom: true; left: true; right: true }\n", "")
            qml = qml.replace("  function inspect() {", "  readonly property var showcaseCard: card\n  function inspect() {", 1)
            source.write_text("\n".join(line for line in qml.splitlines()
                                        if "exclusionMode:" not in line and "WlrLayershell." not in line))
            local = work / ".local/share/keystroke/extensions/keystroke-hister"
            local.parent.mkdir(parents=True)
            local.symlink_to(ROOT)
            frames = work / "frames"
            frames.mkdir()
            scenes = []
            for query in PAGES:
                full = "hister " + query
                for count in range(len("hister "), len(full) + 1):
                    scenes.append({"query": full[:count], "wait": 100, "copies": 1})
                scenes.append({"query": full, "wait": 600, "copies": 18})
                scenes.append({"select": 1, "wait": 150, "copies": 8})
                scenes.append({"ctrl": True, "wait": 150, "copies": 10})
                scenes.append({"ctrl": False, "wait": 100, "copies": 4})
            config = {"version": 1, "palette": {"accent": "sky", "density": "compact", "animations": "off"},
                      "matching": {"mode": "off"}, "providers": {
                          "keystroke-hister": {"enabled": True,
                                              "serverUrl": f"http://127.0.0.1:{server.server_port}"}}}
            harness = r'''
import QtQuick
import Quickshell
import "project"
ShellRoot {
  id: test
  property int stage: 0
  property int index: 0
  property int frame: 0
  property bool busy: false
  property double deadline: 0
  property var scenes: SCENES
  Keystroke { id: palette; omarchyPath: "/usr/share/omarchy" }
  Timer { interval: 30; running: true; repeat: true; onTriggered: {
    if (test.busy || Date.now() < test.deadline) return
    if (test.stage === 0) {
      if (!palette.registry.manifests["keystroke-hister"]) return
      palette.applyConfigText(JSON.stringify(CONFIG)); test.stage = 1; return
    }
    if (test.stage === 1) {
      var entry = palette.registry.entries.filter(function(e) { return e.key === "keystroke-hister" })[0]
      if (!entry || !entry.loaded) return
      palette.open(JSON.stringify({query: "hister "})); test.stage = 2; test.deadline = Date.now() + 300; return
    }
    var scene = test.scenes[test.index]
    if (!scene) { console.log("PASS demo"); Qt.quit(); return }
    if (test.stage === 2) {
      if (scene.query !== undefined) { palette.ctrlHeld = false; palette.setQuery(scene.query) }
      if (scene.select !== undefined) palette.selected = scene.select
      if (scene.ctrl !== undefined) palette.ctrlHeld = scene.ctrl
      test.deadline = Date.now() + scene.wait; test.stage = 3; return
    }
    test.busy = true
    palette.showcaseCard.grabToImage(function(result) {
      for (var i = 0; i < scene.copies; i++) {
        var name = String(test.frame++).padStart(4, "0")
        result.saveToFile(FRAMES + "/" + name + ".png")
      }
      test.busy = false; test.index++; test.stage = 2
    })
  } }
  Timer { interval: 30000; running: true; onTriggered: {console.log("FAIL demo timeout"); Qt.quit()} }
}
'''
            harness = harness.replace("SCENES", json.dumps(scenes)).replace("CONFIG", json.dumps(config))
            harness = harness.replace("FRAMES", json.dumps(str(frames)))
            (work / "shell.qml").write_text(harness)
            env = dict(os.environ, HOME=str(work), XDG_CONFIG_HOME=str(work / ".config"),
                       XDG_DATA_HOME=str(work / ".local/share"), XDG_STATE_HOME=str(work / ".local/state"),
                       XDG_RUNTIME_DIR=str(work), QT_QPA_PLATFORM="offscreen", QT_QPA_PLATFORMTHEME="generic",
                       QT_QUICK_BACKEND="software", QML_IMPORT_PATH=str(work))
            env.pop("DISPLAY", None)
            env.pop("WAYLAND_DISPLAY", None)
            result = subprocess.run(["quickshell", "-p", str(work / "shell.qml")], env=env,
                                    capture_output=True, text=True, timeout=40)
            output = result.stdout + result.stderr
            if "PASS demo" not in output or "FAIL" in output:
                raise SystemExit(output)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "10",
                            "-i", str(frames / "%04d.png"), "-filter_complex",
                            "pad=720:620:(ow-iw)/2:(oh-ih)/2:color=0x101217,split[a][b];"
                            "[a]palettegen=max_colors=128:reserve_transparent=0[p];"
                            "[b][p]paletteuse=dither=bayer:bayer_scale=3",
                            "-loop", "0", str(args.output)], check=True)
            # One representative still for the author's visual review, outside the repo.
            shutil.copy2(frames / "0020.png", "/tmp/keystroke-hister-demo-review.png")
            print(f"Rendered {len(list(frames.glob('*.png')))} frames to {args.output}")
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
