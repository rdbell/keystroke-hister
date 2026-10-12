# Development

Run commands from the repository root.

```bash
python3 -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  /usr/lib/qt6/bin/qmltestrunner -silent -input tests
```

With Hister and Quickshell installed, test the real API and asynchronous QML service against an isolated temporary archive:

```bash
python3 tests/integration.py
```

Keystroke's own extension checker can also validate this checkout:

```bash
~/.config/omarchy/plugins/evindor.keystroke/bin/keystroke check-extensions "$PWD"
```

An optional GitHub Actions workflow is provided at `ci/github-actions.yml`. Copy it to `.github/workflows/tests.yml` to enable CI; publishing an active workflow through an OAuth login requires the GitHub `workflow` permission.

Tests use synthetic public example.com data. Do not use a personal archive, credentials, screenshots, or results as fixtures. See [AGENTS.md](../AGENTS.md) for maintenance rules.

### Regenerate the demo

The README GIF renders the real palette offscreen against a dummy HTTP server. It does not record the desktop or connect to a personal Hister instance. Requires Quickshell, Omarchy, a Keystroke checkout, FFmpeg, and `rsvg-convert` (librsvg):

```bash
python3 tools/render-demo.py
# Or point it at another Keystroke checkout:
python3 tools/render-demo.py --keystroke /path/to/keystroke
```

