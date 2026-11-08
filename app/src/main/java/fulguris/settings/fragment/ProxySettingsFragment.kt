package fulguris.settings.fragment

import android.os.Bundle
import android.text.InputType
import android.view.ViewGroup
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import androidx.preference.Preference
import androidx.preference.PreferenceManager
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import dagger.hilt.android.AndroidEntryPoint
import fulguris.R
import fulguris.extensions.find
import fulguris.network.ProxySettings

@AndroidEntryPoint
class ProxySettingsFragment : AbstractSettingsFragment() {

    override fun titleResourceId(): Int = R.string.pref_title_socks5_proxy

    override fun providePreferencesXmlResource(): Int = R.xml.preference_proxy

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
