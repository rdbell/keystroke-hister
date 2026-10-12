# Maintaining Keystroke Hister

This is a public, standalone Keystroke API 1 extension. Keep the extension self-contained, with no imports from a particular user's Keystroke checkout or Omarchy settings.

Private or sensitive information must never be committed. Exclude real browsing histories, search queries/results, Hister databases/indexes/rules/keys/configuration, credentials, tokens, private paths, personal screenshots, and machine/user settings. Use synthetic example.com fixtures and temporary directories in tests. Do not query a developer's actual Hister archive to test changes. Ignore rules are not a substitute for reviewing the diff.

Run the Python tests and Qt tests in docs/DEVELOPMENT.md. When Quickshell and Hister are available, run the isolated integration test; it must use a temporary Hister instance, never the personal service. Use the installed Keystroke extension checker when available.

Search runs asynchronously; avoid blocking the QML UI thread. Keep request cancellation and stale-response rejection correct. Never interpolate a query into shell code. Do not log queries, result bodies, or tokens. Use plain text titles and allow only HTTP(S) result actions.

Before changing a loaded extension on this Omarchy system, stop Quickshell and restart it afterwards; live QML changes have caused shell crashes. Prefer testing offscreen first. Keep unrelated desktop preferences unchanged.
