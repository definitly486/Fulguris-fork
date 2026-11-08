package fulguris.settings.fragment

import fulguris.R
import fulguris.extensions.find
import fulguris.network.ProxySettings
import fulguris.network.Socks5ProxyClient
import android.os.Bundle
import androidx.preference.Preference
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class ProxySettingsFragment : AbstractSettingsFragment() {

    override fun titleResourceId(): Int = R.string.pref_title_socks5_proxy

    override fun providePreferencesXmlResource(): Int = R.xml.preference_proxy

    override fun onCreatePreferences(savedInstanceState: Bundle?, rootKey: String?) {
        super.onCreatePreferences(savedInstanceState, rootKey)

        val patternsPreference = find<Preference>(R.string.pref_key_socks5_proxy_patterns)
        patternsPreference?.summary = getString(R.string.pref_summary_socks5_proxy_patterns)

        find<Preference>(R.string.pref_key_socks5_proxy_test)?.setOnPreferenceClickListener {
            val config = ProxySettings.read(requireContext())
            val progress = MaterialAlertDialogBuilder(requireContext())
                .setTitle(R.string.pref_title_socks5_proxy_test)
                .setMessage(R.string.pref_summary_socks5_proxy_test_running)
                .setCancelable(false)
                .create()
            progress.show()

            Thread({
                val result = Socks5ProxyClient.testConnection(
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
