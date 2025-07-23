/*
 * Copyright (C) 2008 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.android.commands.monkey.source;

import android.annotation.TargetApi;
import android.app.UiAutomationConnection;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.content.Context;
import android.graphics.Rect;
import android.os.Build;
import android.os.HandlerThread;
import android.app.UiAutomation;
import android.content.ComponentName;
import android.content.pm.ActivityInfo;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.PointF;
import android.hardware.display.DisplayManagerGlobal;
import android.os.SystemClock;
import android.util.DisplayMetrics;
import android.view.Display;
import android.view.KeyCharacterMap;
import android.view.KeyEvent;
import android.view.MotionEvent;

import android.view.Surface;
import android.view.accessibility.AccessibilityNodeInfo;

import com.android.commands.monkey.action.Action;
import com.android.commands.monkey.action.LLMAction;
import com.android.commands.monkey.events.base.MonkeyCommandEvent;
import com.android.commands.monkey.events.base.MonkeyWaitEvent;
import com.android.commands.monkey.fastbot.client.ActionType;
import com.android.commands.monkey.utils.*;
import com.android.commands.monkey.utils.Logger;
import com.android.commands.monkey.utils.UITarpitDetector;
import com.android.commands.monkey.events.MonkeyEvent;
import com.android.commands.monkey.events.MonkeyEventQueue;
import com.android.commands.monkey.events.MonkeyEventSource;
import com.android.commands.monkey.events.base.MonkeyActivityEvent;
import com.android.commands.monkey.events.base.MonkeyKeyEvent;
import com.android.commands.monkey.events.base.MonkeyRotationEvent;
import com.android.commands.monkey.events.base.MonkeyThrottleEvent;
import com.android.commands.monkey.events.base.MonkeyTouchEvent;
import com.android.commands.monkey.events.base.MonkeyTrackballEvent;
import com.android.commands.monkey.framework.AndroidDevice;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.IOException;
import java.util.*;
import java.lang.Exception;
import java.util.concurrent.TimeoutException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;


import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

import static com.android.commands.monkey.fastbot.client.ActionType.SCROLL_BOTTOM_UP;
import static com.android.commands.monkey.utils.Config.SIM_K;
import static com.android.commands.monkey.utils.Config.bytestStatusBarHeight;
import static com.android.commands.monkey.utils.Config.imageWriterCount;
import static com.android.commands.monkey.utils.Config.refectchInfoCount;
import static com.android.commands.monkey.utils.Config.refectchInfoWaitingInterval;
import static com.android.commands.monkey.utils.Config.startAfterNSecondsofsleep;
import static com.android.commands.monkey.utils.Config.swipeDuration;
import static com.android.commands.monkey.utils.Config.takeScreenshotForEveryStep;
import static com.android.commands.monkey.utils.Config.useRandomClick;


/**
 * monkey event queue
 */
public class MonkeySourceRandom implements MonkeyEventSource {

    private static long CLICK_WAIT_TIME = 0L;
    private static long LONG_CLICK_WAIT_TIME = 1000L;

    private static final String GPT_URL = ""; # replace your own API key
    private static final String GPT_KEY = "";
    private static final String task = "You are an expert in App GUI testing. Please guide the testing tool to enhance the coverage of functional scenarios in testing the App based on your extensive App testing experience. ";

    private String currentactivity = "";
    private int actionIdCounter = 0;
    private String packageName = "";

    private int timestamp = 0;
    private int lastInputTimestamp = -1;
    private int mEventId = 0 ;
    private int mEventCount = 0;  // total number of events generated so far
    private int timeStep=0;
    private Random mRandom;
    private List<ComponentName> mMainApps;
    private String intentAction = null;
    private String quickActivity = null;
    private String intentData = null;
    private int statusBarHeight = bytestStatusBarHeight;

    private HashSet<String> activityHistory = new HashSet<>();
    private HashSet<String> llmActionHistory = new HashSet<>();
    private MonkeyEventQueue mQ;
    private List<LLMAction> actionList = new ArrayList<>();
    private File mOutputDirectory;
    private ImageWriterQueue[] mImageWriters;
    private static Locale stringFormatLocale = Locale.ENGLISH;
    private String appVersion = "";
    private int mVerbose = 0;

    protected Context systemContext;
    protected UiAutomation mUiAutomation;

    public File lastScreen;

    public static final int FACTOR_TOUCH = 0;
    public static final int FACTOR_MOTION = 1;
    public static final int FACTOR_PINCHZOOM = 2;
    public static final int FACTOR_TRACKBALL = 3;
    public static final int FACTOR_ROTATION = 4;
    public static final int FACTOR_PERMISSION = 5;
    public static final int FACTOR_NAV = 6;
    public static final int FACTOR_MAJORNAV = 7;
    public static final int FACTOR_SYSOPS = 8;
    public static final int FACTOR_APPSWITCH = 9;
    public static final int FACTOR_FLIP = 10;
    public static final int FACTOR_ANYTHING = 11;
    public static final int FACTORZ_COUNT = 12; // should be last+1
    //
    /**
     * Key events that move around the UI.
     */
    private static final int[] NAV_KEYS = {KeyEvent.KEYCODE_DPAD_UP, KeyEvent.KEYCODE_DPAD_DOWN,
            KeyEvent.KEYCODE_DPAD_LEFT, KeyEvent.KEYCODE_DPAD_RIGHT,};
    /**
     * Key events that perform major navigation options (so shouldn't be sent as
     * much).
     */
    private static final int[] MAJOR_NAV_KEYS = {KeyEvent.KEYCODE_MENU, /*
                                                                          * KeyEvent
                                                                          * .
                                                                          * KEYCODE_SOFT_RIGHT,
                                                                          */
            KeyEvent.KEYCODE_DPAD_CENTER,};
    /**
     * Key events that perform system operations.
     */
    private static final int[] SYS_KEYS = {KeyEvent.KEYCODE_HOME, KeyEvent.KEYCODE_BACK, KeyEvent.KEYCODE_CALL,
            KeyEvent.KEYCODE_ENDCALL, KeyEvent.KEYCODE_VOLUME_UP, KeyEvent.KEYCODE_VOLUME_DOWN,
            KeyEvent.KEYCODE_VOLUME_MUTE, KeyEvent.KEYCODE_MUTE,};
    /**
     * If a physical key exists?
     */
    private static final boolean[] PHYSICAL_KEY_EXISTS = new boolean[KeyEvent.getMaxKeyCode() + 1];
    /**
     * Possible screen rotation degrees
     **/
    private static final int[] SCREEN_ROTATION_DEGREES = {Surface.ROTATION_0, Surface.ROTATION_90,
            Surface.ROTATION_180, Surface.ROTATION_270,};
    private static final int GESTURE_TAP = 0;
    private static final int GESTURE_DRAG = 1;
    private static final int GESTURE_PINCH_OR_ZOOM = 2;

    static {
        for (int i = 0; i < PHYSICAL_KEY_EXISTS.length; ++i) {
            PHYSICAL_KEY_EXISTS[i] = true;
        }
        // Only examine SYS_KEYS
        for (int i = 0; i < SYS_KEYS.length; ++i) {
            PHYSICAL_KEY_EXISTS[SYS_KEYS[i]] = KeyCharacterMap.deviceHasKey(SYS_KEYS[i]);
        }
    }

    /**
     * percentages for each type of event. These will be remapped to working
     * values after we read any optional values.
     **/
    private float[] mFactors = new float[FACTORZ_COUNT];
    private long mThrottle = 0;
    private MonkeyPermissionUtil mPermissionUtil;
    private boolean mKeyboardOpen = false;

    private boolean mRandomizeThrottle = false;
    private HashSet<String> mTotalActivities = new HashSet<>();
    private File tempPath;
    protected final HandlerThread mHandlerThread = new HandlerThread("MonkeySourceRandom");


    private UITarpitDetector tarpitDetector;
//    private Tarpit currentTarpit;
    private boolean isLLMAction = false;

    public MonkeySourceRandom(Random random, List<ComponentName> MainApps, long throttle, boolean randomizeThrottle,
                              boolean permissionTargetSystem, File outputDirectory) {

        mRandom = random;
        mMainApps = MainApps;
        mQ = new MonkeyEventQueue(random, throttle, randomizeThrottle);
        mPermissionUtil = new MonkeyPermissionUtil();
        mPermissionUtil.setTargetSystemPackages(permissionTargetSystem);
        getTotalAcitivities();
        mOutputDirectory = outputDirectory;
        mImageWriters = new ImageWriterQueue[imageWriterCount];
        for (int i = 0; i < imageWriterCount; i++) {
            mImageWriters[i] = new ImageWriterQueue();
            Thread imageThread = new Thread(mImageWriters[i]);
            imageThread.start();
        }
        connect();

        tempPath = createDirectory("/sdcard/fastbot/tmp");
        lastScreen = takeScreenshotForEventSource("initial");

        Logger.println("initial LLMSource");
        systemContext = ContextUtils.getSystemContext();
        tarpitDetector = new UITarpitDetector(SIM_K, mQ);
        Logger.println("sim_k:"+SIM_K);
    }

    public static String getKeyName(int keycode) {
        return KeyEvent.keyCodeToString(keycode);
    }

    /**
     * Looks up the keyCode from a given KEYCODE_NAME. NOTE: This may be an
     * expensive operation.
     *
     * @param keyName the name of the KEYCODE_VALUE to lookup.
     * @returns the intenger keyCode value, or KeyEvent.KEYCODE_UNKNOWN if not
     * found
     */
    public static int getKeyCode(String keyName) {
        return KeyEvent.keyCodeFromString(keyName);
    }

    private static boolean validateKeyCategory(String catName, int[] keys, float factor) {
        if (factor < 0.1f) {
            return true;
        }
        for (int i = 0; i < keys.length; ++i) {
            if (PHYSICAL_KEY_EXISTS[keys[i]]) {
                return true;
            }
        }
        System.err.println("** " + catName + " has no physical keys but with factor " + factor + "%.");
        return false;
    }

    /**
     * Adjust the percentages (after applying user values) and then normalize to
     * a 0..1 scale.
     */
    private boolean adjustEventFactors() {
        // go through all values and compute totals for user & default values
        float userSum = 0.0f;
        float defaultSum = 0.0f;
        int defaultCount = 0;
        for (int i = 0; i < FACTORZ_COUNT; ++i) {
            if (mFactors[i] <= 0.0f) { // user values are zero or negative
                userSum -= mFactors[i];
            } else {
                defaultSum += mFactors[i];
                ++defaultCount;
            }
        }

        // if the user request was > 100%, reject it
        if (userSum > 100.0f) {
            System.err.println("** Event weights > 100%");
            return false;
        }

        // if the user specified all of the weights, then they need to be 100%
        if (defaultCount == 0 && (userSum < 99.9f || userSum > 100.1f)) {
            System.err.println("** Event weights != 100%");
            return false;
        }

        // compute the adjustment necessary
        float defaultsTarget = (100.0f - userSum);
        float defaultsAdjustment = defaultsTarget / defaultSum;

        // fix all values, by adjusting defaults, or flipping user values back
        // to >0
        for (int i = 0; i < FACTORZ_COUNT; ++i) {
            if (mFactors[i] <= 0.0f) { // user values are zero or negative
                mFactors[i] = -mFactors[i];
            } else {
                mFactors[i] *= defaultsAdjustment;
            }
        }

        // if verbose, show factors
        if (mVerbose > 0) {
            System.out.println("// Event percentages:");
            for (int i = 0; i < FACTORZ_COUNT; ++i) {
                System.out.println("//   " + i + ": " + mFactors[i] + "%");
            }
        }

        if (!validateKeys()) {
            return false;
        }

        // finally, normalize and convert to running sum
        float sum = 0.0f;
        for (int i = 0; i < FACTORZ_COUNT; ++i) {
            sum += mFactors[i] / 100.0f;
            mFactors[i] = sum;
        }
        return true;
    }

    /**
     * See if any key exists for non-zero factors.
     */
    private boolean validateKeys() {
        return validateKeyCategory("NAV_KEYS", NAV_KEYS, mFactors[FACTOR_NAV])
                && validateKeyCategory("MAJOR_NAV_KEYS", MAJOR_NAV_KEYS, mFactors[FACTOR_MAJORNAV])
                && validateKeyCategory("SYS_KEYS", SYS_KEYS, mFactors[FACTOR_SYSOPS]);
    }

    /**
     * set the factors
     *
     * @param factors percentages for each type of event
     */
    public void setFactors(float factors[]) {
        int c = FACTORZ_COUNT;
        if (factors.length < c) {
            c = factors.length;
        }
        for (int i = 0; i < c; i++)
            mFactors[i] = factors[i];
    }

    public void setFactors(int index, float v) {
        mFactors[index] = v;
    }

    /**
     * Generates a random motion event. This method counts a down, move, and up
     * as multiple events.
     * <p>
     * TODO: Test & fix the selectors when non-zero percentages TODO: Longpress.
     * TODO: Fling. TODO: Meta state TODO: More useful than the random walk here
     * would be to pick a single random direction and distance, and divvy it up
     * into a random number of segments. (This would serve to generate fling
     * gestures, which are important).
     *
     * @param random  Random number source for positioning
     * @param gesture The gesture to perform.
     */
    private void generatePointerEvent(Random random, int gesture) {
        Display display = DisplayManagerGlobal.getInstance().getRealDisplay(Display.DEFAULT_DISPLAY);

        PointF p1 = randomPoint(random, display);
        PointF v1 = randomVector(random);

        long downAt = SystemClock.uptimeMillis();

        mQ.addLast(new MonkeyTouchEvent(MotionEvent.ACTION_DOWN).setDownTime(downAt).addPointer(0, p1.x, p1.y)
                .setIntermediateNote(false));

        // sometimes we'll move during the touch
        if (gesture == GESTURE_DRAG) {
            int count = random.nextInt(10);
            for (int i = 0; i < count; i++) {
                randomWalk(random, display, p1, v1);

                mQ.addLast(new MonkeyTouchEvent(MotionEvent.ACTION_MOVE).setDownTime(downAt).addPointer(0, p1.x, p1.y)
                        .setIntermediateNote(true));
            }
        } else if (gesture == GESTURE_PINCH_OR_ZOOM) {
            PointF p2 = randomPoint(random, display);
            PointF v2 = randomVector(random);

            randomWalk(random, display, p1, v1);
            mQ.addLast(new MonkeyTouchEvent(
                    MotionEvent.ACTION_POINTER_DOWN | (1 << MotionEvent.ACTION_POINTER_INDEX_SHIFT)).setDownTime(downAt)
                    .addPointer(0, p1.x, p1.y).addPointer(1, p2.x, p2.y).setIntermediateNote(true));

            int count = random.nextInt(10);
            for (int i = 0; i < count; i++) {
                randomWalk(random, display, p1, v1);
                randomWalk(random, display, p2, v2);

                mQ.addLast(new MonkeyTouchEvent(MotionEvent.ACTION_MOVE).setDownTime(downAt).addPointer(0, p1.x, p1.y)
                        .addPointer(1, p2.x, p2.y).setIntermediateNote(true));
            }

            randomWalk(random, display, p1, v1);
            randomWalk(random, display, p2, v2);
            mQ.addLast(
                    new MonkeyTouchEvent(MotionEvent.ACTION_POINTER_UP | (1 << MotionEvent.ACTION_POINTER_INDEX_SHIFT))
                            .setDownTime(downAt).addPointer(0, p1.x, p1.y).addPointer(1, p2.x, p2.y)
                            .setIntermediateNote(true));
        }

        randomWalk(random, display, p1, v1);
        mQ.addLast(new MonkeyTouchEvent(MotionEvent.ACTION_UP).setDownTime(downAt).addPointer(0, p1.x, p1.y)
                .setIntermediateNote(false));
    }

    private PointF randomPoint(Random random, Display display) {
        return new PointF(random.nextInt(display.getWidth()), random.nextInt(display.getHeight()));
    }

    private PointF randomVector(Random random) {
        return new PointF((random.nextFloat() - 0.5f) * 50, (random.nextFloat() - 0.5f) * 50);
    }

    private void randomWalk(Random random, Display display, PointF point, PointF vector) {
        point.x = (float) Math.max(Math.min(point.x + random.nextFloat() * vector.x, display.getWidth()), 0);
        point.y = (float) Math.max(Math.min(point.y + random.nextFloat() * vector.y, display.getHeight()), 0);
    }

    /**
     * Generates a random trackball event. This consists of a sequence of small
     * moves, followed by an optional single click.
     * <p>
     * TODO: Longpress. TODO: Meta state TODO: Parameterize the % clicked TODO:
     * More useful than the random walk here would be to pick a single random
     * direction and distance, and divvy it up into a random number of segments.
     * (This would serve to generate fling gestures, which are important).
     *
     * @param random Random number source for positioning
     */
    private void generateTrackballEvent(Random random) {
        for (int i = 0; i < 10; ++i) {
            // generate a small random step
            int dX = random.nextInt(10) - 5;
            int dY = random.nextInt(10) - 5;

            mQ.addLast(
                    new MonkeyTrackballEvent(MotionEvent.ACTION_MOVE).addPointer(0, dX, dY).setIntermediateNote(i > 0));
        }

        // 10% of trackball moves end with a click
        if (0 == random.nextInt(10)) {
            long downAt = SystemClock.uptimeMillis();

            mQ.addLast(new MonkeyTrackballEvent(MotionEvent.ACTION_DOWN).setDownTime(downAt).addPointer(0, 0, 0)
                    .setIntermediateNote(true));

            mQ.addLast(new MonkeyTrackballEvent(MotionEvent.ACTION_UP).setDownTime(downAt).addPointer(0, 0, 0)
                    .setIntermediateNote(false));
        }
    }

    /**
     * Generates a random screen rotation event.
     *
     * @param random Random number source for rotation degree.
     */
    private void generateRotationEvent(Random random) {
        addEvent(new MonkeyRotationEvent(SCREEN_ROTATION_DEGREES[random.nextInt(SCREEN_ROTATION_DEGREES.length)],
                random.nextBoolean()));
    }

    @TargetApi(Build.VERSION_CODES.O)
    private void generateRandomElemAction(AccessibilityNodeInfo node) {
        // dump string list to call generateDesribedActions func
        List<String> actions = new ArrayList<>();
        // only use global var actionList to get all ui element action
        generateDesribedActions(node,actions);
    }

    private void generateEvents(AccessibilityNodeInfo rootNode) {
        if(dealWithSystemUI(rootNode))
            return;

        // generate Action based on ui element
        generateRandomElemAction(rootNode);
        // add system events
        actionList.add(new LLMAction(ActionType.BACK, packageName, currentactivity,null,"back key"));
        actionList.add(new LLMAction(ActionType.ROTATE_SCREEN, packageName, currentactivity,null,"rotate screen"));
        actionList.add(new LLMAction(ActionType.ACTIVATE, packageName, currentactivity,null, "activate app"));
        actionList.add(new LLMAction(ActionType.START,packageName, currentactivity,null, "start activity"));

        // radnomly pick a action from current ui action list
        int actionId = mRandom.nextInt(actionList.size());
        LLMAction randomAction = actionList.get(actionId);

        // improve click event probability
        if (mRandom.nextDouble() < 0.6){
            randomAction.setType(ActionType.CLICK);
        }

        // generate corresponding monkey event
        generateEventsForAction(randomAction);

        // reset actionList for new ui screen
        actionList.clear();

    }


    private void generateEvents() {
        AccessibilityNodeInfo rootNode = getRootNode();
        if(dealWithSystemUI(rootNode))
            return;

        // generate Action based on ui element
        generateRandomElemAction(rootNode);
        // add system events
        actionList.add(new LLMAction(ActionType.BACK, packageName, currentactivity,null,"back key"));
        actionList.add(new LLMAction(ActionType.ROTATE_SCREEN, packageName, currentactivity,null,"rotate screen"));
        actionList.add(new LLMAction(ActionType.ACTIVATE, packageName, currentactivity,null, "activate app"));
        actionList.add(new LLMAction(ActionType.START,packageName, currentactivity,null, "start activity"));

        // radnomly pick a action from current ui action list
        int actionId = mRandom.nextInt(actionList.size());
        LLMAction randomAction = actionList.get(actionId);

        // improve click event probability
        if (mRandom.nextDouble() < 0.6){
            randomAction.setType(ActionType.CLICK);
        }

        // generate corresponding monkey event
        generateEventsForAction(randomAction);

        // reset actionList for new ui screen
        actionList.clear();

    }

    /**
     * generate a random event based on mFactor
     */
//    private void generateEvents() {
//        float cls = mRandom.nextFloat();
//        int lastKey = 0;
//
//        if (cls < mFactors[FACTOR_TOUCH]) {
//            generatePointerEvent(mRandom, GESTURE_TAP);
//            return;
//        } else if (cls < mFactors[FACTOR_MOTION]) {
//            generatePointerEvent(mRandom, GESTURE_DRAG);
//            return;
//        } else if (cls < mFactors[FACTOR_PINCHZOOM]) {
//            generatePointerEvent(mRandom, GESTURE_PINCH_OR_ZOOM);
//            return;
//        } else if (cls < mFactors[FACTOR_TRACKBALL]) {
//            generateTrackballEvent(mRandom);
//            return;
//        } else if (cls < mFactors[FACTOR_ROTATION]) {
//            generateRotationEvent(mRandom);
//            return;
//        } else if (cls < mFactors[FACTOR_PERMISSION]) {
//            mQ.add(mPermissionUtil.generateRandomPermissionEvent(mRandom));
//            return;
//        }
//
//        // The remaining {event categories are injected as key events
//        for (; ; ) {
//            if (cls < mFactors[FACTOR_NAV]) {
//                lastKey = NAV_KEYS[mRandom.nextInt(NAV_KEYS.length)];
//            } else if (cls < mFactors[FACTOR_MAJORNAV]) {
//                lastKey = MAJOR_NAV_KEYS[mRandom.nextInt(MAJOR_NAV_KEYS.length)];
//            } else if (cls < mFactors[FACTOR_SYSOPS]) {
//                lastKey = SYS_KEYS[mRandom.nextInt(SYS_KEYS.length)];
//            } else if (cls < mFactors[FACTOR_APPSWITCH]) {
//                MonkeyActivityEvent e = new MonkeyActivityEvent(mMainApps.get(mRandom.nextInt(mMainApps.size())));
//                mQ.addLast(e);
//                return;
//            } else if (cls < mFactors[FACTOR_FLIP]) {
//                MonkeyFlipEvent e = new MonkeyFlipEvent(mKeyboardOpen);
//                mKeyboardOpen = !mKeyboardOpen;
//                mQ.addLast(e);
//                return;
//            } else {
//                lastKey = 1 + mRandom.nextInt(KeyEvent.getMaxKeyCode() - 1);
//            }
//
//            if (lastKey != KeyEvent.KEYCODE_POWER && lastKey != KeyEvent.KEYCODE_ENDCALL
//                    && lastKey != KeyEvent.KEYCODE_SLEEP && PHYSICAL_KEY_EXISTS[lastKey]) {
//                break;
//            }
//        }
//
//        MonkeyKeyEvent e = new MonkeyKeyEvent(KeyEvent.ACTION_DOWN, lastKey);
//        mQ.addLast(e);
//
//        e = new MonkeyKeyEvent(KeyEvent.ACTION_UP, lastKey);
//        mQ.addLast(e);
//    }

    public boolean validate() {
        boolean ret = true;
        // only populate & dump permissions if enabled
        if (mFactors[FACTOR_PERMISSION] != 0.0f) {
            ret &= mPermissionUtil.populatePermissionsMapping();
            if (ret && mVerbose >= 2) {
                mPermissionUtil.dump();
            }
        }
        return ret & adjustEventFactors();
    }

    public void setVerbose(int verbose) {
        mVerbose = verbose;
    }

    /**
     * generate an activity event
     */
    public void generateActivity() {
        MonkeyActivityEvent e = new MonkeyActivityEvent(mMainApps.get(mRandom.nextInt(mMainApps.size())));
        addEvent(e);
    }

    public File takeScreenshotForEventSource(String eventSource){
        long timeMillis = System.currentTimeMillis();
        File screenshotFile = null;
        if (takeScreenshotForEveryStep) {
            checkOutputDir();
            screenshotFile = new File(checkOutputDir(), String.format(stringFormatLocale,
                    "step-%d-%s-%s.png",timeStep, eventSource, timeMillis));
            Logger.infoFormat("Saving screen shot to %s at step %d ",
                    screenshotFile, timeStep);
            takeScreenshot(screenshotFile);
        }
        return screenshotFile;
    }

    private void generateReuseEvent() {
        Tarpit currentTarpit = tarpitDetector.getTargetTarpit();
        List<MonkeyEvent> reuseEvent = currentTarpit.getTarpitActions();
        if (reuseEvent.isEmpty()){
            // sometimes due to network problem , we cannot get LLM event successfully
            // thus, we cannot get reuse event to put in mQ, this cause mQ becoming empty
            // to avoid mQ empty we try generating LLM event
            Logger.warningPrintln("Reuse event is null，return to generate llm event!");
            generateLLMEvents();
            isLLMAction = true;
            return;
        }
        // randomly pick a reuse event to execute
        int eid = mRandom.nextInt(reuseEvent.size());
        mQ.addLast(reuseEvent.get(eid));
    }

    private File getCurrentScreen(){
        File currentScreen;
        Logger.println("last screen: "+lastScreen.getPath());
        timeStep++;// for screenshot count

        if(isLLMAction){
            currentScreen = takeScreenshotForEventSource("random-llm");
        } else{
            currentScreen = takeScreenshotForEventSource("random");
        }

        if (currentScreen != null) {
            Logger.println("get current screen successful!");
        } else {
            Logger.errorPrintln("fail to get current screen");
        }
        return currentScreen;
    }
    /**
     * if the queue is empty, we generate events first
     *
     * @return the first event in the queue
     */
    public MonkeyEvent getNextEvent(){
        // ensure aut is on the screen
        checkAppActivity();
        if (mQ.isEmpty()) {
            try{
                File currentScreen = getCurrentScreen();
                // detect tarpit
                if (tarpitDetector.detectedUiTarpit(currentScreen, lastScreen)) {
                    // if visited a known tarpit then probablity resue
                    if ( !tarpitDetector.isNewTarpit(currentScreen) &&
                            mRandom.nextDouble() < 0.5) {
                        Logger.println("// Detected UI Tarpit, strating generate Reuse event");
                        generateReuseEvent();
                    }else{
                        Logger.println("// Detected UI Tarpit, strating generate LLM event");
                        generateLLMEvents();
                        isLLMAction = true;
                    }
                } else {// no tarpit
                    Logger.println("// No Tarpit");
                    actionList.clear();
                    llmActionHistory.clear();
                    try {
                        generateEvents();
                    } catch (RuntimeException e) {
                        Logger.errorPrintln(e.getMessage());
                        e.printStackTrace();
                        clearEvent();
                        return null;
                    }
                    isLLMAction = false;
                }
                lastScreen = currentScreen;
            }catch (RuntimeException e){
                Logger.errorPrintln(e.getMessage());
                e.printStackTrace();
                clearEvent();
                return null;
            }
        }
        // 二次防御性检查（确保mQ不为空）
        if (mQ.isEmpty()) {
            Logger.errorPrintln("严重错误：事件队列仍为空，生成紧急返回事件");
            MonkeyKeyEvent e = new MonkeyKeyEvent(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_BACK);
            mQ.addLast(e);
            e = new MonkeyKeyEvent(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_BACK);
            mQ.addLast(e);
        }
        mEventCount++;
        Logger.println("event counts:"+mEventCount);
        MonkeyEvent e = mQ.getFirst();
        mQ.removeFirst();
        return e;
    }


    protected void checkAppActivity() {
        ComponentName cn = AndroidDevice.getTopActivityComponentName();
        if (cn == null) {
            Logger.println(": debug, gettask api error");
            clearEvent();
            startRandomMainApp();
            return;
        }
        String className = cn.getClassName();
        String pkg = cn.getPackageName();
        boolean allow = MonkeyUtils.getPackageFilter().checkEnteringPackage(pkg);

        if (allow) {
            if (!this.currentactivity.equals(className)) {
                this.currentactivity = className;
                activityHistory.add(this.currentactivity);
                Logger.println(": debug, currentactivity is " + this.currentactivity);
            }
            return;
        }

        Logger.println("// the top activity is " + className + ", not testing app, need inject restart app");
        clearEvent();
        startRandomMainApp();
        return;
    }

    private final void clearEvent() {
        while (!mQ.isEmpty()) {
            MonkeyEvent e = mQ.removeFirst();
        }
    }

    private final void addEvent(MonkeyEvent event) {
        mQ.addLast(event);
        event.setEventId(mEventId++);
    }


    protected void startRandomMainApp() {
        generateActivityEvents(randomlyPickMainApp(), false);
    }

    protected void generateActivityEvents(ComponentName app, boolean clearPackage) {
        MonkeyActivityEvent e = new MonkeyActivityEvent(app);
        addEvent(e);
        generateThrottleEvent(startAfterNSecondsofsleep); // waiting for the loading of apps

    }


    protected void generateThrottleEvent(long base) {
        long throttle = base;
        if (mRandomizeThrottle && (mThrottle > 0)) {
            throttle = mRandom.nextLong();
            if (throttle < 0) {
                throttle = -throttle;
            }
            throttle %= base;
            ++throttle;
        }
        if (throttle < 0) {
            throttle = -throttle;
        }
        addEvent(new MonkeyThrottleEvent(throttle));
    }

    private void getTotalAcitivities() {
        try {
            for (String p : MonkeyUtils.getPackageFilter().getmValidPackages()) {
                PackageInfo packageInfo = AndroidDevice.packageManager.getPackageInfo(p, PackageManager.GET_ACTIVITIES);
                if (packageInfo != null) {
                    if (packageInfo.packageName.equals("com.android.packageinstaller"))
                        continue;
                    if (packageInfo.activities != null) {
                        for (ActivityInfo activityInfo : packageInfo.activities) {
                            mTotalActivities.add(activityInfo.name);
                        }
                    }
                }
            }

        } catch (Exception e) {
        }
    }

    public HashSet<String> getmTotalAcitivities() {
        return mTotalActivities;
    }


    private void printCoverage() {
        HashSet<String> set = getmTotalAcitivities();

        Logger.println("Total app activities:");
        int i = 0;
        for (String activity : set) {
            i++;
            Logger.println(String.format("%4d %s", i, activity));
        }

        String[] testedActivities = this.activityHistory.toArray(new String[0]);
        Arrays.sort(testedActivities);
        int j = 0;
        String activity = "";
        Logger.println("Explored app activities:");
        for (i = 0; i < testedActivities.length; i++) {
            activity = testedActivities[i];
            if (set.contains(activity)) {
                Logger.println(String.format("%4d %s", j + 1, activity));
                j++;
            }
        }

        float f = 0;
        int s = set.size();
        if (s > 0) {
            f = 1.0f * j / s * 100;
            Logger.println("Activity of Coverage: " + f + "%");
        }

        String[] totalActivities = set.toArray(new String[0]);
        Arrays.sort(totalActivities);


        Utils.activityStatistics(mOutputDirectory, testedActivities, totalActivities, new ArrayList<Map<String, String>>(), f, new HashMap<String, Integer>());

    }

    public void setAttribute(String packageName, String appVersion, String intentAction, String intentData, String quickActivity) {
        this.packageName = packageName;
        this.appVersion = (!appVersion.equals("")) ? appVersion : this.getAppVersionCode();
        this.intentAction = intentAction;
        this.intentData = intentData;
        this.quickActivity = quickActivity;
    }

    public void tearDown() {
        this.disconnect();
        tarpitDetector.printUiTarpits();
        this.printCoverage();
        for (ImageWriterQueue writer : mImageWriters) {
            writer.tearDown();
        }
    }

    public File getTempDir(){
        return tempPath;
    }

    public File checkTempDir(){
        File dir = getTempDir();
        if (!dir.exists()) {
            dir.mkdirs();
        }
        return dir;
    }

    public File getOutputDir() {
        return mOutputDirectory;
    }

    private File checkOutputDir() {
        File dir = getOutputDir();
        if (!dir.exists()) {
            dir.mkdirs();
        }
        return dir;
    }

    private void takeScreenshot(File screenshotFile) {
        Bitmap map = mUiAutomation.takeScreenshot();
        nextImageWriter().add(map, screenshotFile);
    }

    private ImageWriterQueue nextImageWriter() {
        return mImageWriters[mRandom.nextInt(mImageWriters.length)];
    }

    /**
     * Connect to AccessibilityService
     */
    public void connect() {
        if (mHandlerThread.isAlive()) {
            throw new IllegalStateException("Already connected!");
        }
        mHandlerThread.start();
        mUiAutomation = new UiAutomation(mHandlerThread.getLooper(), new UiAutomationConnection());
        mUiAutomation.connect();

        AccessibilityServiceInfo info = mUiAutomation.getServiceInfo();
        // Compress this node
        info.flags &= ~AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS;

        mUiAutomation.setServiceInfo(info);
    }

    /**
     * Disconnect to AccessibilityService
     */
    public void disconnect() {
        if (!mHandlerThread.isAlive()) {
            throw new IllegalStateException("Already disconnected!");
        }
        if (mUiAutomation != null) {
            mUiAutomation.disconnect();
        }
        mHandlerThread.quit();
    }

    public File getLastScreen(){
        return lastScreen;
    }

    private File createDirectory(String string) {
        File file = new File(string);
        if (file.exists()) {
            int count = 1;
            File newFile = new File(file.getAbsolutePath() + "." + count);
            while (newFile.exists()) {
                count++;
                newFile = new File(file.getAbsolutePath() + "." + count);
            }
            Logger.format("Rename %s to %s", file, newFile);
            if(file.renameTo(newFile)){
                Logger.format("Rename %s to %s succeed", file, newFile);
            }else{
                Logger.format("Rename %s to %s failed", file, newFile);
            }
        }
        if (file.exists()) {
            throw new IllegalStateException("Cannot rename file " + file);
        }
        if (!file.mkdirs()) {
            throw new IllegalStateException("Cannot mkdirs at file " + file);
        }
        return file;
    }

    private String getAppVersionCode() {
        try {
            for (String p : MonkeyUtils.getPackageFilter().getmValidPackages()) {
                PackageInfo packageInfo = AndroidDevice.packageManager.getPackageInfo(p, PackageManager.GET_ACTIVITIES);
                if (packageInfo != null) {
                    if (packageInfo.packageName.equals(this.packageName)) {
                        return packageInfo.versionName;
                    }
                }
            }

        } catch (Exception e) {
        }
        return "";
    }


    public ComponentName randomlyPickMainApp() {
        int total = mMainApps.size();
        int index = mRandom.nextInt(total);
        return mMainApps.get(index);
    }



    void sleep(long time) {
        try {
            Thread.sleep(time);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    public void generateLLMEvents() {
        AccessibilityNodeInfo rootNode = getRootNode();
        if(dealWithSystemUI(rootNode))
            return;

        LLMAction llmAction = getLLMEvent(rootNode);
        if (llmAction == null){
            Logger.warningPrintln("cannot get LLM action! go back!");
            MonkeyKeyEvent e = new MonkeyKeyEvent(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_BACK);
            mQ.addLast(e);
            e = new MonkeyKeyEvent(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_BACK);
            mQ.addLast(e);
            return;
        }
//        ActionType type = llmAction.getType();
//        Logger.println("LLM action type: "+ type.toString());
//        llmAction.setThrottle(10);
        generateEventsForAction(llmAction);

        Tarpit currentTarpit = tarpitDetector.getTargetTarpit();
        tarpitDetector.addTarpitActions(currentTarpit, llmAction);

        Logger.println("End generate LLM event");

    }

    private AccessibilityNodeInfo getRootNode(){
        ComponentName topActivityName = null;
        AccessibilityNodeInfo rootNode = null;
        int repeat = refectchInfoCount;

        // try to get AccessibilityNodeInfo quickly for several times.
        while (repeat-- > 0) {
            topActivityName = AndroidDevice.getTopActivityComponentName();
            rootNode = getRootInActiveWindow();
            // this two operations may not be the same
            if (rootNode == null || topActivityName == null) {
                sleep(refectchInfoWaitingInterval);
                continue;
            }
            Logger.println("// Event id: " + mEventId);
            break;
        }

        // If node is null, try to get AccessibilityNodeInfo slow for only once
        if (rootNode == null) {
            topActivityName = AndroidDevice.getTopActivityComponentName();
            rootNode = getRootInActiveWindowSlow();
            if (rootNode != null) {
                Logger.println("// Event id: " + mEventId);
            }
        }
        return rootNode;
    }


    // 初始化预编译正则表达式（提升性能）
    private static final Pattern NUMBER_PATTERN = Pattern.compile("-?\\d+"); // 支持负数（如-1）

    @TargetApi(Build.VERSION_CODES.O)
    private LLMAction getLLMEvent(AccessibilityNodeInfo rootNode) {

        String taskPrompt = task + String.format(" Currently, the App is stuck on the %s page, unable to explore more features. You task is to select an action based on the current GUI Information to perform next and help the app escape the UI tarpit.", currentactivity);
        String visitedPagePrompt = "I have already visited the following activities: \n" + String.join("\n", activityHistory);
        String historyPrompt = "I have already tried the following steps with action id in parentheses which should not be selected anymore: \n " + String.join(";\n ", llmActionHistory);
        String statePrompt = getStatePrompt(rootNode); // Assume this returns a string representation
        String question = "Which action should I choose next? Just return the action id and nothing else.\nIf no more action is needed, return -1.";
        String prompt = String.join("\n", taskPrompt ,statePrompt , visitedPagePrompt, historyPrompt ,question);
        Logger.println(prompt);

        String response = null;
        try {
            response = queryLLM(prompt);
        } catch (Exception e) {
            e.printStackTrace();
        }

        Logger.println("Response: " + response);

        try {
            Matcher matcher = NUMBER_PATTERN.matcher(response);
            if (!matcher.find()) {
                Logger.warningPrintln("No valid action ID found in response: " + response);
                return null;
            }

            int idx = Integer.parseInt(matcher.group());
            if (idx == -1) {
                Logger.println("LLM suggested termination (-1)");
                return null;
            }
            if (idx < 0 || idx >= actionList.size()) {
                Logger.errorPrintln("Invalid action index: " + idx
                        + ", valid range: 0-" + (actionList.size()-1));
                return null;
            }

            LLMAction selectedAction = actionList.get(idx);
            if (selectedAction.isEditText()) {
                processTextInput(selectedAction, prompt);
            }
            llmActionHistory.add(selectedAction.toString());

            return selectedAction;
        } catch (IllegalStateException e) {
            Logger.errorPrintln("[ERROR] Regex matching failed: " + e.getMessage());
        } catch (NumberFormatException e) {
            Logger.errorPrintln("[ERROR] Invalid number format: " + e.getMessage());
        } catch (IndexOutOfBoundsException e) {
            Logger.errorPrintln("[ERROR] Invalid action index: " + e.getMessage()
                    + ", valid range: 0-" + (actionList.size()-1));
        } catch (Exception e) {
            Logger.errorPrintln("[ERROR] Unexpected error: " + e.getClass().getSimpleName()
                    + " - " + e.getMessage());
        }
        return null;
    }

    private String queryLLM(String prompt) throws Exception {
        OkHttpClient client = new OkHttpClient();

        JSONObject json = new JSONObject();
        json.put("messages", new JSONArray().put(new JSONObject().put("role", "user").put("content", prompt)));
        json.put("model", "gpt-3.5-turbo");

        RequestBody body = RequestBody.create(MediaType.parse("application/json"), json.toString());
        Request request = new Request.Builder()
                .url(GPT_URL)
                .addHeader("Authorization", "Bearer " + GPT_KEY)
                .post(body)
                .build();

        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) throw new IOException("Unexpected code " + response);
            String responseBody = response.body().string();
            JSONObject responseJson = new JSONObject(responseBody);
            return responseJson.getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content");
        }
    }

    /**
     * handle llm text input
     */
    private void processTextInput(LLMAction action, String contextPrompt) {
        try {
            String question = String.format("What text should I enter to the %s? Just return the text and nothing else.",
                    action.getViewDesc());

            String textResponse = queryLLM(contextPrompt + "\n" + question);
            Logger.infoPrintln("Text Input Response: " + textResponse);

            // 清理响应文本
            String cleanedText = textResponse.replace("\"", "")
                    .replace("\n", " ")
                    .trim();

            // 限制输入长度（可配置化）
            int maxLength = 30;
            if (cleanedText.length() > maxLength) {
                cleanedText = cleanedText.substring(0, maxLength - 3) + "...";
                Logger.warningPrintln("Truncated input text to " + maxLength + " chars");
            }

            action.setInputText(cleanedText);
            Logger.infoPrintln("Final Input Text: " + action.getInputText());

        } catch (Exception e) {
            Logger.errorPrintln("Failed to process text input: " + e.getMessage());
            action.setInputText("hello, world!");  // 设置默认值避免NPE
        }
    }

    /**
     *
     * Get a text description of current state
     *
     * **/
    public String getStatePrompt(AccessibilityNodeInfo rootNode) {
        //initial
        actionList.clear();
        actionIdCounter = 0;

        StringBuilder statePrompt = new StringBuilder();
        statePrompt.append("The current state has the following UI views and corresponding actions, with action id in parentheses:\n");

        List<String> actions = new ArrayList<>();

        if (rootNode != null) {
            generateDesribedActions(rootNode, actions);
        }

        for (String action : actions) {
            statePrompt.append("- ").append(action).append("\n");
        }

        String gobackAction = "- a key to go back (" + actionIdCounter + ")";
        actionList.add(new LLMAction(ActionType.BACK, packageName, currentactivity,new Rect(0,0,0,0),"back key"));
        statePrompt.append(gobackAction).append("\n");

        return statePrompt.toString();
    }

    private void generateSchemaEvents() {
        //todo
    }

    // 校验 Rect 是否合法
    private boolean isRectValid(Rect rect) {
        return rect.left <= rect.right && rect.top <= rect.bottom;
    }

    @TargetApi(Build.VERSION_CODES.O)
    private void generateDesribedActions(AccessibilityNodeInfo node, List<String> actions) {
        if (node == null || !node.isVisibleToUser()) return ;
        // 获取控件的边界
        Rect bounds = new Rect();
        node.getBoundsInScreen(bounds);
        if (!isRectValid(bounds)) {
            Logger.warningPrintln("skip invalid bounds view: " + bounds.toShortString());
            return;
        }
//        int left = bounds.left;
//        int top = bounds.top;
//        int width = bounds.width();
//        int height = bounds.height();
//        Logger.println("Bounds" + "Left: " + left + ", Top: " + top + ", Width: " + width + ", Height: " + height);

//        // 计算中心坐标
//        float centerX = bounds.centerX();
//        float centerY = bounds.centerY();

        StringBuilder viewDesc = new StringBuilder();
        String nodeText = node.getText() != null ? node.getText().toString() : "";
        String nodeContentDesc = node.getContentDescription() != null ? node.getContentDescription().toString() : "";
        if (node.isChecked() || node.isSelected()){
            viewDesc.append("a checked view ");
        }else{
            viewDesc.append("a view ");
        }

        if(!nodeContentDesc.equals("")){
            nodeContentDesc = nodeContentDesc.replace("\n", "  ");
            if (nodeContentDesc.length() > 20) {
                nodeContentDesc = nodeContentDesc.substring(0, 20) + "...";
            }
            viewDesc.append(String.format(" \"%s\"",nodeContentDesc));
        }

        if (!nodeText.equals("")){
            nodeText = nodeText.replace("\n", "  ");
            if (nodeText.length() > 20) {
                nodeText = nodeText.substring(0, 20) + "...";
            }
            viewDesc.append(String.format(" with text \"%s\"", nodeText));
        }

        // 检查属性并添加动作
        List<String> actionDescList = new ArrayList<>();
        if (node.isClickable() || node.isCheckable()) {
            actionDescList.add("can click (" + actionIdCounter++ + ")");
            actionDescList.add("can longclick (" + actionIdCounter++ + ")");
            actionList.add(new LLMAction(ActionType.CLICK, packageName, currentactivity, bounds, viewDesc.toString()));
            actionList.add(new LLMAction(ActionType.LONG_CLICK, packageName, currentactivity, bounds, viewDesc.toString()));
        }
        if (node.isEditable()) {
            actionDescList.add("can edit (" + actionIdCounter++ + ")");
            actionList.add(new LLMAction(ActionType.CLICK, packageName, currentactivity, bounds, viewDesc.toString()).setInputText(RandomHelper.nextString(20)).setEditText(true).setUseAdbInput(true));
        }
        if (node.isScrollable()) {
            actionDescList.add("can scroll up (" + actionIdCounter++ + ")");
            actionDescList.add("can scroll down (" + actionIdCounter++ + ")");
            actionDescList.add("can scroll left (" + actionIdCounter++ + ")");
            actionDescList.add("can scroll right (" + actionIdCounter++ + ")");
            actionList.add(new LLMAction(ActionType.SCROLL_BOTTOM_UP, packageName, currentactivity, bounds, viewDesc.toString()));
            actionList.add(new LLMAction(ActionType.SCROLL_TOP_DOWN, packageName, currentactivity, bounds, viewDesc.toString()));
            actionList.add(new LLMAction(ActionType.SCROLL_RIGHT_LEFT, packageName, currentactivity, bounds, viewDesc.toString()));
            actionList.add(new LLMAction(ActionType.SCROLL_LEFT_RIGHT, packageName, currentactivity, bounds, viewDesc.toString()));
        }

        // 如果有动作，将其添加到视图信息中
        if (!actionDescList.isEmpty()) {
            viewDesc.append(" that ").append(String.join(", ", actionDescList));
            actions.add(viewDesc.toString());
        }

        // 递归获取子节点
        for (int i = 0; i < node.getChildCount(); i++) {
            generateDesribedActions(node.getChild(i), actions);
        }

    }

    private void generateEventsForAction(Action action) {
        generateEventsForActionInternal(action);
//        long throttle = action.getThrottle();
//        generateThrottleEvent(throttle);
    }


    private void generateEventsForActionInternal(Action action) {
        ActionType actionType = action.getType();
        Logger.println("action type: " + actionType.toString());
        switch (actionType) {
            case BACK:
                generateKeyEvent(KeyEvent.KEYCODE_BACK);
                break;
            case ROTATE_SCREEN:
                generateRotationEvent(mRandom);
                break;
            case ACTIVATE:
                generateActivateEvent();
                break;
            case START:
                generateActivityEvents(randomlyPickMainApp(), false);
                break;
            case CLICK:
                generateClickEventAt(((LLMAction) action).getBoundingBox(), CLICK_WAIT_TIME);
                doInput((LLMAction) action);
                break;
            case LONG_CLICK:
                long waitTime = ((LLMAction) action).getWaitTime();
                if (waitTime == 0) {
                    waitTime = LONG_CLICK_WAIT_TIME;
                }
                generateClickEventAt(((LLMAction) action).getBoundingBox(), waitTime);
                break;
            case SCROLL_BOTTOM_UP:
            case SCROLL_TOP_DOWN:
            case SCROLL_LEFT_RIGHT:
            case SCROLL_RIGHT_LEFT:
                generateScrollEventAt(((LLMAction) action).getBoundingBox(), action.getType());
                break;
            default:
                throw new RuntimeException("Should not reach here");
        }
    }

    protected void generateKeyEvent(int key) {
        MonkeyKeyEvent e = new MonkeyKeyEvent(KeyEvent.ACTION_DOWN, key);
//        e.setEventSource("LLM");
        addEvent(e);

        e = new MonkeyKeyEvent(KeyEvent.ACTION_UP, key);
//        e.setEventSource("LLM");
        addEvent(e);
    }

    private void doInput(LLMAction action) {
        String inputText = action.getInputText();
        boolean useAdbInput = action.isUseAdbInput();
        if (inputText != null && !inputText.equals("")) {
            Logger.println("Input text is " + inputText);
            if (action.isClearText())
                generateClearEvent(action.getBoundingBox());

            if (action.isRawInput()) {
                if (!AndroidDevice.sendText(inputText))
                    attemptToSendTextByKeyEvents(inputText);
                return;
            }

            Logger.println("MonkeyCommandEvent added " + inputText);
            addEvent(new MonkeyCommandEvent("input text " + inputText));

        } else {
            if (lastInputTimestamp == timestamp) {
                Logger.warningPrintln("checkVirtualKeyboard: Input only once.");
                return;
            } else {
                lastInputTimestamp = timestamp;
            }
            if (action.isEditText() || AndroidDevice.isVirtualKeyboardOpened()) {
                generateKeyEvent(KeyEvent.KEYCODE_ESCAPE);
            }
        }
    }

    protected void generateClickEventAt(Rect nodeRect, long waitTime) {
        generateClickEventAt(nodeRect, waitTime, useRandomClick);
    }

    protected void generateClickEventAt(Rect nodeRect, long waitTime, boolean useRandomClick) {
        Rect bounds = nodeRect;
        if (bounds == null) {
            Logger.warningPrintln("Error to fetch bounds.");
            bounds = AndroidDevice.getDisplayBounds();
        }

        PointF p1;
        if (useRandomClick) {
            int width = bounds.width() > 0 ? getRandom().nextInt(bounds.width()) : 0;
            int height = bounds.height() > 0 ? getRandom().nextInt(bounds.height()) : 0;
            p1 = new PointF(bounds.left + width, bounds.top + height);
        } else
            p1 = new PointF(bounds.left + bounds.width()/2.0f, bounds.top + bounds.height()/2.0f);
        if (!bounds.contains((int) p1.x, (int) p1.y)) {
            Logger.warningFormat("Invalid bounds: %s", bounds);
            return;
        }
//        p1 = shieldBlackRect(p1);

        long downAt = SystemClock.uptimeMillis();

        addEvent(new MonkeyTouchEvent(MotionEvent.ACTION_DOWN).setDownTime(downAt).addPointer(0, p1.x, p1.y)
                .setIntermediateNote(false));

        if (waitTime > 0) {
            MonkeyWaitEvent we = new MonkeyWaitEvent(waitTime);
            addEvent(we);
        }

        addEvent(new MonkeyTouchEvent(MotionEvent.ACTION_UP).setDownTime(downAt).addPointer(0, p1.x, p1.y)
                .setIntermediateNote(false));
    }

    /**
     * In mathematics, linear interpolation is a method of curve fitting using linear polynomials
     * to construct new data points within the range of a discrete set of known data points.
     * @param a
     * @param b
     * @param alpha
     * @return
     */
    private static float lerp(float a, float b, float alpha) {
        return (b - a) * alpha + a;
    }

    protected void generateActivateEvent() { // duplicated with custmozie
        Logger.infoPrintln("generate app switch events.");
        generateAppSwitchEvent();
    }

    private void generateAppSwitchEvent() {
        generateKeyEvent(KeyEvent.KEYCODE_APP_SWITCH);
        generateThrottleEvent(500);
        if (RandomHelper.nextBoolean()) {
            Logger.println("press HOME after app switch");
            generateKeyEvent(KeyEvent.KEYCODE_HOME);
        } else {
            Logger.println("press BACK after app switch");
            generateKeyEvent(KeyEvent.KEYCODE_BACK);
        }
        generateThrottleEvent(mThrottle);
    }

    private void generateScrollEventAt(Rect nodeRect, ActionType type) {
        Rect displayBounds = AndroidDevice.getDisplayBounds();
        if (nodeRect == null) {
            nodeRect = AndroidDevice.getDisplayBounds();
        }

        PointF start = new PointF(nodeRect.exactCenterX(), nodeRect.exactCenterY());
        PointF end;

        switch (type) {
            case SCROLL_BOTTOM_UP:
                int top = getStatusBarHeight();
                if (top < displayBounds.top) {
                    top = displayBounds.top;
                }
                end = new PointF(start.x, top); // top is inclusive
                break;
            case SCROLL_TOP_DOWN:
                end = new PointF(start.x, displayBounds.bottom - 1); // bottom is
                // exclusive
                break;
            case SCROLL_LEFT_RIGHT:
                end = new PointF(displayBounds.right - 1, start.y); // right is
                // exclusive
                break;
            case SCROLL_RIGHT_LEFT:
                end = new PointF(displayBounds.left, start.y); // left is inclusive
                break;
            default:
                throw new RuntimeException("Should not reach here");
        }

        long downAt = SystemClock.uptimeMillis();


        addEvent(new MonkeyTouchEvent(MotionEvent.ACTION_DOWN).setDownTime(downAt).addPointer(0, start.x, start.y)
                .setIntermediateNote(false).setType(1));

        int steps = 10;
        long waitTime = swipeDuration / steps;
        for (int i = 0; i < steps; i++) {
            float alpha = i / (float) steps;
            addEvent(new MonkeyTouchEvent(MotionEvent.ACTION_MOVE).setDownTime(downAt)
                    .addPointer(0, lerp(start.x, end.x, alpha), lerp(start.y, end.y, alpha)).setIntermediateNote(true).setType(1));
            addEvent(new MonkeyWaitEvent(waitTime));
        }

        addEvent(new MonkeyTouchEvent(MotionEvent.ACTION_UP).setDownTime(downAt).addPointer(0, end.x, end.y)
                .setIntermediateNote(false).setType(1));
    }

    public AccessibilityNodeInfo getRootInActiveWindow() {
        return mUiAutomation.getRootInActiveWindow();
    }

    public boolean dealWithSystemUI(AccessibilityNodeInfo info)
    {
        if(info == null || info.getPackageName() == null)
        {
            Logger.println("get null accessibility node");
            return false;
        }
        String packageName = info.getPackageName().toString();
        if(packageName.equals("com.android.systemui")) {

            Logger.println("get notification window or other system windows");
            Rect bounds = AndroidDevice.getDisplayBounds();
            // press home
            generateKeyEvent(KeyEvent.KEYCODE_HOME);
            //scroll up
            generateScrollEventAt(bounds, SCROLL_BOTTOM_UP);
            // launch app
            generateActivityEvents(randomlyPickMainApp(), false);
            generateThrottleEvent(1000);
            return true;
        }
        return false;
    }

    public AccessibilityNodeInfo getRootInActiveWindowSlow() {
        try {
            mUiAutomation.waitForIdle(1000, 1000 * 10);
        } catch (TimeoutException e) {
            //e.printStackTrace();
        }
        return mUiAutomation.getRootInActiveWindow();
    }


    public Random getRandom() {
        return mRandom;
    }

    private void generateClearEvent(Rect bounds) {
        generateClickEventAt(bounds, LONG_CLICK_WAIT_TIME);
        generateKeyEvent(KeyEvent.KEYCODE_DEL);
        generateClickEventAt(bounds, CLICK_WAIT_TIME);
    }

    public Bitmap captureBitmap() {
        return mUiAutomation.takeScreenshot();
    }

    private void attemptToSendTextByKeyEvents(String inputText) {
        char[] szRes = inputText.toCharArray(); // Convert String to Char array

        KeyCharacterMap CharMap;
        if (Build.VERSION.SDK_INT >= 11) // My soft runs until API 5
            CharMap = KeyCharacterMap.load(KeyCharacterMap.VIRTUAL_KEYBOARD);
        else
            CharMap = KeyCharacterMap.load(KeyCharacterMap.ALPHA);

        KeyEvent[] events = CharMap.getEvents(szRes);

        for (int i = 0; i < events.length; i += 2) {
            generateKeyEvent(events[i].getKeyCode());
        }
        generateKeyEvent(KeyEvent.KEYCODE_ENTER);
    }

    public int getStatusBarHeight() {
        if (this.statusBarHeight == 0) {
            Display display = DisplayManagerGlobal.getInstance().getRealDisplay(Display.DEFAULT_DISPLAY);
            DisplayMetrics dm = new DisplayMetrics();
            display.getMetrics(dm);
            int w = display.getWidth();
            int h = display.getHeight();
            if (w == 1080 && h > 2100) {
                statusBarHeight = (int) (40 * dm.density);
            } else if (w == 1200 && h == 1824) {
                statusBarHeight = (int) (30 * dm.density);
            } else if (w == 1440 && h == 2696) {
                statusBarHeight = (int) (30 * dm.density);
            } else {
                statusBarHeight = (int) (24 * dm.density);
            }
        }
        return this.statusBarHeight;
    }


}
