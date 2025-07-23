package com.android.commands.monkey.utils;

import android.annotation.TargetApi;
import android.os.Build;

import com.android.commands.monkey.action.LLMAction;
import com.android.commands.monkey.events.MonkeyEvent;
import com.android.commands.monkey.events.MonkeyEventQueue;

import org.opencv.core.Core;
import org.opencv.core.Mat;
import org.opencv.core.Size;
import org.opencv.imgcodecs.Imgcodecs;
import org.opencv.imgproc.Imgproc;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public class UITarpitDetector {

    private static final double DEFAULT_THRESHOLD = 0.95;
    private static final double REUSE_THRESHOLD = 0.99;

    private int simK;
    private int simCount;
    private String tarpitSaveDir = "/sdcard/fastbot/tarpit";
    private List<Tarpit> tarpitList;
    private MonkeyEventQueue mQ;
    private static int consecutiveFails = 0;
    private Tarpit targetTarpit;

    public UITarpitDetector(int simK, MonkeyEventQueue mQ) {
        this.simK = simK;
        this.mQ = mQ;
        new File(tarpitSaveDir).mkdirs();
        tarpitList = new ArrayList<>();
    }

    public boolean isSimilarPage(File currentStateScreen, File lastStateScreen) {
        // Read current and last state screenshot
//        String currentStateScreen = currentState.getStateScreen();
//        double simScore = 0;
//        try {
//            simScore = ImageSimilarityClient.getSimilarityWithRetry(currentStateScreen, lastStateScreen);
//            Logger.println("similarity score: " + simScore);
//        } catch (IOException | JSONException | InterruptedException e) {
//            e.printStackTrace();
//        }
        try {
            double simScore = calculateSimilarity(lastStateScreen, currentStateScreen);
            Logger.println("similarity score: " + simScore);
            consecutiveFails = 0; // 成功时重置计数器
            return simScore >= DEFAULT_THRESHOLD;
        } catch (Exception e) {
            if (++consecutiveFails > 10) {
                Logger.errorPrintln("连续失败过多，禁用检测");
            }
        }
        return false;
    }

    public boolean detectedUiTarpit(File cureentScreen, File lastScreen) {
        if (!isSimilarPage(cureentScreen, lastScreen)) {
            simCount = 0;
        } else {
            simCount++;
        }
        return simCount >= simK;
    }


    public void saveUiTarpits() {
//        try (Writer writer = new FileWriter(tarpitSaveDir + File.separator + "UITarpits.json")) {
//            new Gson().toJson(toSaveTarpits, writer);
//            Logger.println("UI traps saved successfully.");
//        } catch (IOException e) {
//            Logger.errorPrintln("Error saving UI traps: " + e.getMessage());
//        }
    }

    public void printUiTarpits() {
        for (Tarpit tarpit : tarpitList) {
            Logger.println("tarpit name: " + tarpit.getTarpitName() + ", visited times: " + tarpit.getVisitedTimes() + ", actions: " + tarpit.getTarpitActions().toString());
        }
        Logger.println("total tarpits: " + tarpitList.size());
    }

    public void setTarpit(Tarpit tarpit){
        targetTarpit = tarpit;
    }

    public Tarpit getTargetTarpit(){
        return targetTarpit;
    }

    @TargetApi(Build.VERSION_CODES.O)
    public boolean isNewTarpit(File screenshot) {
        for (Tarpit tarpit : tarpitList) {
            File tarpitImg = tarpit.getTarpitScreen();
            double simScore = 0;
            try {
                 simScore = calculateSimilarity(screenshot, tarpitImg);
                 consecutiveFails = 0; // 成功时重置计数器
            }catch (Exception e){
                if (++consecutiveFails > 10) {
                    Logger.errorPrintln("连续失败过多，禁用检测");
                }
            }
            if (simScore >= REUSE_THRESHOLD) {
                Logger.println("Visiting known tarpit: " + tarpit.getTarpitName());
                tarpit.addVisitedTimes();
                targetTarpit = tarpit;
                return false;
            }
        }
        List<MonkeyEvent> actions = new ArrayList<>();
        File tarpitpath = modifyScreenshotPath(screenshot);
        // 移动文件到新路径
        try {
            moveFile(screenshot.toPath(), tarpitpath.toPath());
            System.out.println("File moved to: " + tarpitpath.getPath());
        } catch (IOException e) {
            System.err.println("Failed to move the file: " + e.getMessage());
        }

        targetTarpit = new Tarpit(tarpitList.size(), actions, tarpitpath);
        targetTarpit.addVisitedTimes();
        tarpitList.add(targetTarpit);
        Logger.println("New UI tarpit saved: " + targetTarpit.getTarpitName());
        return true;
    }

    // 方法用于修改截图的路径
    public File modifyScreenshotPath(File originalFile) {
        String fileName = originalFile.getName();
        return new File(tarpitSaveDir, fileName);
    }

    // 方法用于移动文件
    public static void moveFile(Path originalPath, Path newPath) throws IOException {
        // 确保目标目录存在
        Files.createDirectories(newPath.getParent());
        // 使用 Files.move() 方法移动文件
        Files.move(originalPath, newPath);
    }


    public void addTarpitActions(Tarpit tarpit, LLMAction action) {
        for(MonkeyEvent event: mQ){
            String type = action.getType().toString();
            tarpit.addTarpitActions(event);
            Logger.println("UI tarpit updated : " + tarpit.getTarpitName() + ", add event: " + type + ", event count:" + tarpit.getTarpitActions().size());
        } //contain throttle event
    }

    public void clearTarpitActions(String tarpitName) {
//        tarpitList.get(tarpitName).clearActions();
    }

    public Tarpit getTarpitById(int tarpitId) {
        return tarpitList.get(tarpitId);
    }

    public static double calculateSimilarity(File fileA, File fileB) {
        int maxRetries = 3;          // 最大重试次数
        long retryInterval = 500;    // 重试间隔(ms)
        int retryCount = 0;

        Mat imgA = null;
        Mat imgB = null;

        while (retryCount < maxRetries) {
            try {
                // 1. 检查文件是否存在
                if (!fileA.exists() || !fileB.exists()) {
                    throw new FileNotFoundException("文件未生成: " +
                            (!fileA.exists() ? fileA : fileB));
                }

                // 2. 读取图片
                imgA = Imgcodecs.imread(fileA.getAbsolutePath());
                imgB = Imgcodecs.imread(fileB.getAbsolutePath());

                // 3. 验证是否读取成功
                if (imgA.empty() || imgB.empty()) {
                    throw new IOException("图片数据未完全写入: " +
                            (imgA.empty() ? fileA : fileB));
                }

                // 4. 计算相似度
                int hashSize = 8;
                long hashA = dhash(imgA, hashSize);
                long hashB = dhash(imgB, hashSize);
                return 1.0 - (double) hammingDistance(hashA, hashB) / 64.0;

            } catch (FileNotFoundException e) {
                // 文件不存在（临时问题）- 等待后重试
                Logger.warningPrintln("文件未找到，重试中 (第 " + (retryCount+1) + " 次): " + e.getMessage());
                retryCount++;
                sleep(retryInterval);

            } catch (IOException e) {
                // 数据不完整（临时问题）- 等待后重试
                Logger.warningPrintln("图片数据不完整，重试中 (第 " + (retryCount+1) + " 次): " + e.getMessage());
                retryCount++;
                sleep(retryInterval);

            } catch (Exception e) {
                // 其他错误（如权限问题）- 直接终止
                Logger.warningPrintln("致命错误: " + e.getMessage());
                throw new RuntimeException(e);

            } finally {
                // 释放资源，避免内存泄漏
                if (imgA != null) imgA.release();
                if (imgB != null) imgB.release();
            }
        }

        // 重试全部失败后返回安全值（例如认为不相似）
        Logger.errorPrintln("重试 " + maxRetries + " 次失败，跳过本次检测");
        return 0; // 返回最大值表示不相似，避免触发终止逻辑
    }

    private static void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

//    public static double calculateSimilarity(File fileA, File fileB) {
//        if (!fileA.exists() || !fileB.exists()) {
//            throw new RuntimeException("文件不存在: " + (fileA.exists() ? fileB.getAbsolutePath() : fileA.getAbsolutePath()));
//        }
//        Mat imgA = Imgcodecs.imread(fileA.getAbsolutePath());
//        Mat imgB = Imgcodecs.imread(fileB.getAbsolutePath());
//        if (imgA.empty() || imgB.empty()) {
//            throw new RuntimeException("无法读取图片文件: " +
//                    (imgA.empty() ? fileA.getAbsolutePath() : fileB.getAbsolutePath()));
//        }
//
//        try {
//            // 3. 计算哈希
//            int hashSize = 8;
//            long hashA = dhash(imgA, hashSize);
//            long hashB = dhash(imgB, hashSize);
//
//            // 4. 计算相似度
//            return 1.0 - (double) hammingDistance(hashA, hashB) / 64.0; // 64 is the dhash bit count
//        } finally {
//            // 释放资源
//            imgA.release();
//            imgB.release();
//        }
//    }

    public static long dhash(Mat image, int hashSize) {
        if (image.empty()) throw new IllegalArgumentException("输入图像为空");
        // 调整尺寸前检查原图尺寸
        if (image.cols() <= hashSize || image.rows() <= hashSize) {
            throw new IllegalArgumentException("图片尺寸过小");
        }
        // 调整大小
        Imgproc.resize(image, image, new Size(hashSize + 1, hashSize));
        // 转换为灰度图
        Mat gray = new Mat();
        int channels = image.channels();
        if (channels == 3 || channels == 4) {
            Imgproc.cvtColor(image, gray, Imgproc.COLOR_BGR2GRAY);
        } else if (channels == 1) {
            image.copyTo(gray);
        } else {
            throw new IllegalArgumentException("不支持的图像通道数: " + channels);
        }

        // Calculate differences
        Mat diff = new Mat();
        Core.compare(gray.colRange(0, gray.cols() - 1), gray.colRange(1, gray.cols()), diff, Core.CMP_GT);
        long hash = 0;
        for (int i = 0; i < diff.rows(); i++) {
            for (int j = 0; j < diff.cols(); j++) {
                if (diff.get(i, j)[0] > 0) {
                    hash |= (1L << (i * hashSize + j));
                }
            }
        }
        gray.release();
        diff.release();
        return hash;
    }

    public static int hammingDistance(long hash1, long hash2) {
        return Long.bitCount(hash1 ^ hash2);
    }

}