pragma ComponentBehavior: Bound
import QtQuick
import Quickshell.Io
import "core/Hister.js" as Hister

QtObject {
  id: root
  property var shell: null
  property var extension: null
  property string omarchyPath: ""
  property var host: null
  readonly property string key: extension && extension.id ? String(extension.id) : Hister.KEY
  readonly property string helper: decodeURIComponent(String(Qt.resolvedUrl("bin/search.py")).replace(/^file:\/\//, ""))
  property var subject: null
  property var active: null
  property var cache: ({})

  readonly property var provider: ({
    apiVersion: 1, name: "Hister", icon: Hister.ICON, color: "#61afef",
    description: "Search the full text of your archived pages",
    settings: Hister.SETTINGS,
    query: function(ctx) { return root.query(ctx) },
    opened: function() { root.reset() },
    dismiss: function() { root.reset() }
  })

  function cancel() {
    if (active) {
      active.cancelled = true
      if (active.running) active.signal(15)
      active = null
    }
  }
  function reset() { debounce.stop(); cancel(); subject = null; cache = ({}) }
  function query(ctx) {
    host = ctx.host || host
    var req = Hister.request(ctx, key)
    if (!req || !req.query) {
      debounce.stop(); cancel(); subject = null
      if (req) return [Hister.status("Search your Hister archive", "Type words from a page's title, URL, or content")]
      if (ctx.scope) return []
      return [{ id: "hister-open", title: "Search Hister", subtitle: "Search archived page content",
                icon: Hister.ICON, keywords: "archive history web pages", section: "Hister",
                action: { type: "navigate", scope: key, title: "Hister" }, verb: "Search" }]
    }
    var k = Hister.cacheKey(req)
    if (!subject || Hister.cacheKey(subject) !== k) {
      cancel(); subject = req; debounce.restart()
    }
    var hit = cache[k]
    if (hit !== undefined) return Hister.rows(hit)
    if (ctx.pending) ctx.pending()
    return [Hister.status("Searching Hister…", "")]
  }

  readonly property Timer debounce: Timer {
    interval: 250
    onTriggered: root.search()
  }
  function search() {
    if (!subject) return
    var k = Hister.cacheKey(subject)
    if (cache[k] !== undefined || (active && active.requestKey === k)) return
    var proc = fetcher.createObject(root, { requestKey: k })
    active = proc
    proc.command = Hister.argv(helper, subject)
    proc.running = true
  }
  readonly property Component fetcher: Component {
    Process {
      id: proc
      property string requestKey: ""
      property bool cancelled: false
      property bool outputDone: false
      property bool exitDone: false
      property int code: 0
      property string output: ""
      property bool timedOut: false
      readonly property Timer watchdog: Timer {
        interval: 6000
        onTriggered: { proc.timedOut = true; if (proc.running) proc.signal(9) }
      }
      onRunningChanged: { if (running) watchdog.start(); else watchdog.stop() }
      stdout: StdioCollector {
        onStreamFinished: { proc.output = text; proc.outputDone = true; root.finish(proc) }
      }
      onExited: function(exitCode) { proc.code = exitCode; proc.exitDone = true; root.finish(proc) }
    }
  }
  function finish(proc) {
    // Process exit and stdout completion may arrive in either order.
    if (!proc.outputDone || !proc.exitDone) return
    if (!proc.cancelled && active === proc && subject && Hister.cacheKey(subject) === proc.requestKey) {
      var value = proc.timedOut ? { results: [], error: "Hister search timed out" }
        : proc.code === 0 ? Hister.parse(proc.output)
        : { results: [], error: "Search helper failed; check that Python 3 is installed" }
      var next = ({})
      var keys = Object.keys(cache).slice(-15)
      for (var i = 0; i < keys.length; i++) next[keys[i]] = cache[keys[i]]
      next[proc.requestKey] = value
      cache = next
      active = null
      if (host) host.requery({ catalog: false, provider: key })
    }
    Qt.callLater(function() { proc.destroy() })
  }
  Component.onDestruction: root.cancel()
}
