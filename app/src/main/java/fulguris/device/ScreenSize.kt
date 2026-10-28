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
     * True for large screens such as tablets with a display diagonal of [LARGE_SCREEN_MIN_INCHES] or more.
     *
     * The physical size reported by many cheap tablets is wrong (dpi often just mirrors the density
     * bucket), which makes the computed diagonal too small. So a screen is also considered large when
     * it has a lot of pixels for a low density, something phones do not have.
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
        val diagonalInches = kotlin.math.sqrt(w * w + h * h)
        if (diagonalInches >= LARGE_SCREEN_MIN_INCHES) return true

        // Fallback for wrong reported dpi: 800+ px on the short side with a density of 280 dpi or less
        // (phones with such a resolution use much higher densities)
        val shortSidePx = minOf(metrics.widthPixels, metrics.heightPixels)
        return shortSidePx >= 800 && metrics.densityDpi <= 280
    }

    companion object {
        const val LARGE_SCREEN_MIN_INCHES = 8.0
    }

}
