# Configuration and maintenance

In Keystroke, open **Extensions → Hister → Settings**. You can rename the command prefix, change the server URL (default `http://127.0.0.1:4433`), choose a result limit (default 12, up to 50), or provide an access token file.

The extension uses Hister's full-text relevance ordering, with semantic search disabled. Hister's query syntax and filters are passed through unchanged. Searches return HTTP(S) pages; other document types, including file snapshots, are omitted. Opening a result opens its original URL rather than an archived preview.

Compatibility: Keystroke extension API 1 (tested with 1.5.1), Python 3.10+, and Hister's search API (tested with 0.20.0).

## Authentication

For a protected server, create a private file containing the access token, set its permissions to `0600`, and enter its path in **Access token file**. Keep this file outside the checkout. The extension does not read Hister's configuration; an empty token-file setting sends no token. Never commit a real token or a private configuration.

## Updates and removal

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

