//
// Created by xmq on 2025/2/26.
//

#include "hybirddroid_native.h"

extern "C" {

// 全局变量：Python 解释器初始化标志
static bool isPythonInitialized = false;

JNIEXPORT jdouble JNICALL
Java_com_bytedance_fastbot_hybirddroidClient_calculateSimilarity(
        JNIEnv *env, jclass clazz, jstring jScriptDir, jstring jImageA, jstring jImageB) {

    const char *scriptDir = env->GetStringUTFChars(jScriptDir, NULL);
    const char *imageA = env->GetStringUTFChars(jImageA, NULL);
    const char *imageB = env->GetStringUTFChars(jImageB, NULL);
    double similarity = -1.0;

    // 初始化 Python 解释器（仅一次）
    if (!isPythonInitialized) {
        Py_Initialize();
        PyEval_InitThreads();
        isPythonInitialized = true;
    }

    PyGILState_STATE gstate = PyGILState_Ensure();

    try {
        // 添加脚本目录到 Python 路径
        PyRun_SimpleString("import sys");
        std::string pathCmd = "sys.path.append('" + std::string(scriptDir) + "')";
        PyRun_SimpleString(pathCmd.c_str());

        // 导入模块
        PyObject *pModule = PyImport_ImportModule("similarity");
        if (pModule) {
            PyObject *pFunc = PyObject_GetAttrString(pModule, "calculate_similarity");
            if (pFunc && PyCallable_Check(pFunc)) {
                PyObject *pArgs = PyTuple_Pack(2,
                                               PyUnicode_FromString(imageA),
                                               PyUnicode_FromString(imageB));
                PyObject *pResult = PyObject_CallObject(pFunc, pArgs);
                similarity = PyFloat_AsDouble(pResult);
                Py_DECREF(pArgs);
                Py_DECREF(pResult);
            }
            Py_XDECREF(pFunc);
            Py_DECREF(pModule);
        }
    } catch (...) {
        PyErr_Print();
    }

    PyGILState_Release(gstate);

    env->ReleaseStringUTFChars(jScriptDir, scriptDir);
    env->ReleaseStringUTFChars(jImageA, imageA);
    env->ReleaseStringUTFChars(jImageB, imageB);

    return similarity;
}

}