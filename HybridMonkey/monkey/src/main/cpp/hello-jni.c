/*
 * Copyright (C) 2016 The Android Open Source Project
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
 *
 */
#include <jni.h>
#include <android/log.h>
#include <string.h>

#define  LOG_TAG    "bruce-native-dev"
#define  LOGI(...)  __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...)  __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)


/* This is a trivial JNI example where we use a native method
 * to return a new VM String. See the corresponding Java source
 * file located at:
 *
 *   hello-jni/app/src/main/java/com/example/hellojni/HelloJni.java
 */
JNIEXPORT jstring JNICALL
Java_com_devwang_hellojni_HelloJni_stringFromJNI( JNIEnv* env,
                                                  jobject thiz )
{
#if defined(__arm__)
    #if defined(__ARM_ARCH_7A__)
    #if defined(__ARM_NEON__)
      #if defined(__ARM_PCS_VFP)
        #define ABI "armeabi-v7a/NEON (hard-float)"
      #else
        #define ABI "armeabi-v7a/NEON"
      #endif
    #else
      #if defined(__ARM_PCS_VFP)
        #define ABI "armeabi-v7a (hard-float)"
      #else
        #define ABI "armeabi-v7a"
      #endif
    #endif
  #else
   #define ABI "armeabi"
  #endif
#elif defined(__i386__)
#define ABI "x86"
#elif defined(__x86_64__)
#define ABI "x86_64"
#elif defined(__mips64)  /* mips64el-* toolchain defines __mips__ too */
#define ABI "mips64"
#elif defined(__mips__)
#define ABI "mips"
#elif defined(__aarch64__)
#define ABI "arm64-v8a"
#else
#define ABI "unknown"
#endif

    return (*env)->NewStringUTF(env, "Hello from JNI , I'm Bruce !  Compiled with ABI " ABI ".");
}

JNIEXPORT jint JNICALL
Java_com_devwang_hellojni_HelloJni_getFromJNI( JNIEnv* env,
                                                  jobject thiz,jint a,jint b )
{
    LOGI("hello bruce info");
    LOGE("hello bruce error");
    //return (*env)->NewStringUTF(env, "Hello from JNI , I'm Bruce !  " + a);
    return a+b+b+a;

}

JNIEXPORT jint JNICALL
Java_com_devwang_hellojni_HelloJni_addInt( JNIEnv* env,
                                               jobject thiz,jint a,jint b )
{
    LOGE("hello bruce error ===>> addInt()");
     return a + b;//输入整数，输出整数
}
JNIEXPORT jint JNICALL
Java_com_devwang_hellojni_HelloJni_mulDouble( JNIEnv* env,
                                           jobject thiz,jdouble a,jdouble b )
{
    LOGE("hello bruce error ===>> mulDouble()");
    return a * b;//输入实数，输出实数
}

JNIEXPORT jint JNICALL
Java_com_devwang_hellojni_HelloJni_bigger( JNIEnv* env,
                                              jobject thiz,jfloat a,jfloat b )
{
    LOGE("hello bruce error ===>> bigger()");//输入float型实数，输出布尔值，判断a是否大于b
    return a > b;
}

//return (*env)->NewStringUTF(env, "Hello from JNI !");//如果是用C语言格式就用这种方式
//return env->NewStringUTF((char *)"Hello from JNI !");//C++用这种格式
char * JstringToCstr(JNIEnv * env, jstring jstr) { //jstring转换为C++的字符数组指针
    char * pChar ;
    //char * pChar = NULL;//报错 ，头文件 #include <string.h>
    jclass classString = (*env)->FindClass(env,"java/lang/String");
    jstring code = (*env)->NewStringUTF(env,"GB2312");
    jmethodID id = (*env)->GetMethodID(env,classString, "getBytes", "(Ljava/lang/String;)[B");
    jbyteArray arr = (jbyteArray)(*env)->CallObjectMethod(env,jstr, id, code);
    jsize size = (*env)->GetArrayLength(env,arr);
    jbyte * bt = (*env)->GetByteArrayElements(env,arr, JNI_FALSE);
    if(size > 0) {
        pChar = (char*)malloc(size + 1);
        memcpy(pChar, bt, size);
        pChar[size] = 0;
    }
    (*env)->ReleaseByteArrayElements(env,arr, bt, 0);
    return pChar;
}

JNIEXPORT jstring  JNICALL
Java_com_devwang_hellojni_HelloJni_addString( JNIEnv* env,
                                           jobject thiz,jstring a,jstring b )
{
    char * pA = JstringToCstr(env,a);//取得a的C++指针
    char * pB = JstringToCstr(env,b);//取得b的C++指针
    LOGE("hello bruce error ===>> addString()");
    return (*env)->NewStringUTF(env,strcat(pA,pB));//输出a+b
}

JNIEXPORT jintArray JNICALL
Java_com_devwang_hellojni_HelloJni_intArray( JNIEnv* env,
                                              jobject thiz,jintArray a )
{
    //输入整数数组，将其每个元素加10后输出
    //输入值为a，输出值为b
    int N = (*env)->GetArrayLength(env,a); //获取a的元素个数
    jint * pA = (*env)->GetIntArrayElements(env,a, NULL); //获取a的指针
    jintArray b = (*env)->NewIntArray(env,N); //创建数组b，长度为N
    jint * pB = (*env)->GetIntArrayElements(env,b, NULL); //获取b的指针
    //for (int i = 0; i < N; i++) pB = pA + 10; //把a的每个元素加10，赋值给b中对应的元素
    //另一种方法
    (*env)->SetIntArrayRegion(env,b, 0, N, pA); //b是a的复制品
    for (int j = 0; j < N; j++) pB[j] += 10; //b的每个元素加10
    (*env)->ReleaseIntArrayElements(env,a, pA, 0); //释放a的内存
    (*env)->ReleaseIntArrayElements(env,b, pB, 0); //释放b的内存
    LOGE("hello bruce error ===>> intArray()");
    return b; //输出b
}

JNIEXPORT jdoubleArray  JNICALL
Java_com_devwang_hellojni_HelloJni_doubleArray( JNIEnv* env,
                                              jobject thiz,jdoubleArray a )
{
    //输入实数数组，将其每个元素乘2后输出
    //输入值为a，输出值为b
    int N = (*env)->GetArrayLength(env,a); //获取a的元素个数
    jdouble * pA = (*env)->GetDoubleArrayElements(env,a, NULL); //获取a的指针
    jdoubleArray b = (*env)->NewDoubleArray(env,N); //创建数组b，长度为N
    jdouble * pB = (*env)->GetDoubleArrayElements(env,b, NULL); //获取b的指针
    for (int i = 0; i < N; i++) (*pB) = (*pA) * 2; //把a的每个元素乘2，赋值给b中对应的元素
    /*//另一种方法
    env->SetDoubleArrayRegion(b, 0, N, pA); //b是a的复制品
    for (int j = 0; j < N; j++) pB[j] *= 2; //b的每个元素乘2
    */
    (*env)->ReleaseDoubleArrayElements(env,a, pA, 0); //释放a的内存
    (*env)->ReleaseDoubleArrayElements(env,b, pB, 0); //释放b的内存
    LOGE("hello bruce error ===>> doubleArray()");
    return b; //输出b

}

JNIEXPORT jobjectArray  JNICALL
Java_com_devwang_hellojni_HelloJni_stringArray( JNIEnv* env,
                                              jobject thiz,jobjectArray a )
{
    //输入字符串数组，颠倒顺序后输出
    //输入值为a，输出值为b
    int N = (*env)->GetArrayLength(env,a); //获取a的元素个数
    jobjectArray b = (*env)->NewObjectArray(env,N, (*env)->FindClass(env,"java/lang/String"), (*env)->NewStringUTF(env,"")); //创建数组b，长度为N
    for (int i = 0; i < N; i++) { //对于a中的每个元素
        jstring ai = (jstring)(*env)->GetObjectArrayElement(env,a, i); //读出这个元素的值
        (*env)->SetObjectArrayElement(env,b, N - 1 - i, ai); //赋值给b中倒序对应的元素
        (*env)->DeleteLocalRef(env,ai);//释放内存
    }
    LOGE("hello bruce error ===>> addString()");
    return b; //输出b
}