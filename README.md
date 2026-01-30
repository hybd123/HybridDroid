# HybridDroid

HybridDroid is a novel LLM-powered Random Testing Framwork.
We realize this approach on top of two different AIG tools for mobile apps, Monkey, a state-of-the-practice tool and Droidbot, a state-of-the-art tool.

## 📈 Experimental Results

We evaluated our tool across 12 popular open-source Android apps using a consistent 3-hour time budget. The metrics used include **Line**, **Branch**, **Method**, and **Class** coverage.

### 📊 RQ1: Coverage Results

> Below is the full experimental coverage data across tools and applications:

| App              | Tool            | Avg Line Cov(%) | Avg Branch Cov(%) | Avg Method Cov(%) | Avg Class Cov(%) |
| ---------------- | --------------- | --------------- | ----------------- | ----------------- | ---------------- |
| AmazeFileManager | HybridMonkey    | 36.50           | 27.04             | 43.99             | 51.06            |
| AmazeFileManager | Fastbot         | 31.34           | 22.93             | 39.25             | 46.83            |
| AmazeFileManager | Monkey*        | 33.74           | 24.75             | 41.41             | 48.42            |
| AmazeFileManager | Monkey          | 26.81           | 19.61             | 34.46             | 43.19            |
| AmazeFileManager | HybridDroidbot  | 33.14           | 24.07             | 41.01             | 49.80            |
| AmazeFileManager | Droidbot*       | 23.36           | 16.13             | 30.70             | 39.18            |
| AmazeFileManager | GPTDroid        | 14.03           | 9.06              | 20.08             | 30.67            |
| AmazeFileManager | Aurora          | 32.58           | 23.93             | 40.38             | 49.39            |
| AntennaPod       | HybridMonkey    | 49.72           | 36.41             | 53.41             | 66.18            |
| AntennaPod       | Fastbot         | 33.44           | 22.62             | 36.99             | 49.53            |
| AntennaPod       | Monkey*        | 49.09           | 35.84             | 53.04             | 65.63            |
| AntennaPod       | Monkey          | 25.54           | 14.67             | 29.01             | 43.82            |
| AntennaPod       | HybridDroidbot  | 48.43           | 35.70             | 52.19             | 65.47            |
| AntennaPod       | Droidbot*       | 31.87           | 20.84             | 35.71             | 49.71            |
| AntennaPod       | GPTDroid        | 10.46           | 4.63              | 12.31             | 23.41            |
| AntennaPod       | Aurora          | 8.14            | 3.45              | 9.93              | 20.00            |
| MyExpenses       | HybridMonkey    | 33.32           | 17.05             | 35.42             | 42.68            |
| MyExpenses       | Fastbot         | 23.95           | 10.80             | 24.16             | 31.47            |
| MyExpenses       | Monkey*        | 31.92           | 16.43             | 32.86             | 38.44            |
| MyExpenses       | Monkey          | 25.47           | 12.28             | 25.21             | 31.22            |
| MyExpenses       | HybridDroidbot  | 32.22           | 16.66             | 33.85             | 39.25            |
| MyExpenses       | Droidbot*       | 27.56           | 13.00             | 28.79             | 34.95            |
| MyExpenses       | GPTDroid        | 18.19           | 7.23              | 16.74             | 24.30            |
| MyExpenses       | Aurora          | 13.28           | 4.95              | 14.15             | 20.77            |
| NewPipe          | HybridMonkey    | 46.29           | 32.28             | 53.28             | 63.04            |
| NewPipe          | Fastbot         | 11.94           | 6.70              | 15.10             | 30.74            |
| NewPipe          | Monkey*        | 32.12           | 21.30             | 37.76             | 50.97            |
| NewPipe          | Monkey          | 29.45           | 19.87             | 34.24             | 47.26            |
| NewPipe          | HybridDroidbot  | 35.97           | 24.07             | 42.17             | 55.15            |
| NewPipe          | Droidbot*       | 21.40           | 13.13             | 25.73             | 39.84            |
| NewPipe          | GPTDroid        | 6.38            | 3.48              | 8.41              | 20.36            |
| NewPipe          | Aurora          | 16.39           | 9.21              | 20.73             | 38.74            |
| Omni-Notes       | HybridMonkey    | 48.38           | 40.49             | 49.42             | 58.93            |
| Omni-Notes       | Fastbot         | 43.12           | 33.53             | 44.66             | 56.24            |
| Omni-Notes       | Monkey*        | 30.34           | 23.69             | 32.51             | 43.76            |
| Omni-Notes       | Monkey          | 23.98           | 17.81             | 26.21             | 38.00            |
| Omni-Notes       | HybridDroidbot  | 51.79           | 43.26             | 52.77             | 62.40            |
| Omni-Notes       | Droidbot*       | 21.61           | 16.42             | 21.80             | 29.44            |
| Omni-Notes       | GPTDroid        | 12.70           | 9.33              | 15.42             | 24.80            |
| Omni-Notes       | Aurora          | 24.41           | 17.93             | 26.36             | 38.00            |
| OwnTracks        | HybridMonkey    | 62.04           | 44.32             | 49.79             | 48.18            |
| OwnTracks        | Fastbot         | 58.96           | 42.14             | 46.17             | 45.97            |
| OwnTracks        | Monkey*        | 60.34           | 43.01             | 48.38             | 47.75            |
| OwnTracks        | Monkey          | 53.72           | 38.63             | 44.49             | 44.93            |
| OwnTracks        | HybridDroidbot  | 59.39           | 42.93             | 48.11             | 47.02            |
| OwnTracks        | Droidbot*       | 59.94           | 43.09             | 48.55             | 47.20            |
| OwnTracks        | GPTDroid        | 49.67           | 35.20             | 40.11             | 41.71            |
| OwnTracks        | Aurora          | 36.21           | 25.31             | 28.12             | 33.02            |
| RedReader        | HybridMonkey    | 25.15           | 19.43             | 28.81             | 39.40            |
| RedReader        | Fastbot         | 20.34           | 14.45             | 24.59             | 35.30            |
| RedReader        | Monkey*        | 25.00           | 18.95             | 28.65             | 39.43            |
| RedReader        | Monkey          | 19.18           | 13.56             | 22.96             | 32.04            |
| RedReader        | HybridDroidbot  | 23.57           | 17.04             | 27.47             | 38.47            |
| RedReader        | Droidbot*       | 19.18           | 13.56             | 22.96             | 32.04            |
| RedReader        | GPTDroid        | 14.10           | 9.34              | 18.90             | 28.06            |
| RedReader        | Aurora          | 16.75           | 11.57             | 21.04             | 30.27            |
| Wikipedia        | HybridMonkey    | 14.95           | 9.74              | 16.28             | 23.93            |
| Wikipedia        | Fastbot         | 14.67           | 9.50              | 16.33             | 23.88            |
| Wikipedia        | Monkey*        | 14.80           | 9.61              | 16.12             | 23.76            |
| Wikipedia        | Monkey          | 10.79           | 6.98              | 12.15             | 19.43            |
| Wikipedia        | HybridDroidbot  | 14.20           | 9.26              | 15.67             | 23.25            |
| Wikipedia        | Droidbot*       | 12.64           | 8.19              | 14.42             | 22.05            |
| Wikipedia        | GPTDroid        | 4.66            | 2.77              | 6.52              | 10.83            |
| Wikipedia        | Aurora          | 12.82           | 8.19              | 14.37             | 22.51            |
| AlarmClock       | HybridMonkey    | 79.52           | 48.26             | 80.68             | 89.60            |
| AlarmClock       | Fastbot         | 76.79           | 43.12             | 76.18             | 87.20            |
| AlarmClock       | Monkey*        | 78.76           | 47.34             | 80.00             | 88.80            |
| AlarmClock       | Monkey          | 76.74           | 44.59             | 76.18             | 86.40            |
| AlarmClock       | HybridDroidbot  | 78.10           | 45.87             | 79.40             | 86.67            |
| AlarmClock       | Droidbot*       | 78.28           | 47.34             | 79.10             | 85.60            |
| AlarmClock       | GPTDroid        | 39.33           | 27.52             | 47.19             | 52.00            |
| AlarmClock       | Aurora          | 69.95           | 40.36             | 69.29             | 80.00            |
| Feeder           | HybridMonkey    | 34.16           | 19.38             | 52.37             | 63.04            |
| Feeder           | Fastbot         | 7.60            | 3.01              | 18.86             | 31.63            |
| Feeder           | Monkey*        | 15.38           | 7.47              | 30.46             | 42.39            |
| Feeder           | Monkey          | 8.24            | 3.66              | 19.07             | 31.63            |
| Feeder           | HybridDroidbot  | 24.36           | 14.14             | 38.40             | 50.22            |
| Feeder           | Droidbot*       | 17.40           | 9.81              | 28.97             | 40.98            |
| Feeder           | GPTDroid        | 6.67            | 2.66              | 16.90             | 30.43            |
| Feeder           | Aurora          | 8.09            | 3.46              | 18.38             | 31.34            |
| Chess            | HybridMonkey    | 46.83           | 41.54             | 56.60             | 67.71            |
| Chess            | Fastbot         | 49.46           | 49.53             | 59.29             | 67.54            |
| Chess            | Monkey*        | 44.62           | 37.75             | 52.72             | 68.31            |
| Chess            | Monkey          | 37.91           | 35.48             | 47.35             | 55.30            |
| Chess            | HybridDroidbot  | 45.01           | 39.76             | 54.23             | 65.68            |
| Chess            | Droidbot*       | 39.54           | 32.45             | 47.99             | 62.20            |
| Chess            | GPTDroid        | 15.43           | 10.21             | 19.16             | 25.00            |
| Chess            | Aurora          | 30.62           | 26.72             | 36.39             | 43.22            |
| AnkiDroid        | HybridMonkey    | 40.14           | 25.55             | 41.97             | 48.20            |
| AnkiDroid        | Fastbot         | 36.83           | 23.65             | 38.29             | 43.27            |
| AnkiDroid        | Monkey*        | 22.14           | 11.70             | 23.07             | 30.29            |
| AnkiDroid        | Monkey          | 20.89           | 11.00             | 22.38             | 29.41            |
| AnkiDroid        | HybridDroidbot  | 37.21           | 22.82             | 38.83             | 45.60            |
| AnkiDroid        | Droidbot*       | 32.05           | 19.52             | 33.64             | 40.52            |
| AnkiDroid        | GPTDroid        | 11.28           | 5.98              | 11.26             | 16.59            |
| AnkiDroid        | Aurora          | 20.20           | 14.97             | 7.80              | 15.64            |

### 📊 Discussion Results

> This table presents additional experimental results from our discussion section, comparing LLMDroid, HybridDroidbot, and HybridMonkey on the original dataset of LLMDoid:

| App Name            | LLMDroid | HybridDroidbot | HybridMonkey |
| ------------------- | -------- | -------------- | ------------ |
| Wish: Shop and Save | 11.14%   | 11.90%         | 12.10%       |
| Twitch              | 1.74%    | 1.80%          | 2.20%        |
| Wikipedia           | 2.10%    | 14.30%         | 16.10%       |
| Quora               | 1.80%    | 1.60%          | 1.81%        |
| Fing                | 13.72%   | 16.30%         | 12.80%       |
| Lefun Health        | 2.15%    | 2.00%          | 2.30%        |
| Red Bull TV         | 5.45%    | 2.00%          | 5.60%        |
| Time Planner        | 13.62%   | 15.80%         | 20.60%       |
| NewPipe             | 20.16%   | 18.10%         | 30.50%       |
| NHK WORLD-JAPAN     | 8.19%    | 7.70%          | 8.10%        |
| Renpho Health       | 1.23%    | 1.70%          | 1.70%        |
| Mood Tracker        | 12.58%   | 15.70%         | 17.30%       |
| CafeNovel           | 1.39%    | 1.40%          | 1.40%        |
| OceanEx             | 6.05%    | 5.80%          | 6.80%        |
| **ACC (Average)**   | **7.24%**    | **8.29%**          | **9.95%**        |

> **Note:** ACC represents Average Code Coverage, the mean code coverage percentage achieved across all tested applications.

# 📦 Installation

```
git clone https://github.com/hybd123/HybridDroid.git
cd HybridDroid/HybridDroidbot
pip install -r requirements.txt

```

🔧 Make sure you have Android SDK and emulator/device setup.

# ⚙️ Usage

Run HybridMonkey

```
cd HybridMonkey
adb -s device-serial push max.config /sdcard
adb -s device-serial push awl.strings /sdcard
adb -s device-serial push libs/*  /data/local/tmp/
adb -s device-serial push monkeyq.jar /sdcard/monkeyq.jar
adb -s device-serial install AmazeFileManager.apk
adb -s device-serial shell CLASSPATH=/sdcard/monkeyq.jar:/sdcard/framework.jar:/sdcard/fastbot-thirdpart.jar LD_LIBRARY_PATH="/data/local/tmp/x86_64" exec app_process /system/bin com.android.commands.monkey.Monkey -p <package_name> --running-minutes <test_time> --ignore-crashes --ignore-timeouts --ignore-security-exceptions  --bugreport --output-directory <output_path> --throttle <throttle_time> -v <count>
```

Run HybridDroidbot

```
cd HybridDroidbot
python3 start.py -d "$DEVICE_SERIAL" -a "$APK_PATH" -o "$RESULT_DIR" -timeout "$TEST_TIME" -grant_perm -is_emulator -accessibility_auto 2>&1 | tee -a "$LOG_FILE"
```

# 🔧 Configuration Options

Option	Description
--apk	Path to the APK file
--device/--avd	Target device serial name or AVD
--timeout	Testing time in seconds
--llm	Enable or disable LLM guidance
--output	Directory to store logs and coverage

# 🙌 Acknowledgements

Based on the enhancements of Monkey and Droidbot.

LLM support powered by OpenAI.
