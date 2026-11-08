/*
 * The contents of this file are subject to the Common Public Attribution License Version 1.0.
 * See https://github.com/Slion/Fulguris/blob/main/LICENSE.CPAL-1.0.
 */
package fulguris.network

import android.webkit.CookieManager
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import okhttp3.OkHttpClient
import okhttp3.Request
import timber.log.Timber
import java.io.ByteArrayInputStream
import java.net.Authenticator
import java.net.InetSocketAddress
import java.net.PasswordAuthentication
import java.net.Proxy
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit

/** Handles WebView-intercepted requests through SOCKS5. Request bodies are unavailable
 * in shouldInterceptRequest, so body-bearing methods fail closed instead of bypassing proxy. */
object Socks5ProxyClient {
    private data class ClientKey(val host: String, val port: Int, val username: String, val password: String)
    private val clients = ConcurrentHashMap<ClientKey, OkHttpClient>()

    private object ProxyCredentials {
        private val current = ThreadLocal<PasswordAuthentication?>()
        @Volatile private var installed = false
        @Synchronized private fun install() {
            if (installed) return
            Authenticator.setDefault(object : Authenticator() {
                override fun getPasswordAuthentication(): PasswordAuthentication? =
                    if (requestorType == RequestorType.PROXY) current.get() else null
            })
            installed = true
        }
        fun <T> withCredentials(username: String, password: String, action: () -> T): T {
            if (username.isEmpty() && password.isEmpty()) return action()
            install()
            current.set(PasswordAuthentication(username, password.toCharArray()))
            return try { action() } finally { current.remove() }
        }
    }

    private fun client(host: String, port: Int, username: String, password: String): OkHttpClient {
        val key = ClientKey(host, port, username, password)
        return clients.getOrPut(key) {
            OkHttpClient.Builder()
                .proxy(Proxy(Proxy.Type.SOCKS, InetSocketAddress.createUnresolved(host, port)))
                .connectTimeout(15, TimeUnit.SECONDS)
                .readTimeout(45, TimeUnit.SECONDS)
                .writeTimeout(30, TimeUnit.SECONDS)
                .followRedirects(true)
                .followSslRedirects(true)
                .retryOnConnectionFailure(false)
                .build()
        }
    }

    fun intercept(request: WebResourceRequest, host: String, portValue: String, username: String, password: String): WebResourceResponse {
        val port = portValue.toIntOrNull()
        if (host.isBlank() || port == null || port !in 1..65535) return errorResponse(502, "Invalid SOCKS5 proxy address or port")
        val method = request.method.uppercase()
        if (method !in setOf("GET", "HEAD", "DELETE", "OPTIONS")) {
            Timber.w("SOCKS5 cannot forward request body for $method ${request.url}")
            return errorResponse(501, "SOCKS5 proxy cannot forward this request method")
        }
        return try {
            val builder = Request.Builder().url(request.url.toString())
            request.requestHeaders.forEach { (name, value) ->
                if (!name.equals("host", true) && !name.equals("content-length", true) && !name.equals("connection", true)) builder.header(name, value)
            }
            val outgoing = builder.method(method, null).build()
            val response = ProxyCredentials.withCredentials(username, password) {
                client(host, port, username, password).newCall(outgoing).execute()
            }
            val contentType = response.header("Content-Type")
            val mime = contentType?.substringBefore(';')?.trim()?.takeIf { it.isNotEmpty() } ?: "text/plain"
            val charset = contentType?.split(';')?.map { it.trim() }?.firstOrNull { it.startsWith("charset=", true) }?.substringAfter('=')?.trim() ?: "UTF-8"
            val headers = linkedMapOf<String, String>()
            response.headers.forEach { (name, value) -> headers[name] = value }
            response.headers("Set-Cookie").forEach { CookieManager.getInstance().setCookie(request.url.toString(), it) }
            WebResourceResponse(mime, charset, response.code, response.message.ifBlank { reasonPhrase(response.code) }, headers,
                response.body?.byteStream() ?: ByteArrayInputStream(ByteArray(0)))
        } catch (error: Exception) {
            Timber.e(error, "SOCKS5 request failed for ${request.url}")
            errorResponse(502, "SOCKS5 proxy connection failed")
        }
    }

    private fun errorResponse(code: Int, message: String) = WebResourceResponse(
        "text/plain", "UTF-8", code, reasonPhrase(code), mapOf("Cache-Control" to "no-store"),
        ByteArrayInputStream(message.toByteArray(Charsets.UTF_8))
    )
    private fun reasonPhrase(code: Int) = when (code) {
        501 -> "Not Implemented"
        502 -> "Bad Gateway"
        else -> "Proxy Error"
    }
}
