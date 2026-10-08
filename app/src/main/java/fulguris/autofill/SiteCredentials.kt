package fulguris.autofill

import android.content.Context
import android.webkit.WebView
import org.json.JSONArray
import org.json.JSONObject

/**
 * Fills login forms on a fixed list of sites from assets/site_credentials.json.
 *
 * File format: [{"host":"github.com","username":"...","password":"...","autoSubmit":false}]
 * "host" matches the page host or any of its subdomains.
 * Anything stored in an APK can be extracted, so never publish a build or a repo containing real passwords.
 */
object SiteCredentials {

    private class Entry(val host: String, val username: String, val password: String, val autoSubmit: Boolean)

    @Volatile private var entries: List<Entry>? = null

    private fun load(context: Context): List<Entry> {
        entries?.let { return it }
        val list = mutableListOf<Entry>()
        try {
            val text = context.assets.open("site_credentials.json").bufferedReader().use { it.readText() }
            val arr = JSONArray(text)
            for (i in 0 until arr.length()) {
                val o: JSONObject = arr.getJSONObject(i)
                val user = o.optString("username")
                val pass = o.optString("password")
                // Skip unfilled placeholders
                if (user.isBlank() || pass.isBlank() || user.startsWith("CHANGE_ME") || pass.startsWith("CHANGE_ME")) continue
                list.add(Entry(o.getString("host").lowercase(), user, pass, o.optBoolean("autoSubmit", false)))
            }
        } catch (e: Exception) {
        }
        entries = list
        return list
    }

    fun fill(view: WebView, url: String) {
        val host = try { android.net.Uri.parse(url).host?.lowercase() } catch (e: Exception) { null } ?: return
        val entry = load(view.context).firstOrNull { host == it.host || host.endsWith("." + it.host) }
        if (entry == null) return
        // Not a one shot: the password field often shows up after onPageFinished
        // (login popups, forms rendered by scripts, in-site navigation without a page load),
        // so we keep watching the page for a while and fill every new visible password field once.
        val js = """
            (function() {
                if (window.__siteCredWatch) return;
                window.__siteCredWatch = true;
                var USER = ${JSONObject.quote(entry.username)};
                var PASS = ${JSONObject.quote(entry.password)};
                var AUTO = ${entry.autoSubmit};
                function visible(el) {
                    return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                }
                function setVal(el, v) {
                    var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                    el.focus();
                    setter.call(el, v);
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                }
                function tryFill() {
                    var passes = document.querySelectorAll('input[type=password]');
                    for (var i = 0; i < passes.length; i++) {
                        var pass = passes[i];
                        if (pass.getAttribute('data-sitecred') || !visible(pass)) continue;
                        pass.setAttribute('data-sitecred', '1');
                        var scope = pass.form || document;
                        var cands = scope.querySelectorAll('input[type=email], input[type=text], input:not([type]), input[name*=login i], input[name*=user i], input[name*=nick i]');
                        var user = null;
                        for (var j = 0; j < cands.length; j++) {
                            if (visible(cands[j]) && !cands[j].value) { user = cands[j]; break; }
                        }
                        if (user) setVal(user, USER);
                        setVal(pass, PASS);
                        if (AUTO && pass.form) {
                            // Press the real submit button, never form.submit(): a native submit bypasses the
                            // site scripts (login becomes a plain GET without password and the page just reloads).
                            // Wait a bit so the site scripts are attached, and at most once per 30 s to avoid reload loops.
                            var last = 0;
                            try { last = parseInt(sessionStorage.getItem('__sitecred_sub') || '0'); } catch (e) {}
                            if (Date.now() - last > 30000) {
                                try { sessionStorage.setItem('__sitecred_sub', String(Date.now())); } catch (e) {}
                                (function(f) {
                                    setTimeout(function() {
                                        var btns = f.querySelectorAll('button[type=submit], input[type=submit], button:not([type])');
                                        for (var k = 0; k < btns.length; k++) {
                                            if (visible(btns[k]) && !btns[k].disabled) { btns[k].click(); return; }
                                        }
                                    }, 800);
                                })(pass.form);
                            }
                        }
                    }
                }
                tryFill();
                var obs = new MutationObserver(tryFill);
                obs.observe(document.documentElement, {childList: true, subtree: true, attributes: true, attributeFilter: ['style', 'class', 'hidden']});
                setTimeout(function() { obs.disconnect(); window.__siteCredWatch = false; }, 60000);
            })();
        """.trimIndent()
        view.evaluateJavascript(js, null)
    }
}
