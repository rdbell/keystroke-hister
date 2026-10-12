import QtQuick
import QtTest
import "../core/Hister.js" as Hister

TestCase {
  name: "Hister"
  function context(query, scope, command, settings) {
    return { query: query, scope: scope || "", command: command || null, settings: settings || {} }
  }
  function test_commands_and_scope() {
    compare(Hister.request(context("hister linux"), Hister.KEY).query, "linux")
    compare(Hister.request(context("archive linux", "", { rest: "linux" }, { prefix: "archive" }), Hister.KEY).query, "linux")
    compare(Hister.request(context("linux", Hister.KEY), Hister.KEY).query, "linux")
    compare(Hister.request(context("linux"), Hister.KEY), null)
    compare(Hister.request(context("hister linux", "timer"), Hister.KEY), null)
    compare(Hister.request(context("hister"), Hister.KEY).query, "")
  }
  function test_cache_separates_servers_and_settings() {
    var a = Hister.request(context("hister linux"), Hister.KEY)
    var b = Hister.request(context("hister linux", "", null, { serverUrl: "http://localhost:1234" }), Hister.KEY)
    verify(Hister.cacheKey(a) !== Hister.cacheKey(b))
    b.serverUrl = a.serverUrl; b.tokenFile = "/private/token"
    verify(Hister.cacheKey(a) !== Hister.cacheKey(b))
  }
  function test_result_actions_and_ranking() {
    var rows = Hister.rows({ results: [
      { title: "First", url: "https://example.com/" },
      { title: "Second", url: "https://example.org/" }] })
    compare(rows.length, 2)
    compare(rows[0].action.type, "url")
    compare(rows[0].altAction.type, "copy")
    compare(rows[0].altAction.text, "https://example.com/")
    verify(rows[0].score > rows[1].score)
    compare(rows[0].remember, false)
  }
  function test_unavailable_empty_and_malformed() {
    compare(Hister.rows({ results: [] })[0].title, "No matching pages")
    compare(Hister.rows({ results: [], error: "Offline" })[0].title, "Offline")
    verify(Hister.rows(Hister.parse("oops"))[0].disabled)
    compare(Hister.rows({ results: [{ url: "file:///private" }] })[0].title, "No matching pages")
  }
}
