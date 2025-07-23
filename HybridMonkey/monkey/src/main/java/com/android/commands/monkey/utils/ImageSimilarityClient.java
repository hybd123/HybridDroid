package com.android.commands.monkey.utils;

import okhttp3.*;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.File;
import java.io.IOException;
import java.util.concurrent.TimeUnit;

import static com.android.commands.monkey.utils.Config.serverURL;
import static java.lang.Thread.sleep;

public class ImageSimilarityClient {
    // 配置带超时的 OkHttpClient（单位：秒）
    private static final OkHttpClient client = new OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build();

    private static final String SERVER_URL = serverURL;
    private static final int MAX_RETRIES = 3; // 最大重试次数
    private static final long INITIAL_RETRY_DELAY_MS = 1000; // 初始重试延迟

    public static double getSimilarityWithRetry(File imageFileA, File imageFileB)
            throws IOException, JSONException, InterruptedException {

        int retryCount = 0;
        long retryDelayMs = INITIAL_RETRY_DELAY_MS;

        while (retryCount < MAX_RETRIES) {
            try {
                // 1. 检查文件稳定性（例如：2秒内无修改）
                if (!isFileStable(imageFileA, 2000) || !isFileStable(imageFileB, 2000)) {
                    throw new IOException("文件尚未处理完成");
                }

                // 2. 发送请求
                return getSimilarity(imageFileA, imageFileB);

            } catch (IOException e) {
                retryCount++;
                if (retryCount >= MAX_RETRIES) {
                    throw new IOException(String.format("重试 %d 次后失败", MAX_RETRIES), e);
                }

                // 3. 指数退避等待
                Thread.sleep(retryDelayMs);
                retryDelayMs *= 2; // 指数增加等待时间
            }
        }

        throw new IOException("未知错误");
    }

    private static double getSimilarity(File imageFileA, File imageFileB)
            throws IOException, JSONException {

        RequestBody requestBody = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("imageA", imageFileA.getName(),
                        RequestBody.create(MediaType.parse(getMimeType(imageFileA)), imageFileA))
                .addFormDataPart("imageB", imageFileB.getName(),
                        RequestBody.create(MediaType.parse(getMimeType(imageFileB)), imageFileB))
                .build();

        Request request = new Request.Builder()
                .url(SERVER_URL)
                .post(requestBody)
                .build();

        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                String errorBody = response.body() != null ? response.body().string() : "empty body";
                throw new IOException("HTTP " + response.code() + ": " + errorBody);
            }

            String jsonResponse = response.body().string();
            JSONObject json = new JSONObject(jsonResponse);

            if (!json.has("similarity")) {
                throw new JSONException("无效响应: " + jsonResponse);
            }

            return json.getDouble("similarity");
        }
    }

    private static String getMimeType(File file) {
        String name = file.getName().toLowerCase();
        if (name.endsWith(".jpg") || name.endsWith(".jpeg")) {
            return "image/jpeg";
        } else if (name.endsWith(".png")) {
            return "image/png";
        } else {
            return "image/*";
        }
    }

    public static boolean isFileStable(File file, long stabilityWindowMs) {
        long lastModified = file.lastModified();
        return (System.currentTimeMillis() - lastModified) > stabilityWindowMs;
    }
}
