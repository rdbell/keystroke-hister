# Hister for Keystroke

Search the full text of your [Hister](https://hister.org/) browsing archive from [Keystroke](https://github.com/evindor/keystroke), the Omarchy command launcher.

```text
hister linux thunderbolt
```

Results show page titles and URLs, in Hister's relevance order. **Enter** opens the selected page in your default browser. **Ctrl+Enter** copies its URL. You can also choose **Search Hister** to search within its own scope. The command prefix is configurable in Keystroke.

## Install

Requires Keystroke with extension API 1 (tested with 1.5.1), Python 3.10+, and a running Hister server (tested with 0.20.0). No pip packages, Node runtime, or extra compiled binaries are needed.

```bash
git clone https://github.com/rdbell/keystroke-hister.git
cd keystroke-hister
./bin/install
```

The installer links this checkout to `~/.local/share/keystroke/extensions/keystroke-hister`, the local extension directory used by Keystroke API 1. It refuses to overwrite an existing installation. Keep the checkout in place.

Open Keystroke, type `ext`, choose **Hister**, and turn on **Enabled**. Then type `hister <query>`. The default server is `http://127.0.0.1:4433`. Extension settings let you change its URL, the maximum result count (default 12), and an optional access token file. Hister's query syntax and filters work as they do in Hister; searches use full-text relevance, with semantic search disabled.

### Authentication

For a protected server, create a private file containing the access token, set its permissions to `0600`, and enter its path in **Access token file**. Keep this file outside the checkout. The extension does not read Hister's configuration; an empty token-file setting sends no token. Never commit a real token or a private configuration.

### Updates and removal

Run `git pull --ff-only` in the checkout, then restart the shell to clear QML's component cache. On Omarchy, stop the shell before pulling changes to a loaded extension, then restart afterwards:

```bash
quickshell kill -p /usr/share/omarchy/shell --any-display
git pull --ff-only
omarchy restart shell
```

To uninstall, disable Hister in Keystroke, then remove **only the installation symlink**. Neither the checkout nor Hister's archive is removed:

```bash
unlink "$HOME/.local/share/keystroke/extensions/keystroke-hister"
```

## Behavior and privacy

- Searches start after a 250 ms typing pause. Superseded requests are cancelled and stale results ignored.
- The helper calls Hister's `/search` API directly. It never opens browser profiles, Hister databases, or Hister configuration. An explicitly configured token file is the only private file it reads.
- Queries are sent to the configured server. Localhost is the default; choosing a remote server sends queries there. Ambient HTTP proxies are ignored, and redirects are refused.
- Hister may record search history on its server. This extension keeps a bounded cache in memory and clears it when the launcher next opens. It does not write searches or results to disk, log them, or contribute them to Keystroke's optional Smart Match catalog. Result rows opt out of frecency remembering.
- Only page titles and URLs are used; stored HTML and text are not requested. Icons are a shared glyph, so showing results does not fetch favicons from visited sites.
- Only HTTP(S) pages can be opened. File snapshots and other non-web documents are omitted. Enter opens the original page, rather than Hister's saved preview.
- Connection, authentication, invalid-query, and timeout errors appear in the result list. Reopen the launcher to retry after an error.

## Development

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

Tests use synthetic public example.com data. Do not use a personal archive, credentials, screenshots, or results as fixtures. See [AGENTS.md](AGENTS.md) for maintenance rules.

## License

MIT. This project integrates with Hister and Keystroke but is not affiliated with either project.
