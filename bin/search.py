#!/usr/bin/env python3
"""Read Hister's search API. No browser profiles, databases or config are opened."""
import argparse
import json
from pathlib import Path
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

MAX_RESPONSE = 2 * 1024 * 1024


class SearchError(Exception):
    pass


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward a query or access token to a redirected endpoint.
        return None


def validate_server(value):
    try:
        parts = urlsplit(value)
        _ = parts.port
    except ValueError:
        raise SearchError("Invalid Hister server URL") from None
    if (parts.scheme not in ("http", "https") or not parts.hostname
            or parts.username is not None or parts.password is not None
            or parts.query or parts.fragment or any(c.isspace() for c in value)):
        raise SearchError("Use an HTTP(S) server URL without credentials, query, or fragment")
    return value.rstrip("/")


def web_url(value):
    if not isinstance(value, str) or any(ord(c) < 33 for c in value):
        return False
    try:
        parts = urlsplit(value)
        return (parts.scheme in ("http", "https") and bool(parts.hostname)
                and parts.username is None and parts.password is None)
    except ValueError:
        return False


def normalize(payload, limit):
    if not isinstance(payload, dict):
        raise SearchError("Hister returned an unreadable response")
    docs = payload.get("documents")
    if docs is None and payload.get("total") == 0:
        docs = []
    if not isinstance(docs, list):
        raise SearchError("Hister returned an unreadable response")
    results, seen = [], set()
    for doc in docs:
        if not isinstance(doc, dict) or not web_url(doc.get("url")):
            continue
        url = doc["url"]
        if url in seen:
            continue
        seen.add(url)
        title = doc.get("title")
        title = " ".join(title.split())[:1000] if isinstance(title, str) else url
        results.append({"url": url, "title": title or url})
        if len(results) >= limit:
            break
    return {"results": results}


def search(server_url, query, limit=12, token_file="", timeout=4):
    server = validate_server(server_url)
    query = query.strip()
    if not query:
        return {"results": []}
    if len(query) > 4096:
        raise SearchError("Search query is too long")
    limit = max(1, min(50, limit))
    headers = {"Accept": "application/json", "Origin": "hister://",
               "User-Agent": "keystroke-hister/0.1.0"}
    if token_file:
        try:
            with Path(token_file).expanduser().open("r", encoding="utf-8") as token_stream:
                token = token_stream.read(8193).strip()
        except (OSError, UnicodeError):
            raise SearchError("Cannot read the access token file") from None
        if not token or len(token) > 8192 or "\n" in token or "\r" in token:
            raise SearchError("The access token file must contain one token")
        headers["X-Access-Token"] = token
    request_query = {"text": query, "limit": limit, "highlight": "", "sort": "score",
                     "include_html": False, "include_text": False, "semantic_enabled": False}
    url = server + "/search?" + urlencode({"query": json.dumps(request_query)})
    # Ignore ambient proxies, including for localhost. Use exactly the configured server.
    opener = build_opener(ProxyHandler({}), NoRedirects())
    try:
        with opener.open(Request(url, headers=headers), timeout=timeout) as response:
            data = response.read(MAX_RESPONSE + 1)
        if len(data) > MAX_RESPONSE:
            raise SearchError("Hister's response is too large")
        return normalize(json.loads(data), limit)
    except HTTPError as exc:
        exc.close()
        if exc.code in (401, 403):
            raise SearchError("Hister requires authentication; configure an access token file") from None
        if exc.code == 400:
            raise SearchError("Hister could not parse this query") from None
        raise SearchError("Hister returned HTTP " + str(exc.code)) from None
    except (TimeoutError, socket.timeout):
        raise SearchError("Hister search timed out") from None
    except URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise SearchError("Hister search timed out") from None
        raise SearchError("Cannot connect to Hister; check that the server is running") from None
    except OSError:
        raise SearchError("Connection to Hister was interrupted") from None
    except (ValueError, UnicodeError):
        raise SearchError("Hister returned an unreadable response") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-url", default="http://127.0.0.1:4433")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--token-file", default="")
    parser.add_argument("--query", required=True)
    args = parser.parse_args()
    try:
        result = search(args.server_url, args.query, args.limit, args.token_file)
    except SearchError as exc:
        result = {"results": [], "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
