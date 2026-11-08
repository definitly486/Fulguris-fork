package fulguris.network

import android.net.Uri
import android.util.Log
import androidx.webkit.ProxyConfig
import androidx.webkit.ProxyController
import androidx.webkit.WebViewFeature
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.io.OutputStream
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Local HTTP proxy for WebView. It routes by hostname and creates authenticated
 * SOCKS5 connections (RFC 1928/1929), allowing WebView POST/media traffic to use
 * the proxy without exposing TLS contents or installing a MITM certificate.
 */
object LocalSocks5Proxy {
    private const val TAG = "LocalSocks5Proxy"
    private const val CONNECT_TIMEOUT = 15000
    private const val MAX_HEADER = 65536
    @Volatile private var config: ProxySettings.Config? = null
    @Volatile private var listener: ServerSocket? = null
    @Volatile private var localPort = -1
    private val active = AtomicBoolean(false)
    private val workers: ExecutorService = Executors.newCachedThreadPool()
    private val callbackExecutor: ExecutorService = Executors.newSingleThreadExecutor()

    @Synchronized
    fun refresh(context: android.content.Context) {
        val value = ProxySettings.read(context.applicationContext)
        config = value
        if (!value.enabled || value.host.isBlank() || value.port.toIntOrNull()?.let { it in 1..65535 } != true) {
            stop()
            clearOverride()
            return
        }
        try {
            if (listener == null || listener?.isClosed != false) start()
            applyOverride()
        } catch (e: Exception) {
            Log.e(TAG, "Cannot start local proxy", e)
            stop()
            clearOverride()
        }
    }

    @Synchronized private fun start() {
        stop()
        val socket = ServerSocket()
        socket.reuseAddress = true
        socket.bind(InetSocketAddress("127.0.0.1", 0))
        listener = socket
        localPort = socket.localPort
        active.set(true)
        workers.execute {
            while (active.get()) {
                try {
                    val client = socket.accept()
                    workers.execute { handle(client) }
                } catch (e: Exception) {
                    if (active.get()) Log.w(TAG, "Accept failed", e)
                }
            }
        }
        Log.i(TAG, "Listening on 127.0.0.1:$localPort")
    }

    @Synchronized private fun stop() {
        active.set(false)
        try { listener?.close() } catch (_: Exception) {}
        listener = null
        localPort = -1
    }

    private fun applyOverride() {
        if (!WebViewFeature.isFeatureSupported(WebViewFeature.PROXY_OVERRIDE)) {
            Log.e(TAG, "WebView provider does not support PROXY_OVERRIDE")
            return
        }
        val port = localPort
        if (port <= 0) return
        val value = ProxyConfig.Builder().addProxyRule("http://127.0.0.1:$port").build()
        ProxyController.getInstance().setProxyOverride(value, callbackExecutor) {
            Log.i(TAG, "WebView proxy override enabled on local port $port")
        }
    }

    private fun clearOverride() {
        try {
            if (WebViewFeature.isFeatureSupported(WebViewFeature.PROXY_OVERRIDE)) {
                ProxyController.getInstance().clearProxyOverride(callbackExecutor) {
                    Log.i(TAG, "WebView proxy override cleared")
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "Cannot clear WebView proxy override", e)
        }
    }

    private fun handle(client: Socket) {
        var upstream: Socket? = null
        try {
            val input = client.getInputStream()
            val output = client.getOutputStream()
            val line = readLine(input) ?: return
            val fields = line.split(' ')
            if (fields.size < 2) return
            val method = fields[0].uppercase()
            val target = fields[1]
            val headers = ArrayList<String>()
            var size = line.length
            while (true) {
                val header = readLine(input) ?: return
                size += header.length + 2
                if (size > MAX_HEADER) throw IllegalStateException("Request headers too large")
                if (header.isEmpty()) break
                headers.add(header)
            }

            val connect = method == "CONNECT"
            val uri = if (connect) null else Uri.parse(target)
            val hostHeader = headers.firstOrNull { it.startsWith("Host:", true) }
                ?.substringAfter(':')?.trim()
            val host = if (connect) target.substringBeforeLast(':').trim('[', ']')
                else uri?.host ?: hostHeader?.substringBefore(':')?.trim('[', ']')
            if (host.isNullOrBlank()) {
                sendError(output, 400, "Bad Request")
                return
            }
            val port = if (connect) target.substringAfterLast(':').toIntOrNull() ?: 443
                else uri?.port?.takeIf { it > 0 } ?: if (uri?.scheme.equals("https", true)) 443 else 80

            val cfg = config
            val viaSocks = cfg != null && ProxySettings.shouldUseProxyHost(cfg, host)
            val upstreamSocket = if (viaSocks) openSocks(host, port, cfg!!) else Socket().apply {
                connect(InetSocketAddress(host, port), CONNECT_TIMEOUT)
            }
            upstream = upstreamSocket

            if (connect) {
                output.write("HTTP/1.1 200 Connection Established\r\nProxy-Agent: Fulguris\r\n\r\n".toByteArray(Charsets.ISO_8859_1))
                output.flush()
            } else {
                val path = buildString {
                    append(uri?.encodedPath?.takeIf { it.isNotEmpty() } ?: "/")
                    uri?.encodedQuery?.let { append('?'); append(it) }
                }
                upstreamSocket.getOutputStream().write("$method $path HTTP/1.1\r\n".toByteArray(Charsets.ISO_8859_1))
                headers.forEach { header ->
                    if (!header.startsWith("Proxy-Connection:", true) &&
                        !header.startsWith("Proxy-Authorization:", true) &&
                        !header.startsWith("Connection:", true)
                    ) {
                        upstream.getOutputStream().write(header.toByteArray(Charsets.ISO_8859_1))
                        upstream.getOutputStream().write("\r\n".toByteArray(Charsets.ISO_8859_1))
                    }
                }
                upstream.getOutputStream().write("Connection: close\r\n\r\n".toByteArray(Charsets.ISO_8859_1))
                upstream.getOutputStream().flush()
            }
            bridge(client, upstreamSocket)
            upstream = null
        } catch (e: Exception) {
            Log.w(TAG, "Request failed: ${e.javaClass.simpleName}: ${e.message}")
            try { sendError(client.getOutputStream(), 502, "Bad Gateway") } catch (_: Exception) {}
        } finally {
            try { upstream?.close() } catch (_: Exception) {}
            try { client.close() } catch (_: Exception) {}
        }
    }

    private fun openSocks(host: String, port: Int, cfg: ProxySettings.Config): Socket {
        val socket = Socket()
        try {
            socket.connect(InetSocketAddress(cfg.host.trim(), cfg.port.toInt()), CONNECT_TIMEOUT)
            socket.soTimeout = CONNECT_TIMEOUT
            val input = socket.getInputStream()
            val output = socket.getOutputStream()
            val auth = cfg.username.isNotEmpty() || cfg.password.isNotEmpty()
            output.write(if (auth) byteArrayOf(5, 1, 2) else byteArrayOf(5, 1, 0))
            output.flush()
            val greeting = readExact(input, 2)
            if (greeting[0].toInt() != 5 || (greeting[1].toInt() and 255) == 255) error("SOCKS5 auth method rejected")
            if (greeting[1].toInt() == 2) {
                val user = cfg.username.toByteArray(Charsets.UTF_8)
                val pass = cfg.password.toByteArray(Charsets.UTF_8)
                require(user.size in 1..255 && pass.size <= 255) { "SOCKS5 credentials exceed RFC1929 limit" }
                output.write(byteArrayOf(1, user.size.toByte()))
                output.write(user)
                output.write(pass.size)
                output.write(pass)
                output.flush()
                if (readExact(input, 2)[1].toInt() != 0) error("SOCKS5 authentication failed")
            } else if (auth) error("SOCKS5 server does not support username/password")
            val domain = host.toByteArray(Charsets.UTF_8)
            require(domain.size in 1..255) { "Invalid destination hostname" }
            output.write(byteArrayOf(5, 1, 0, 3, domain.size.toByte()))
            output.write(domain)
            output.write(byteArrayOf((port shr 8).toByte(), port.toByte()))
            output.flush()
            val reply = readExact(input, 4)
            if (reply[0].toInt() != 5 || reply[1].toInt() != 0) {
                error("SOCKS5 CONNECT failed: ${reply[1].toInt() and 255}")
            }
            when (reply[3].toInt()) {
                1 -> readExact(input, 4)
                3 -> readExact(input, readExact(input, 1)[0].toInt() and 255)
                4 -> readExact(input, 16)
                else -> error("Invalid SOCKS5 address type")
            }
            readExact(input, 2)
            socket.soTimeout = 0
            return socket
        } catch (e: Exception) {
            try { socket.close() } catch (_: Exception) {}
            throw e
        }
    }

    private fun bridge(client: Socket, upstream: Socket) {
        // Preserve TCP half-close: after the browser finishes uploading a POST body,
        // the upstream server may still need to send its response.
        val upload = workers.submit { copy(client.getInputStream(), upstream.getOutputStream(), upstream) }
        val download = workers.submit { copy(upstream.getInputStream(), client.getOutputStream(), client) }
        try { upload.get() } catch (_: Exception) {}
        try { download.get() } catch (_: Exception) {}
    }

    private fun copy(input: InputStream, output: OutputStream, peer: Socket) {
        try {
            val buffer = ByteArray(32768)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                output.write(buffer, 0, count)
                output.flush()
            }
        } catch (_: Exception) {
        } finally {
            try { peer.shutdownOutput() } catch (_: Exception) {}
        }
    }

    private fun readLine(input: InputStream): String? {
        val bytes = ByteArrayOutputStream()
        while (bytes.size() <= MAX_HEADER) {
            val b = input.read()
            if (b < 0) return if (bytes.size() == 0) null else bytes.toString("ISO-8859-1")
            if (b == 10) {
                val data = bytes.toByteArray()
                val length = if (data.isNotEmpty() && data.last() == 13.toByte()) data.size - 1 else data.size
                return String(data, 0, length, Charsets.ISO_8859_1)
            }
            bytes.write(b)
        }
        error("HTTP header line too long")
    }

    private fun readExact(input: InputStream, length: Int): ByteArray {
        val result = ByteArray(length)
        var offset = 0
        while (offset < length) {
            val count = input.read(result, offset, length - offset)
            if (count < 0) error("Unexpected EOF during SOCKS5 handshake")
            offset += count
        }
        return result
    }

    private fun sendError(output: OutputStream, code: Int, reason: String) {
        val body = reason.toByteArray(Charsets.UTF_8)
        output.write("HTTP/1.1 $code $reason\r\nConnection: close\r\nContent-Length: ${body.size}\r\n\r\n".toByteArray(Charsets.ISO_8859_1))
        output.write(body)
        output.flush()
    }
}
