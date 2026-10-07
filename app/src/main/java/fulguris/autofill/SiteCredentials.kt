package fulguris.autofill

import android.content.Context
import android.webkit.WebView
import org.json.JSONArray
import org.json.JSONObject
import timber.log.Timber

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
            Timber.d("No site credentials loaded: ${e.message}")
        }
        entries = list
        return list
    }

    fun fill(view: WebView, url: String) {
        val host = try { android.net.Uri.parse(url).host?.lowercase() } catch (e: Exception) { null } ?: return
        val entry = load(view.context).firstOrNull { host == it.host || host.endsWith("." + it.host) } ?: return
        val js = """
            (function() {
                function setVal(el, v) {
                    var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                    setter.call(el, v);
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                }
                var pass = document.querySelector('input[type=password]');
                if (!pass) return;
                var scope = pass.form || document;
                var user = scope.querySelector('input[type=email], input[type=text], input[name*=login i], input[name*=user i], input[name*=nick i]');
                if (user) setVal(user, ${JSONObject.quote(entry.username)});
                setVal(pass, ${JSONObject.quote(entry.password)});
                ${if (entry.autoSubmit) "if (pass.form) { if (pass.form.requestSubmit) pass.form.requestSubmit(); else pass.form.submit(); }" else ""}
            })();
        """.trimIndent()
        view.evaluateJavascript(js, null)
    }
}
