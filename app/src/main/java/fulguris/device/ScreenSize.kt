package fulguris.device

import android.content.Context
import android.content.res.Configuration
import android.hardware.display.DisplayManager
import android.util.DisplayMetrics
import android.view.Display
import dagger.Reusable
import javax.inject.Inject

/**
 * A model used to determine the screen size info.
 *
 * Created by anthonycr on 2/19/18.
 */
@Reusable
class ScreenSize @Inject constructor(private val context: Context) {

    fun isTablet(): Boolean =
        context.resources.configuration.screenLayout and Configuration.SCREENLAYOUT_SIZE_MASK == Configuration.SCREENLAYOUT_SIZE_XLARGE

    /**
     * True when the physical display diagonal is [LARGE_SCREEN_MIN_INCHES] or more.
     * Uses the real display size so it does not change with split-screen or window resizing.
     */
    fun isLargeScreen(): Boolean {
        val metrics = DisplayMetrics()
        val display = (context.getSystemService(Context.DISPLAY_SERVICE) as? DisplayManager)
            ?.getDisplay(Display.DEFAULT_DISPLAY) ?: return false
        @Suppress("DEPRECATION")
        display.getRealMetrics(metrics)
        val xdpi = if (metrics.xdpi > 0f) metrics.xdpi else metrics.densityDpi.toFloat()
        val ydpi = if (metrics.ydpi > 0f) metrics.ydpi else metrics.densityDpi.toFloat()
        val w = metrics.widthPixels / xdpi
        val h = metrics.heightPixels / ydpi
        return kotlin.math.sqrt(w * w + h * h) >= LARGE_SCREEN_MIN_INCHES
    }

    companion object {
        const val LARGE_SCREEN_MIN_INCHES = 8.0
    }

}
