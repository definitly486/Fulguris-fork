package fulguris.network

import android.content.Context
import android.net.Uri
import androidx.preference.PreferenceManager
import fulguris.R

/**
 * SOCKS5 settings and domain-only FoxyProxy-style rules.
 *
 * One rule per line. Prefix with ! to bypass the proxy. A rule may be a plain
 * domain (example.com), wildcard domain (*.example.com), or an imported
 * FoxyProxy URL pattern with any path on the example.com domain. Scheme, port and path are
 * deliberately discarded: routing decisions are made only from the hostname.
 * Prefix with re: to match the hostname with a regular expression.
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

    fun read(context: Context): Config {
        val prefs = PreferenceManager.getDefaultSharedPreferences(context)
        return Config(
            enabled = prefs.getBoolean(context.getString(R.string.pref_key_socks5_proxy_enabled), false),
            host = prefs.getString(context.getString(R.string.pref_key_socks5_proxy_host), "") ?: "",
            port = prefs.getString(context.getString(R.string.pref_key_socks5_proxy_port), "1080") ?: "1080",
            username = prefs.getString(context.getString(R.string.pref_key_socks5_proxy_username), "") ?: "",
            password = prefs.getString(context.getString(R.string.pref_key_socks5_proxy_password), "") ?: "",
            patterns = prefs.getString(context.getString(R.string.pref_key_socks5_proxy_patterns), "") ?: ""
        )
    }

    fun shouldUseProxy(context: Context, url: String): Boolean {
        val scheme = Uri.parse(url).scheme?.lowercase()
        if (scheme != "http" && scheme != "https") return false
        val config = read(context)
        return config.enabled && config.host.isNotBlank() && shouldUseProxyHost(config, Uri.parse(url).host.orEmpty())
    }

    fun shouldUseProxyHost(config: Config, hostValue: String): Boolean {
        if (!config.enabled || config.host.isBlank()) return false
        val host = hostValue.trim().trimEnd('.').lowercase()
        if (host.isEmpty()) return false

        val rules = config.patterns.lineSequence()
            .map { it.trim() }
            .filter { it.isNotEmpty() && !it.startsWith("#") }
            .toList()
        if (rules.isEmpty()) return true

        val exclusions = rules.filter { it.startsWith("!") }.map { it.drop(1) }
        if (exclusions.any { matchesHost(host, it) }) return false

        val inclusions = rules.filterNot { it.startsWith("!") }
        return inclusions.isEmpty() || inclusions.any { matchesHost(host, it) }
    }

    private fun matchesHost(host: String, rawPattern: String): Boolean {
        val pattern = normalizeDomainPattern(rawPattern)
        if (pattern.isBlank()) return false
        return try {
            if (pattern.startsWith("re:", ignoreCase = true)) {
                Regex(pattern.substring(3), RegexOption.IGNORE_CASE).containsMatchIn(host)
            } else if (pattern.startsWith("*.")) {
                val suffix = pattern.substring(2).lowercase()
                host == suffix || host.endsWith(".$suffix")
            } else {
                val regex = buildString {
                    append('^')
                    pattern.forEach { ch ->
                        when (ch) {
                            '*' -> append(".*")
                            '?' -> append('.')
                            else -> append(Regex.escape(ch.toString()))
                        }
                    }
                    append('$')
                }
                Regex(regex, RegexOption.IGNORE_CASE).matches(host)
            }
        } catch (_: Exception) {
            false
        }
    }

    private fun normalizeDomainPattern(raw: String): String {
        var value = raw.trim()
        if (value.isEmpty()) return ""
        if (value.startsWith("re:", ignoreCase = true)) return value

        // Accept FoxyProxy-style URL patterns but intentionally retain only host.
        value = value.substringAfter("://", value)
        value = value.substringBefore('/')
        value = value.substringBefore('?')
        value = value.substringBefore('#')
        value = value.substringAfterLast('@')
        if (value.startsWith("*.")) value = "*." + value.removePrefix("*.")
        // A port is not part of a domain rule. IPv6 literals are not pattern-matched
        // with this wildcard syntax; ordinary domain names are the intended input.
        if (!value.startsWith("[") && value.count { it == ':' } == 1) {
            value = value.substringBefore(':')
        }
        if (value.startsWith("*.")) {
            val suffix = value.removePrefix("*.")
            // *.example.com includes the apex and all subdomains.
            return "*.$suffix"
        }
        return value.trimEnd('.').lowercase()
    }
}
