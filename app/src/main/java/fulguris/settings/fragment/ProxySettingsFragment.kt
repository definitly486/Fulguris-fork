package fulguris.settings.fragment

import android.os.Bundle
import android.content.Context
import android.util.Base64
import android.os.Build
import android.net.Uri
import android.text.InputType
import android.view.ViewGroup
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import androidx.preference.Preference
import androidx.activity.result.contract.ActivityResultContracts
import androidx.preference.PreferenceManager
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import dagger.hilt.android.AndroidEntryPoint
import fulguris.R
import fulguris.extensions.find
import fulguris.network.ProxySettings
import fulguris.extensions.snackbar
import org.json.JSONObject
import java.io.IOException
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.PBEKeySpec
import javax.crypto.spec.SecretKeySpec

@AndroidEntryPoint
class ProxySettingsFragment : AbstractSettingsFragment() {

    override fun titleResourceId(): Int = R.string.pref_title_socks5_proxy

    override fun providePreferencesXmlResource(): Int = R.xml.preference_proxy

    private val foxyProxyImportPicker =
        registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
            uri?.let { importFoxyProxy(it) }
        }

    private val proxyExportPicker =
        registerForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri: Uri? ->
            uri?.let { exportProxySettings(it) }
        }

    private val proxyImportPicker =
        registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
            uri?.let { importProxySettings(it) }
        }

    private fun proxySettingsJson(context: Context): JSONObject {
        val prefs = PreferenceManager.getDefaultSharedPreferences(context)
        return JSONObject()
            .put("format", "fulguris-socks5-proxy")
            .put("version", 1)
            .put("enabled", prefs.getBoolean(getString(R.string.pref_key_socks5_proxy_enabled), false))
            .put("host", prefs.getString(getString(R.string.pref_key_socks5_proxy_host), "").orEmpty())
            .put("port", prefs.getString(getString(R.string.pref_key_socks5_proxy_port), "1080").orEmpty())
            .put("username", prefs.getString(getString(R.string.pref_key_socks5_proxy_username), "").orEmpty())
            .put("password", prefs.getString(getString(R.string.pref_key_socks5_proxy_password), "").orEmpty())
            .put("patterns", prefs.getString(getString(R.string.pref_key_socks5_proxy_patterns), "").orEmpty())
    }

    private fun exportProxySettings(uri: Uri) {
        val password = EditText(requireContext()).apply {
            hint = getString(R.string.pref_hint_proxy_backup_password)
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
        val confirmation = EditText(requireContext()).apply {
            hint = getString(R.string.pref_hint_proxy_backup_password_confirm)
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
        val fields = LinearLayout(requireContext()).apply {
            orientation = LinearLayout.VERTICAL
            val pad = (20 * resources.displayMetrics.density).toInt()
            setPadding(pad, 0, pad, 0)
            addView(password)
            addView(confirmation)
        }
        val dialog = MaterialAlertDialogBuilder(requireContext())
            .setTitle(R.string.pref_title_proxy_backup_password)
            .setMessage(R.string.pref_message_proxy_backup_password)
            .setView(fields)
            .setNegativeButton(android.R.string.cancel, null)
            .setPositiveButton(R.string.pref_action_socks5_proxy_export, null)
            .create()
        dialog.setOnShowListener {
            dialog.getButton(androidx.appcompat.app.AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val pass = password.text.toString()
                if (pass.length < 8) {
                    password.error = getString(R.string.pref_error_proxy_backup_password_short)
                    return@setOnClickListener
                }
                if (pass != confirmation.text.toString()) {
                    confirmation.error = getString(R.string.pref_error_proxy_backup_password_mismatch)
                    return@setOnClickListener
                }
                try {
                    val plain = proxySettingsJson(requireContext()).toString().toByteArray(Charsets.UTF_8)
                    val encrypted = encryptProxyBackup(plain, pass)
                    requireContext().contentResolver.openOutputStream(uri)?.use { it.write(encrypted) }
                        ?: throw IOException("Cannot open destination")
                    dialog.dismiss()
                    activity?.snackbar(R.string.pref_message_socks5_proxy_export_success)
                } catch (error: Exception) {
                    password.error = error.message ?: getString(R.string.pref_message_socks5_proxy_export_failed_generic)
                }
            }
        }
        dialog.show()
    }

    private fun importProxySettings(uri: Uri) {
        try {
            val data = requireContext().contentResolver.openInputStream(uri)?.use { it.readBytes() }
                ?: throw IOException("Cannot read selected file")
            val password = EditText(requireContext()).apply {
                hint = getString(R.string.pref_hint_proxy_backup_password)
                inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            }
            MaterialAlertDialogBuilder(requireContext())
                .setTitle(R.string.pref_title_proxy_backup_password)
                .setMessage(R.string.pref_message_proxy_backup_import_password)
                .setView(password)
                .setNegativeButton(android.R.string.cancel, null)
                .setPositiveButton(android.R.string.ok) { _, _ ->
                    try {
                        val plain = decryptProxyBackup(data, password.text.toString())
                        applyProxySettings(JSONObject(String(plain, Charsets.UTF_8)))
                    } catch (error: Exception) {
                        if (isAdded) MaterialAlertDialogBuilder(requireContext())
                            .setTitle(R.string.pref_title_socks5_proxy_import_settings)
                            .setMessage(R.string.pref_error_proxy_backup_decrypt)
                            .setPositiveButton(android.R.string.ok, null).show()
                    }
                }.show()
        } catch (error: Exception) {
            showProxyImportError(error)
        }
    }

    private fun applyProxySettings(root: JSONObject) {
        if (root.optString("format") != "fulguris-socks5-proxy" || root.optInt("version") != 1)
            throw IllegalArgumentException("Unsupported proxy settings file")
        val host = root.optString("host").trim()
        val port = root.optString("port", "1080").trim()
        val enabled = root.optBoolean("enabled", false)
        val portNumber = port.toIntOrNull()
        if (enabled && (host.isEmpty() || portNumber == null || portNumber !in 1..65535))
            throw IllegalArgumentException("Invalid SOCKS5 server address or port")
        val prefs = PreferenceManager.getDefaultSharedPreferences(requireContext())
        prefs.edit()
            .putBoolean(getString(R.string.pref_key_socks5_proxy_enabled), enabled)
            .putString(getString(R.string.pref_key_socks5_proxy_host), host)
            .putString(getString(R.string.pref_key_socks5_proxy_port), port)
            .putString(getString(R.string.pref_key_socks5_proxy_username), root.optString("username"))
            .putString(getString(R.string.pref_key_socks5_proxy_password), root.optString("password"))
            .putString(getString(R.string.pref_key_socks5_proxy_patterns), root.optString("patterns"))
            .apply()
        val rules = root.optString("patterns").lineSequence().map { it.trim() }
            .filter { it.isNotEmpty() && !it.startsWith("#") }.count()
        find<Preference>(R.string.pref_key_socks5_proxy_patterns)?.summary =
            if (rules == 0) getString(R.string.pref_summary_socks5_proxy_patterns_empty)
            else resources.getQuantityString(R.plurals.pref_summary_socks5_proxy_patterns_count, rules, rules)
        activity?.snackbar(R.string.pref_message_socks5_proxy_import_settings_success)
    }

    private fun showProxyImportError(error: Exception) {
        if (!isAdded) return
        MaterialAlertDialogBuilder(requireContext())
            .setTitle(R.string.pref_title_socks5_proxy_import_settings)
            .setMessage(getString(R.string.pref_message_socks5_proxy_import_settings_failed, error.message ?: ""))
            .setPositiveButton(android.R.string.ok, null).show()
    }

    private fun encryptProxyBackup(plain: ByteArray, password: String): ByteArray {
        val random = SecureRandom()
        val salt = ByteArray(16).also { random.nextBytes(it) }
        val iv = ByteArray(12).also { random.nextBytes(it) }
        val iterations = 250_000
        val algorithm = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) "PBKDF2WithHmacSHA256" else "PBKDF2WithHmacSHA1"
        val spec = PBEKeySpec(password.toCharArray(), salt, iterations, 256)
        val key = SecretKeySpec(SecretKeyFactory.getInstance(algorithm).generateSecret(spec).encoded, "AES")
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key, GCMParameterSpec(128, iv))
        return JSONObject().put("format", "fulguris-socks5-proxy-encrypted").put("version", 1)
            .put("kdf", algorithm).put("iterations", iterations)
            .put("salt", Base64.encodeToString(salt, Base64.NO_WRAP))
            .put("iv", Base64.encodeToString(iv, Base64.NO_WRAP))
            .put("data", Base64.encodeToString(cipher.doFinal(plain), Base64.NO_WRAP))
            .toString(2).toByteArray(Charsets.UTF_8)
    }

    private fun decryptProxyBackup(data: ByteArray, password: String): ByteArray {
        val envelope = JSONObject(String(data, Charsets.UTF_8))
        if (envelope.optString("format") != "fulguris-socks5-proxy-encrypted" || envelope.optInt("version") != 1)
            throw IllegalArgumentException("Not an encrypted proxy backup")
        val iterations = envelope.getInt("iterations")
        if (iterations !in 100_000..1_000_000) throw IllegalArgumentException("Invalid KDF parameters")
        val algorithm = envelope.getString("kdf")
        if (algorithm != "PBKDF2WithHmacSHA256" && algorithm != "PBKDF2WithHmacSHA1")
            throw IllegalArgumentException("Unsupported key derivation algorithm")
        val salt = Base64.decode(envelope.getString("salt"), Base64.NO_WRAP)
        val iv = Base64.decode(envelope.getString("iv"), Base64.NO_WRAP)
        val encrypted = Base64.decode(envelope.getString("data"), Base64.NO_WRAP)
        if (salt.size != 16 || iv.size != 12) throw IllegalArgumentException("Invalid encrypted backup")
        val spec = PBEKeySpec(password.toCharArray(), salt, iterations, 256)
        val key = SecretKeySpec(SecretKeyFactory.getInstance(algorithm).generateSecret(spec).encoded, "AES")
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, iv))
        return cipher.doFinal(encrypted)
    }

    private fun importFoxyProxy(uri: Uri) {
        try {
            val json = requireContext().contentResolver.openInputStream(uri)
                ?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }
                ?: throw IllegalArgumentException("Cannot read selected file")
            val root = JSONObject(json)
            val profiles = root.optJSONArray("data")
                ?: throw IllegalArgumentException("FoxyProxy data array is missing")

            var selected: JSONObject? = null
            for (index in 0 until profiles.length()) {
                val candidate = profiles.optJSONObject(index) ?: continue
                if (candidate.optBoolean("active", true) &&
                    candidate.optString("type").equals("socks5", ignoreCase = true)
                ) {
                    selected = candidate
                    break
                }
            }
            val profile = selected ?: throw IllegalArgumentException("No active SOCKS5 profile found")
            val host = profile.optString("hostname").trim()
            val port = profile.optString("port").trim()
            val portNumber = port.toIntOrNull()
            if (host.isEmpty() || portNumber == null || portNumber !in 1..65535) {
                throw IllegalArgumentException("Invalid SOCKS5 host or port")
            }

            val rules = mutableListOf<String>()
            fun appendRules(arrayName: String, excluded: Boolean) {
                val array = profile.optJSONArray(arrayName) ?: return
                for (index in 0 until array.length()) {
                    val rule = array.optJSONObject(index) ?: continue
                    if (!rule.optBoolean("active", true)) continue
                    val pattern = rule.optString("pattern").trim()
                    if (pattern.isEmpty()) continue
                    val type = rule.optString("type", "wildcard").lowercase()
                    val normalized = when (type) {
                        "regex", "regexp", "regular expression" ->
                            if (pattern.startsWith("re:", true)) pattern else "re:$pattern"
                        else -> pattern
                    }
                    rules += if (excluded) "!$normalized" else normalized
                }
            }
            appendRules("include", false)
            appendRules("exclude", true)

            val prefs = PreferenceManager.getDefaultSharedPreferences(requireContext())
            val patternsKey = getString(R.string.pref_key_socks5_proxy_patterns)
            prefs.edit()
                .putString(getString(R.string.pref_key_socks5_proxy_host), host)
                .putString(getString(R.string.pref_key_socks5_proxy_port), port)
                .putString(getString(R.string.pref_key_socks5_proxy_username), profile.optString("username"))
                .putString(getString(R.string.pref_key_socks5_proxy_password), profile.optString("password"))
                .putString(patternsKey, rules.joinToString("\n"))
                .putBoolean(getString(R.string.pref_key_socks5_proxy_enabled), true)
                .apply()

            find<Preference>(R.string.pref_key_socks5_proxy_patterns)?.summary =
                if (rules.isEmpty()) getString(R.string.pref_summary_socks5_proxy_patterns_empty)
                else resources.getQuantityString(R.plurals.pref_summary_socks5_proxy_patterns_count, rules.size, rules.size)
            activity?.snackbar(getString(R.string.pref_message_socks5_proxy_import_success, rules.size))
        } catch (error: Exception) {
            if (isAdded) {
                MaterialAlertDialogBuilder(requireContext())
                    .setTitle(R.string.pref_title_socks5_proxy_import_foxyproxy)
                    .setMessage(getString(R.string.pref_message_socks5_proxy_import_failed, error.message ?: "Invalid file"))
                    .setPositiveButton(android.R.string.ok, null)
                    .show()
            }
        }
    }

    override fun onCreatePreferences(savedInstanceState: Bundle?, rootKey: String?) {
        super.onCreatePreferences(savedInstanceState, rootKey)

        val preferences = PreferenceManager.getDefaultSharedPreferences(requireContext())
        val patternsKey = getString(R.string.pref_key_socks5_proxy_patterns)
        val patternsPreference = find<Preference>(R.string.pref_key_socks5_proxy_patterns)

        fun updatePatternsSummary() {
            val rules = preferences.getString(patternsKey, "").orEmpty()
                .lineSequence().map { it.trim() }
                .filter { it.isNotEmpty() && !it.startsWith("#") }.count()
            patternsPreference?.summary = if (rules == 0) {
                getString(R.string.pref_summary_socks5_proxy_patterns_empty)
            } else {
                resources.getQuantityString(R.plurals.pref_summary_socks5_proxy_patterns_count, rules, rules)
            }
        }

        updatePatternsSummary()

        preferenceScreen.addPreference(Preference(requireContext()).apply {
            title = getString(R.string.pref_title_socks5_proxy_export)
            summary = getString(R.string.pref_summary_socks5_proxy_export)
            setIcon(R.drawable.ic_cloud_upload_outline)
            isSingleLineTitle = false
            setOnPreferenceClickListener {
                MaterialAlertDialogBuilder(requireContext())
                    .setTitle(R.string.pref_title_socks5_proxy_export_confirm)
                    .setMessage(R.string.pref_message_socks5_proxy_export_confirm)
                    .setNegativeButton(android.R.string.cancel, null)
                    .setPositiveButton(R.string.pref_action_socks5_proxy_export) { _, _ ->
                        proxyExportPicker.launch("Fulguris-SOCKS5-Settings.enc.json")
                    }
                    .show()
                true
            }
        })

        preferenceScreen.addPreference(Preference(requireContext()).apply {
            title = getString(R.string.pref_title_socks5_proxy_import_settings)
            summary = getString(R.string.pref_summary_socks5_proxy_import_settings)
            setIcon(R.drawable.ic_cloud_download_outline)
            isSingleLineTitle = false
            setOnPreferenceClickListener {
                proxyImportPicker.launch(arrayOf("application/json", "text/plain", "application/octet-stream"))
                true
            }
        })

        preferenceScreen.addPreference(Preference(requireContext()).apply {
            title = getString(R.string.pref_title_socks5_proxy_import_foxyproxy)
            summary = getString(R.string.pref_summary_socks5_proxy_import_foxyproxy)
            setIcon(R.drawable.ic_file_import)
            isSingleLineTitle = false
            setOnPreferenceClickListener {
                foxyProxyImportPicker.launch(arrayOf("application/json", "text/plain", "application/octet-stream"))
                true
            }
        })

        patternsPreference?.setOnPreferenceClickListener {
            val editor = EditText(requireContext()).apply {
                setText(preferences.getString(patternsKey, "").orEmpty())
                inputType = InputType.TYPE_CLASS_TEXT or
                    InputType.TYPE_TEXT_FLAG_MULTI_LINE or
                    InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
                minLines = 10
                maxLines = 18
                gravity = android.view.Gravity.TOP or android.view.Gravity.START
                setHorizontallyScrolling(false)
                textSize = 14f
                setPadding(24, 20, 24, 20)
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT
                )
            }
            val scroll = ScrollView(requireContext()).apply {
                addView(editor)
                setPadding(8, 0, 8, 0)
            }
            MaterialAlertDialogBuilder(requireContext())
                .setTitle(R.string.pref_title_socks5_proxy_patterns)
                .setMessage(R.string.pref_message_socks5_proxy_patterns_editor)
                .setView(scroll)
                .setNegativeButton(android.R.string.cancel, null)
                .setNeutralButton(R.string.pref_action_patterns_examples) { _, _ ->
                    MaterialAlertDialogBuilder(requireContext())
                        .setTitle(R.string.pref_action_patterns_examples)
                        .setMessage(R.string.pref_message_socks5_proxy_patterns_examples)
                        .setPositiveButton(android.R.string.ok, null)
                        .show()
                }
                .setPositiveButton(android.R.string.ok) { _, _ ->
                    preferences.edit().putString(patternsKey, editor.text.toString()).apply()
                    updatePatternsSummary()
                }
                .show()
            true
        }

        find<Preference>(R.string.pref_key_socks5_proxy_test)?.setOnPreferenceClickListener {
            val config = ProxySettings.read(requireContext())
            val progress = MaterialAlertDialogBuilder(requireContext())
                .setTitle(R.string.pref_title_socks5_proxy_test)
                .setMessage(R.string.pref_summary_socks5_proxy_test_running)
                .setCancelable(false)
                .create()
            progress.show()

            Thread({
                val result = fulguris.network.Socks5ProxyClient.testConnection(
                    config.host, config.port, config.username, config.password
                )
                activity?.runOnUiThread {
                    if (isAdded) {
                        progress.dismiss()
                        val message = if (result.success) {
                            getString(R.string.pref_summary_socks5_proxy_test_success, result.httpCode ?: 0)
                        } else {
                            getString(R.string.pref_summary_socks5_proxy_test_failed, result.error ?: "")
                        }
                        MaterialAlertDialogBuilder(requireContext())
                            .setTitle(R.string.pref_title_socks5_proxy_test)
                            .setMessage(message)
                            .setPositiveButton(android.R.string.ok, null)
                            .show()
                    }
                }
            }, "Socks5ProxyTest").start()
            true
        }
    }
}
