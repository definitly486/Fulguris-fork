package fulguris.network

import android.content.Context
import androidx.preference.PreferenceManager

/**
 * Global SOCKS5 settings and FoxyProxy-style URL pattern matching.
 *
 * Pattern syntax: one wildcard pattern per line; prefix with ! to bypass the proxy.
 * Prefix with re: to use a regular expression. If there are positive patterns,
 * only matching URLs use the proxy. Exclusions always take precedence.
 */
object ProxySettings {
    data class Config(
        val enabled: Boolean,
        val host: String,
        val port: String,
        val username: String,
        val password: String,
        val patterns: String
    )

    private fun key(context: Context, name: String) = context.getString(
        context.resources.getIdentifier(name, "string", context.packageName)
    )

    fun read(context: Context): Config {
        val prefs = PreferenceManager.getDefaultSharedPreferences(context)
        return Config(
            enabled = prefs.getBoolean(key(context, "pref_key_socks5_proxy_enabled"), false),
            host = prefs.getString(key(context, "pref_key_socks5_proxy_host"), "") ?: "",
            port = prefs.getString(key(context, "pref_key_socks5_proxy_port"), "1080") ?: "1080",
            username = prefs.getString(key(context, "pref_key_socks5_proxy_username"), "") ?: "",
            password = prefs.getString(key(context, "pref_key_socks5_proxy_password"), "") ?: "",
            patterns = prefs.getString(key(context, "pref_key_socks5_proxy_patterns"), "") ?: ""
        )
    }

    fun shouldUseProxy(context: Context, url: String): Boolean {
        val config = read(context)
        if (!config.enabled || config.host.isBlank()) return false

        val rules = config.patterns.lineSequence()
            .map { it.trim() }
            .filter { it.isNotEmpty() && !it.startsWith("#") }
            .toList()
        if (rules.isEmpty()) return true

        val exclusions = rules.filter { it.startsWith("!") }.map { it.drop(1) }
        if (exclusions.any { matches(url, it) }) return false

        val inclusions = rules.filterNot { it.startsWith("!") }
        return inclusions.isEmpty() || inclusions.any { matches(url, it) }
    }

    private fun matches(url: String, rawPattern: String): Boolean {
        if (rawPattern.isBlank()) return false
        return try {
            if (rawPattern.startsWith("re:", ignoreCase = true)) {
                Regex(rawPattern.substring(3), RegexOption.IGNORE_CASE).containsMatchIn(url)
            } else {
                val regex = buildString {
                    append('^')
                    rawPattern.forEach { ch ->
                        when (ch) {
                            '*' -> append(".*")
                            '?' -> append('.')
                            else -> {
                                if (ch in ".\\+()^${}[]|") append('\\')
                                append(ch)
                            }
                        }
                    }
                    append('$')
                }
                Regex(regex, RegexOption.IGNORE_CASE).matches(url)
            }
        } catch (_: Exception) {
            false
        }
    }
}
