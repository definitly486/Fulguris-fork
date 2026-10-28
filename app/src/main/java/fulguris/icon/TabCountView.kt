package fulguris.icon

import fulguris.R
import fulguris.extensions.preferredLocale
import fulguris.extensions.scale
import android.content.Context
import android.graphics.*
import android.util.AttributeSet
import android.view.View
import androidx.core.content.withStyledAttributes
import java.text.NumberFormat

/**
 * A view that draws a count enclosed by a border. Defaults to drawing zero, draws infinity if the
 * number is greater than 99.
 *
 * Attributes:
 * - [R.styleable.TabCountView_tabIconColor] - The color used to draw the number and border.
 * Defaults to black.
 * - [R.styleable.TabCountView_tabIconTextSize] - The count text size, defaults to 14.
 * - [R.styleable.TabCountView_tabIconBorderRadius] - The radius of the border's corners. Defaults
 * to 0.
 * - [R.styleable.TabCountView_tabIconBorderWidth] - The width of the border. Defaults to 0.
 */
class TabCountView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    private val numberFormat = NumberFormat.getInstance(context.preferredLocale)
    private val paint: Paint = Paint().apply {
        typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        isAntiAlias = true
        textAlign = Paint.Align.CENTER
    }
    private var borderRadius: Float = 0F
    private var borderWidth: Float = 0F
    private val workingRect = RectF()

    private var count: Int = 0
    public var textColor: Int = Color.BLACK

    init {
        context.withStyledAttributes(attrs, R.styleable.TabCountView) {
            paint.color = getColor(R.styleable.TabCountView_tabIconColor, Color.BLACK)
            textColor = paint.color
            borderRadius = getDimension(R.styleable.TabCountView_tabIconBorderRadius, 0F)
            borderWidth = getDimension(R.styleable.TabCountView_tabIconBorderWidth, 0F)
        }
    }

    /**
     * Update the number count displayed by the view.
     */
    fun updateCount(count: Int) {
        this.count = count
        contentDescription = count.toString()
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        val text: String = if (count > MAX_DISPLAYABLE_NUMBER) {
            context.getString(R.string.infinity)
        } else {
            numberFormat.format(count)
        }

        // Square frame centered in the view, recomputed on every draw so size changes are handled.
        val side = minOf(width, height).toFloat() * 0.6f
        val left = (width - side) / 2f
        val top = (height - side) / 2f
        workingRect.set(left, top, left + side, top + side)

        paint.color = textColor
        paint.style = Paint.Style.STROKE
        paint.strokeWidth = borderWidth
        canvas.drawRoundRect(workingRect, borderRadius, borderRadius, paint)

        // Text scaled to fit inside the frame
        paint.style = Paint.Style.FILL
        paint.textSize = side * if (text.length <= 1) 0.62f else if (text.length == 2) 0.5f else 0.38f
        val xPos = width / 2F
        val yPos = height / 2F - (paint.descent() + paint.ascent()) / 2
        canvas.drawText(text, xPos, yPos, paint)
    }

    companion object {
        private const val MAX_DISPLAYABLE_NUMBER = 999
    }

}
