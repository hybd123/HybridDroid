/*
 * This code is licensed under the Fastbot license. You may obtain a copy of this license in the LICENSE.txt file in the root directory of this source tree.
 */

package com.android.commands.monkey.fastbot.client;

/**
 * @author Zhao Zhang
 */

/**
 * action type class
 *
 */
public enum ActionType {

    /**
     * Phantom action for logging.
     */
    CRASH,
    /**
     * Fuzz action
     */
    FUZZ,
    /**
     * Used for starting activities
     */
    START,
    /**
     * kill the process and start the activity
     */
    RESTART,
    /**
     * Kill the process and clean the app cache, and start the activity
     */
    CLEAN_RESTART,
    /**
     * Used for throttle
     */
    NOP,
    /**
     * Used for clicking app switch key, should bring up the application switcher dialog.
     */
    ACTIVATE,
    /**
     * action can be used as a label of an edge in the model.
     */
    BACK,
    /**
     * @deprecated feed stream swipe，Abandoned
     */
    FEED,
    /**
     * Used for clicking components and inputting text if needed.
     */
    CLICK,
    /**
     * Perform long click
     */
    LONG_CLICK,
    /**
     * Scroll from top down to bottom
     */
    SCROLL_TOP_DOWN,
    /**
     * Scroll from bottom up to top
     */
    SCROLL_BOTTOM_UP,
    /**
     * Scroll from left to right
     */
    SCROLL_LEFT_RIGHT,
    /**
     * Scroll from right to left
     */
    SCROLL_RIGHT_LEFT,
    /**
     * Scroll from bottom up to top for N times
     */
    SCROLL_BOTTOM_UP_N,

    /**
     * Used for generate shell event
     */
    SHELL_EVENT,
    // Enum types above are the same with of cpp, so they should be identical!
    // Enum types below are out of the scope of the c++ native code.

    // xmq
    ROTATE_SCREEN;


    /**
     * Check if this action type needs a target to interact with
     * @return If this action needs target, return true
     */
    public boolean requireTarget() {
        int ord = ordinal();
        return ord >= CLICK.ordinal() && ord <= SCROLL_BOTTOM_UP_N.ordinal();
    }

    /**
     * Check if this action could be generated by cpp native model
     * @return True if this type of action could be generated by native model
     */
    public boolean isModelAction() {
        int ord = ordinal();
        return ord >= BACK.ordinal() && ord <= SHELL_EVENT.ordinal();
    }
}
