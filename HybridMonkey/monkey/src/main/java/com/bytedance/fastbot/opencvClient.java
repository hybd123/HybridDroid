package com.bytedance.fastbot;

import android.os.Build;

import com.android.commands.monkey.utils.Logger;

import java.io.File;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;

public class opencvClient {
    private static final String BASE_LIB_PATH = "/data/local/tmp";

    public static void loadLibraryFromJar(String libraryName) {
            // 1. 获取设备支持的 ABI 列表
            String[] abis = Build.SUPPORTED_ABIS;
            Logger.println("abis: " + abis);
            Logger.println("loading opencv lib...");
            for (String abi : abis) {
                String libPath = getLibPath(abi);
                Logger.println("libpath:"+libPath);
                if (new File(libPath).exists()) {
                    System.load(libPath);
                    return; // 加载成功即退出
                }
            }
            Logger.println("load failed..");
            throw new RuntimeException("No compatible OpenCV library found");

    }

    private static String getLibPath(String abi) {
        return BASE_LIB_PATH + "/" + abi + "/libopencv_java4.so";
    }

}
