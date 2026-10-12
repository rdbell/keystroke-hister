.pragma library

var KEY = "keystroke-hister"
var ICON = "󰋚"
var SETTINGS = [
  { key: "serverUrl", type: "string", label: "Server URL", default: "http://127.0.0.1:4433",
    description: "The Hister server to search. Queries are sent only to this server." },
  { key: "limit", type: "number", label: "Maximum results", default: 12, min: 1, max: 50, integer: true },
  { key: "tokenFile", type: "string", label: "Access token file", default: "",
    description: "Optional path to a private file containing your Hister access token. Leave empty for an unauthenticated local server." }
]

function request(ctx, key) {
  var scoped = ctx.scope === key
  if (ctx.scope && !scoped) return null
  var text = String(ctx.query || "").trim()
  if (ctx.command) text = String(ctx.command.rest || "").trim()
  else if (!scoped) {
    var prefix = String(ctx.settings.prefix || "hister")
    if (text.toLowerCase() === prefix.toLowerCase()) text = ""
    else if (text.toLowerCase().indexOf(prefix.toLowerCase() + " ") === 0) text = text.slice(prefix.length).trim()
    else return null
  }
  return { query: text, serverUrl: String(ctx.settings.serverUrl || "http://127.0.0.1:4433").trim(),
           limit: Math.max(1, Math.min(50, Math.round(Number(ctx.settings.limit) || 12))),
           tokenFile: String(ctx.settings.tokenFile || "").trim() }
}

function cacheKey(req) { return JSON.stringify([req.query, req.serverUrl, req.limit, req.tokenFile]) }
function argv(helper, req) {
  return ["python3", helper, "--server-url", req.serverUrl, "--limit", String(req.limit),
          "--token-file", req.tokenFile, "--query", req.query]
}
function status(title, subtitle) {
  return { id: "hister-status", title: title, subtitle: subtitle || "", icon: ICON,
           section: "Hister", score: 100, disabled: true, remember: false }
}
function parse(text) {
  try {
    var value = JSON.parse(text)
    if (value && Array.isArray(value.results)) return value
  } catch (_) {}
  return { results: [], error: "Hister returned an unreadable response" }
}
function safeUrl(url) { return /^https?:\/\/[^\s\/]+(?:[\/?#]|$)/i.test(String(url || "")) }
function rows(result) {
  if (result.error) return [status(result.error, "Check Hister and this extension's settings")]
  var items = result.results.filter(function(item) { return item && safeUrl(item.url) })
  if (!items.length) return [status("No matching pages", "Try another query, or archive more pages with Hister")]
  return items.map(function(item, i) {
    return { id: "hister:" + item.url, title: item.title || item.url, subtitle: item.url,
             icon: ICON, section: "Hister", score: 1000 - i, order: i, remember: false,
             verb: "Open", action: { type: "url", url: item.url },
             altVerb: "Copy URL", altAction: { type: "copy", text: item.url } }
  })
}
