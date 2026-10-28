/*
 * The contents of this file are subject to the Common Public Attribution License Version 1.0.
 * (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at:
 * https://github.com/Slion/Fulguris/blob/main/LICENSE.CPAL-1.0.
 * The License is based on the Mozilla Public License Version 1.1, but Sections 14 and 15 have been
 * added to cover use of software over a computer network and provide for limited attribution for
 * the Original Developer. In addition, Exhibit A has been modified to be consistent with Exhibit B.
 *
 * Software distributed under the License is distributed on an "AS IS" basis, WITHOUT WARRANTY OF
 * ANY KIND, either express or implied. See the License for the specific language governing rights
 * and limitations under the License.
 *
 * The Original Code is Fulguris.
 *
 * The Original Developer is the Initial Developer.
 * The Initial Developer of the Original Code is Stéphane Lenclud.
 *
 * All portions of the code written by Stéphane Lenclud are Copyright © 2020 Stéphane Lenclud.
 * All Rights Reserved.
 */

package fulguris.cursor

/**
 * Everything [CursorController] needs to read from the hosting app's settings.
 *
 * Kept as a tiny interface (rather than a dependency on Fulguris' `UserPreferences`) so the whole
 * `cursor` package stays free of app specifics and can be pulled into a standalone library.
 */
interface CursorSettings {
    /** Whether the long-press hardware hotkey may toggle the cursor on/off. The menu item ignores this. */
    val hotkeyEnabled: Boolean

    /**
     * Cursor speed, 0..100 (percent). 0 is a valid setting but must be treated as 1 by the
     * consumer (the slowest usable speed). Mapped to a physical travel speed (cm/s) using the
     * display's DPI.
     */
    val speed: Float

    /** Cursor acceleration, 0..100 (percent). Mapped to a physical acceleration (cm/s²) while a direction is held. */
    val acceleration: Float

    /**
     * Seconds of no cursor movement after which the cursor fades out. 0 means never fade.
     * Any new movement fades it straight back in.
     */
    val fadeTimeoutSec: Float

    /**
     * Seconds the action key (select / DPAD center / ENTER) must be deliberately held to
     * perform a long press at the cursor and open the context menu; a shorter press is a click.
     * The controller clamps this to [minActionHoldSec] so hesitant short clicks never trigger it.
     */
    val actionHoldSec: Float

    /** Minimum the controller accepts for [actionHoldSec]: 0.5 s. */
    val minActionHoldSec: Float
}
