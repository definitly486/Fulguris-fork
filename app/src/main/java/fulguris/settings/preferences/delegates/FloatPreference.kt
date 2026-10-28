package fulguris.settings.preferences.delegates

import fulguris.app
import android.content.SharedPreferences
import androidx.annotation.IntegerRes
import androidx.annotation.StringRes
import kotlin.properties.ReadWriteProperty
import kotlin.reflect.KProperty

/**
 * An [Float] delegate that is backed by [SharedPreferences].
 */
private class FloatPreferenceDelegate(
    private val name: String,
    private val defaultValue: Float,
    private val preferences: SharedPreferences
) : ReadWriteProperty<Any, Float> {
    override fun getValue(thisRef: Any, property: KProperty<*>): Float =
        preferences.getFloat(name, defaultValue)

    override fun setValue(thisRef: Any, property: KProperty<*>, value: Float) {
        preferences.edit().putFloat(name, value).apply()
    }

}

/**
 * Creates a [Float] from [SharedPreferences] with the provide arguments.
 */
fun SharedPreferences.floatPreference(
    name: String,
    defaultValue: Float = 0F
): ReadWriteProperty<Any, Float> = FloatPreferenceDelegate(name, defaultValue, this)


/**
 * Creates a [Float] from [SharedPreferences] with the provide arguments.
 */
fun SharedPreferences.floatPreference(
        @StringRes stringRes: Int,
        defaultValue: Float = 0F
): ReadWriteProperty<Any, Float> = FloatPreferenceDelegate(app.resources.getString(stringRes), defaultValue, this)

/**
 * Like [floatPreference], but tolerant of the value being stored under a different primitive
 * type (e.g. an int left by an earlier build of a setting that used to be a [SeekBarPreference]):
 * the read falls back to the default instead of throwing a [ClassCastException], and the next
 * write self-heals the stored type.
 */
fun SharedPreferences.safeFloatPreference(
    name: String,
    defaultValue: Float = 0F
): ReadWriteProperty<Any, Float> = object : ReadWriteProperty<Any, Float> {
    override fun getValue(thisRef: Any, property: KProperty<*>): Float =
        try {
            getFloat(name, defaultValue)
        } catch (ex: ClassCastException) {
            defaultValue
        }

    override fun setValue(thisRef: Any, property: KProperty<*>, value: Float) {
        edit().putFloat(name, value).apply()
    }
}

/**
 * Creates a [Float] from [SharedPreferences] with the provide arguments (see [safeFloatPreference]).
 */
fun SharedPreferences.safeFloatPreference(
    @StringRes stringRes: Int,
    defaultValue: Float = 0F
): ReadWriteProperty<Any, Float> = safeFloatPreference(app.resources.getString(stringRes), defaultValue)

/**
 * Creates a [Float] from [SharedPreferences] with the provide arguments.
 */
fun SharedPreferences.floatResPreference(
    @StringRes stringRes: Int,
    @IntegerRes intRes: Int
): ReadWriteProperty<Any, Float> = FloatPreferenceDelegate(app.resources.getString(stringRes), app.resources.getInteger(intRes).toFloat(), this)

