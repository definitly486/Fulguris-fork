/*
 * The contents of this file are subject to the Common Public Attribution License Version 1.0.
 * See https://github.com/Slion/Fulguris/blob/main/LICENSE.CPAL-1.0.
 */
package fulguris.network

import android.util.Log
import android.webkit.CookieManager
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import okhttp3.OkHttpClient
import okhttp3.Request
import timber.log.Timber
import java.io.ByteArrayInputStream
import java.net.Authenticator
import java.net.ConnectException
import java.net.InetSocketAddress
import java.net.PasswordAuthentication
import java.net.Proxy
import java.net.SocketException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit

/** Handles WebView-intercepted requests through SOCKS5. Request bodies are unavailable
 * in shouldInterceptRequest, so body-bearing methods fail closed instead of bypassing proxy. */
object Socks5ProxyClient {
    private const val TAG = "Socks5ProxyClient"

    data class TestResult(val success: Boolean, val httpCode: Int? = null, val error: String? = null)

    private data class ClientKey(val host: String, val port: Int, val username: String, val password: String)
    private val clients = ConcurrentHashMap<ClientKey, OkHttpClient>()

    private object ProxyCredentials {
        private data class Endpoint(val host: String, val port: Int)

        // Android's SOCKS implementation may request credentials from a different
        // thread than the one executing OkHttp Call.execute(). ThreadLocal therefore
        // loses the credentials intermittently. Keep the active credentials keyed by
        // the configured proxy endpoint instead.
        private val credentials = ConcurrentHashMap<Endpoint, PasswordAuthentication>()
        @Volatile private var installed = false

        @Synchronized
        private fun install() {
            if (installed) return
            Authenticator.setDefault(object : Authenticator() {
                override fun getPasswordAuthentication(): PasswordAuthentication? {
                    val isSocks5Authentication = requestorType == RequestorType.SERVER &&
                        requestingProtocol.equals("SOCKS5", ignoreCase = true)
                    val isProxyAuthentication = requestorType == RequestorType.PROXY
                    if (!isSocks5Authentication && !isProxyAuthentication) return null

                    val host = requestingHost
                    return credentials.entries.firstOrNull { (endpoint, _) ->
                        endpoint.port == requestingPort &&
                            (host.isNullOrBlank() || endpoint.host.equals(host, ignoreCase = true))
                    }?.value
                }
            })
            installed = true
        }

        fun <T> withCredentials(
            host: String,
            port: Int,
            username: String,
            password: String,
            action: () -> T
        ): T {
            if (username.isEmpty() && password.isEmpty()) return action()
            install()
            credentials[Endpoint(host, port)] =
                PasswordAuthentication(username, password.toCharArray())
            return action()
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

    /**
     * Performs a real HTTPS request through the configured proxy.
     * Any HTTP response means the SOCKS tunnel and TLS connection were established.
     * Returns a user-readable result and never includes proxy credentials.
     */
    fun testConnection(host: String, portValue: String, username: String, password: String): TestResult {
        val port = portValue.toIntOrNull()
        if (host.isBlank()) return TestResult(false, error = "Proxy server address is empty")
        if (port == null || port !in 1..65535) return TestResult(false, error = "Invalid proxy port: $portValue")

        return try {
            val request = Request.Builder()
                .url("https://example.com/")
                .header("Cache-Control", "no-cache")
                .get()
                .build()
            val response = ProxyCredentials.withCredentials(host.trim(), port, username, password) {
                client(host.trim(), port, username, password).newCall(request).execute()
            }
            response.use {
                TestResult(true, httpCode = it.code)
            }
        } catch (error: Exception) {
            val detail = describeError(error)
            Log.e(TAG, "SOCKS5 connection test failed for ${host.trim()}:$port - $detail", error)
            TestResult(false, error = detail)
        }
    }

    private fun describeError(error: Throwable): String {
        val cause = generateSequence(error) { it.cause }.last()
        val type = cause.javaClass.simpleName.ifBlank { error.javaClass.simpleName }
        val rawMessage = cause.message?.trim()?.takeIf { it.isNotEmpty() }
            ?: error.message?.trim()?.takeIf { it.isNotEmpty() }
        val message = rawMessage
            ?.replace(Regex("(?i)(password|username)=([^\\s&]+)")) { match -> "${match.groupValues[1]}=[hidden]" }
            ?.take(180)
        return when (cause) {
            is SocketTimeoutException -> "Timeout while connecting to the proxy"
            is UnknownHostException -> "Cannot resolve proxy host: ${message ?: "unknown host"}"
            is ConnectException -> "Proxy refused the connection: ${message ?: type}"
            is SocketException -> message ?: "Socket error: $type"
            else -> if (message == null) type else "$type: $message"
        }
    }

    fun intercept(
        request: WebResourceRequest,
        host: String,
        portValue: String,
        username: String,
        password: String
    ): WebResourceResponse {
        val port = portValue.toIntOrNull()
        if (host.isBlank() || port == null || port !in 1..65535) {
            return errorResponse(502, "Invalid SOCKS5 proxy address or port")
        }

        val method = request.method.uppercase()
        if (method !in setOf("GET", "HEAD", "DELETE", "OPTIONS")) {
            val message = "SOCKS5 cannot forward request body for $method"
            Log.w(TAG, "$message ${request.url}")
            Timber.w("$message ${request.url}")
            return errorResponse(501, "$message. This WebView request method is not supported.")
        }

        return try {
            val builder = Request.Builder().url(request.url.toString())
            request.requestHeaders.forEach { (name, value) ->
                if (!name.equals("host", true) &&
                    !name.equals("content-length", true) &&
                    !name.equals("connection", true)
                ) {
                    builder.header(name, value)
                }
            }

            // WebView may send cache validators, but this interceptor does not share
            // WebView's HTTP cache. A 304 therefore has no cached body to reuse.
            builder.removeHeader("If-None-Match")
                .removeHeader("If-Modified-Since")

            val outgoing = builder.method(method, null).build()
            var response = ProxyCredentials.withCredentials(host, port, username, password) {
                client(host, port, username, password).newCall(outgoing).execute()
            }

            // Some servers/CDNs can still return 304. Retry once without validators
            // so WebView receives a complete response body rather than an unusable 304.
            if (response.code == 304) {
                response.close()
                val unconditional = outgoing.newBuilder()
                    .removeHeader("If-None-Match")
                    .removeHeader("If-Modified-Since")
                    .header("Cache-Control", "no-cache")
                    .header("Pragma", "no-cache")
                    .build()
                response = ProxyCredentials.withCredentials(host, port, username, password) {
                    client(host, port, username, password).newCall(unconditional).execute()
                }
            }

            Log.d(
                TAG,
                "SOCKS5 ${request.method} ${request.url} -> ${response.code}, " +
                    "range=${request.requestHeaders["Range"]}, " +
                    "contentRange=${response.header("Content-Range")}, " +
                    "contentType=${response.header("Content-Type")}"
            )

            // OkHttp follows normal redirects itself. Android WebResourceResponse
            // rejects every 3xx status, so never pass an unexpected one to its constructor.
            if (response.code in 300..399) {
                val location = response.header("Location")
                Log.w(TAG, "Unexpected HTTP ${response.code} for ${request.url}; location=$location")
                response.close()
                return errorResponse(502, "Unexpected HTTP ${response.code} from upstream server")
            }

            val contentType = response.header("Content-Type")
            val mime = contentType?.substringBefore(';')?.trim()?.takeIf { it.isNotEmpty() } ?: "text/plain"
            val charset = contentType?.split(';')
                ?.map { it.trim() }
                ?.firstOrNull { it.startsWith("charset=", true) }
                ?.substringAfter('=')
                ?.trim() ?: "UTF-8"
            val headers = linkedMapOf<String, String>()
            response.headers.forEach { (name, value) -> headers[name] = value }
            response.headers("Set-Cookie").forEach {
                CookieManager.getInstance().setCookie(request.url.toString(), it)
            }
            WebResourceResponse(
                mime,
                charset,
                response.code,
                response.message.ifBlank { reasonPhrase(response.code) },
                headers,
                response.body?.byteStream() ?: ByteArrayInputStream(ByteArray(0))
            )
        } catch (error: Exception) {
            val detail = describeError(error)
            Log.e(TAG, "SOCKS5 request failed for ${request.url}: $detail", error)
            Timber.e(error, "SOCKS5 request failed for ${request.url}: $detail")
            errorResponse(502, "SOCKS5 proxy connection failed: $detail")
        }
    }

    private fun errorResponse(code: Int, message: String) = WebResourceResponse(
        "text/plain",
        "UTF-8",
        code,
        reasonPhrase(code),
        mapOf("Cache-Control" to "no-store"),
        ByteArrayInputStream(message.toByteArray(Charsets.UTF_8))
    )

    private fun reasonPhrase(code: Int) = when (code) {
        501 -> "Not Implemented"
        502 -> "Bad Gateway"
        else -> "Proxy Error"
    }
}
