package com.android.commands.monkey.source;

import static com.android.commands.monkey.utils.Config.doHistoryRestart;
import static com.android.commands.monkey.utils.Config.historyRestartRate;
import static com.android.commands.monkey.utils.Config.refectchInfoCount;
import static com.android.commands.monkey.utils.Config.imageWriterCount;
import static com.android.commands.monkey.utils.Config.refectchInfoWaitingInterval;
import static com.android.commands.monkey.fastbot.client.ActionType.SCROLL_BOTTOM_UP;
import static com.android.commands.monkey.fastbot.client.ActionType.SCROLL_TOP_DOWN;


import android.annotation.TargetApi;
import android.app.UiAutomation;
import android.graphics.PointF;
import android.graphics.Rect;
import android.graphics.Bitmap;
import android.content.Context;
import android.content.ComponentName;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.os.SystemClock;
import android.view.KeyCharacterMap;
import android.os.Build;
import android.util.DisplayMetrics;
import android.hardware.display.DisplayManagerGlobal;
import android.util.DisplayMetrics;
import android.view.Display;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;

import com.android.commands.monkey.action.*;
import com.android.commands.monkey.utils.*;
import com.android.commands.monkey.events.*;
import com.android.commands.monkey.framework.AndroidDevice;
import com.android.commands.monkey.action.LLMAction;
import com.android.commands.monkey.fastbot.client.ActionType;
import com.android.commands.monkey.utils.*;
import com.android.commands.monkey.utils.Logger;
import com.android.commands.monkey.utils.UITarpitDetector;
import com.android.commands.monkey.events.MonkeyEvent;
import com.android.commands.monkey.events.MonkeyEventQueue;
import com.android.commands.monkey.events.MonkeyEventSource;
import com.android.commands.monkey.events.base.MonkeyActivityEvent;
import com.android.commands.monkey.events.base.MonkeyCommandEvent;
import com.android.commands.monkey.events.base.MonkeyIMEEvent;
import com.android.commands.monkey.events.base.MonkeyKeyEvent;
import com.android.commands.monkey.events.base.MonkeyDataActivityEvent;
import com.android.commands.monkey.events.base.MonkeyRotationEvent;
import com.android.commands.monkey.events.base.MonkeySchemaEvent;
import com.android.commands.monkey.events.base.MonkeyThrottleEvent;
import com.android.commands.monkey.events.base.MonkeyTouchEvent;
import com.android.commands.monkey.events.base.MonkeyWaitEvent;


import java.io.File;
import java.util.*;
import java.util.concurrent.TimeoutException;
import java.lang.Exception;
import java.util.Locale;
import java.io.IOException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.MediaType;
import okhttp3.RequestBody;

import org.json.JSONArray;
import org.json.JSONObject;


import static com.android.commands.monkey.utils.Config.imageWriterCount;
import static com.android.commands.monkey.utils.Config.startAfterNSecondsofsleep;
import static com.android.commands.monkey.utils.Config.takeScreenshotForEveryStep;
import static com.android.commands.monkey.utils.Config.swipeDuration;
import static com.android.commands.monkey.utils.Config.useRandomClick;
import static com.android.commands.monkey.utils.Config.bytestStatusBarHeight;

public class MonkeySourceLLM implements MonkeyEventSource{
    private static long CLICK_WAIT_TIME = 0L;
    private static long LONG_CLICK_WAIT_TIME = 1000L;

    private static final String GPT_URL = "https://api.chatanywhere.tech/v1/chat/completions";
    private static final String GPT_KEY = "sk-G3dXD5UnEjiv1OVxwc5ZnRSFNccp2WiGOp2tJDjLM7WeDW8D";
    private static final String task = "You are an expert in App GUI testing. Please guide the testing tool to enhance the coverage of functional scenarios in testing the App based on your extensive App testing experience. ";

    private String currentactivity = "";
    private int actionIdCounter = 0;
    private String packageName = "";

    private int timestamp = 0;
    private int lastInputTimestamp = -1;
    private int mEventId;
    private int mEventCount;
    private int timeStep;
    private Random mRandom;
    private List<ComponentName> mMainApps;
    private String intentAction = null;
    private String quickActivity = null;
    private String intentData = null;
    private int statusBarHeight = bytestStatusBarHeight;

    private HashSet<String> activityHistory = new HashSet<>();
    private HashSet<String> actionHistory = new HashSet<>();
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


    public MonkeySourceLLM(Random mRandom, List<ComponentName> mMainApps, HashSet<String> activityHistory,
                           String packageName, MonkeyEventQueue mQ, UiAutomation mUiAutomation,
                           int mEventId, int timeStep, int mEventCount, File mOutputDirectory,
                           String currentactivity, ImageWriterQueue[] mImageWriters, File lastScreen){
        this.mRandom = mRandom;
        this.mMainApps = mMainApps;
        this.packageName = packageName;
        this.activityHistory = activityHistory;
        this.mUiAutomation = mUiAutomation;
        this.mQ = mQ;
        this.mEventId = mEventId;
        this.timeStep = timeStep;
        this.mEventCount = mEventCount;
        this.mOutputDirectory = mOutputDirectory;
        this.currentactivity = currentactivity;
        this.mImageWriters = mImageWriters;
        this.lastScreen = lastScreen;
        Logger.println("initial LLMSource");
//        uiDevice = UiDevice.getInstanceUiAutomation.getInstance());
        systemContext = ContextUtils.getSystemContext();
    }

    private static float lerp(float a, float b, float alpha) {
        return (b - a) * alpha + a;
    }

    public void setmEventCount(int mEventCount){
        this.mEventCount = mEventCount;
    }

    public void setmEventId(int mEventId){
        this.mEventId = mEventId;
    }

    public void setTimeStep(int timeStep){
        this.timeStep = timeStep;
    }

    public int getmEventId() {
        return mEventId;
    }

    public int getmEventCount() {
        return mEventCount;
    }

    public int getTimeStep() {
        return timeStep;
    }

    public void clearActionHistory(){
        actionHistory.clear();
    }

    public void clearActionList(){
        actionList.clear();
    }

    public List<LLMAction> getActionList() {
        return actionList;
    }

    public LLMAction getActions(){
        return actionList.get(0);
    }

    public File getLastScreen(){
        return lastScreen;
    }
    /**
     get LLM event
    **/
    public MonkeyEvent getNextEvent() {
        checkAppActivity();
        if (mQ.isEmpty()) {
            generateLLMEvents();
        }
        mEventCount++;
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

    protected void startRandomMainApp() {
        generateActivityEvents(randomlyPickMainApp(), false);
    }

    public ComponentName randomlyPickMainApp() {
        int total = mMainApps.size();
        int index = mRandom.nextInt(total);
        return mMainApps.get(index);
    }

    protected void generateActivityEvents(ComponentName app, boolean clearPackage) {
        MonkeyActivityEvent e = new MonkeyActivityEvent(app);
        addEvent(e.setEventSource("LLM"));
        generateThrottleEvent(startAfterNSecondsofsleep); // waiting for the loading of apps

    }

    private final void clearEvent() {
        while (!mQ.isEmpty()) {
            MonkeyEvent e = mQ.removeFirst();
        }
    }

    void sleep(long time) {
        try {
            Thread.sleep(time);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    public void generateLLMEvents() {

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

            Logger.println("// Event count: " + mEventCount);
            if(dealWithSystemUI(rootNode))
                return;
            break;
        }

        // If node is null, try to get AccessibilityNodeInfo slow for only once
        if (rootNode == null) {
            topActivityName = AndroidDevice.getTopActivityComponentName();
            rootNode = getRootInActiveWindowSlow();
            if (rootNode != null) {
                Logger.println("// Event count: " + mEventCount);
                if(dealWithSystemUI(rootNode))
                    return;
            }
        }


        LLMAction llmAction = getLLMEvent(rootNode);
        if (llmAction == null){
            Logger.warningPrintln("cannot get LLM action!");
            return;
        }
        ActionType type = llmAction.getType();
        Logger.println("LLM action type: "+ type.toString());
        llmAction.setThrottle(100);

//        timeStep++;
//        long timeMillis = System.currentTimeMillis();
//
//        if (takeScreenshotForEveryStep) {
//            checkOutputDir();
//            File screenshotFile = new File(checkOutputDir(), String.format(stringFormatLocale,
//                    "step-LLM-%d-%s.png", timeStep, timeMillis));
//            Logger.infoFormat("Saving screen shot to %s at step %d ",
//                    screenshotFile, timeStep);
//            takeScreenshot(screenshotFile);
//            lastScreen = screenshotFile;
//            Logger.println("last screen "+ lastScreen.getPath());
//        }

        generateEventsForAction(llmAction);

        Logger.println("End generate LLM event");

    }

    private void takeScreenshot(File screenshotFile) {
        Bitmap map = mUiAutomation.takeScreenshot();
        nextImageWriter().add(map, screenshotFile);
    }

    private ImageWriterQueue nextImageWriter() {
        return mImageWriters[mRandom.nextInt(mImageWriters.length)];
    }

    private File checkOutputDir() {
        File dir = getOutputDir();
        if (!dir.exists()) {
            dir.mkdirs();
        }
        return dir;
    }

    public File getOutputDir() {
        return mOutputDirectory;
    }

    //初始化预编译正则表达式（提升性能）
    private static final Pattern NUMBER_PATTERN = Pattern.compile("-?\\d+"); // 支持负数（如-1）

    @TargetApi(Build.VERSION_CODES.O)
    private LLMAction getLLMEvent(AccessibilityNodeInfo rootNode) {

        String taskPrompt = task + String.format(" Currently, the App is stuck on the %s page, unable to explore more features. You task is to select an action based on the current GUI Information to perform next and help the app escape the UI tarpit.", currentactivity);
        String visitedPagePrompt = "I have already visited the following activities: \n" + String.join("\n", activityHistory);
        String historyPrompt = "I have already tried the following steps with action id in parentheses which should not be selected anymore: \n " + String.join(";\n ", actionHistory);
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
            actionHistory.add(selectedAction.toString());

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


    @TargetApi(Build.VERSION_CODES.O)
    private void generateDesribedActions(AccessibilityNodeInfo node, List<String> actions) {
        if (node == null) return ;
        // 获取控件的边界
        Rect bounds = new Rect();
        node.getBoundsInScreen(bounds);
        int left = bounds.left;
        int top = bounds.top;
        int width = bounds.width();
        int height = bounds.height();
        Logger.println("Bounds" + "Left: " + left + ", Top: " + top + ", Width: " + width + ", Height: " + height);

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
            actionList.add(new LLMAction(ActionType.CLICK, packageName, currentactivity, bounds, viewDesc.toString()).setInputText("Hello, world!").setEditText(true).setUseAdbInput(true));
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
        long throttle = action.getThrottle();
        generateThrottleEvent(throttle);
    }

    protected void generateThrottleEvent(long base) {
        long throttle = base;
        boolean mRandomizeThrottle = false;
        if (mRandomizeThrottle && (throttle > 0)) {
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
        addEvent(new MonkeyThrottleEvent(throttle).setEventSource("LLM throttle"));
    }


    private void generateEventsForActionInternal(Action action) {
        ActionType actionType = action.getType();
        switch (actionType) {
            case BACK:
                generateKeyEvent(KeyEvent.KEYCODE_BACK);
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
        e.setEventSource("LLM");
        addEvent(e);

        e = new MonkeyKeyEvent(KeyEvent.ACTION_UP, key);
        e.setEventSource("LLM");
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
            addEvent(new MonkeyCommandEvent("input text " + inputText).setEventSource("LLM"));

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
                .setIntermediateNote(false).setEventSource("LLM"));

        if (waitTime > 0) {
            MonkeyWaitEvent we = new MonkeyWaitEvent(waitTime);
            addEvent(we.setEventSource("LLM"));
        }

        addEvent(new MonkeyTouchEvent(MotionEvent.ACTION_UP).setDownTime(downAt).addPointer(0, p1.x, p1.y)
                .setIntermediateNote(false).setEventSource("LLM"));
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
                .setIntermediateNote(false).setType(1).setEventSource("LLM"));

        int steps = 10;
        long waitTime = swipeDuration / steps;
        for (int i = 0; i < steps; i++) {
            float alpha = i / (float) steps;
            addEvent(new MonkeyTouchEvent(MotionEvent.ACTION_MOVE).setDownTime(downAt)
                    .addPointer(0, lerp(start.x, end.x, alpha), lerp(start.y, end.y, alpha)).setIntermediateNote(true).setType(1).setEventSource("LLM"));
            addEvent(new MonkeyWaitEvent(waitTime).setEventSource("LLM"));
        }

        addEvent(new MonkeyTouchEvent(MotionEvent.ACTION_UP).setDownTime(downAt).addPointer(0, end.x, end.y)
                .setIntermediateNote(false).setType(1).setEventSource("LLM"));
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

    private final void addEvent(MonkeyEvent event) {
        mQ.addLast(event);
        event.setEventId(mEventId++);
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

    public boolean validate(){
        return true;
    }

    public void setAttribute(String packageName, String appVersion, String intentAction, String intentData, String quickActivity) {
        this.packageName = packageName;
        this.appVersion = (!appVersion.equals("")) ? appVersion : this.getAppVersionCode();
        this.intentAction = intentAction;
        this.intentData = intentData;
        this.quickActivity = quickActivity;
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

    public void setVerbose(int verbose) {
        mVerbose = verbose;
    }





}