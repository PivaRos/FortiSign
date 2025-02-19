# FortiSign: Secure Network Communication

This project demonstrates secure network communication using SSL pinning for both Android and iOS platforms. It incorporates custom scripts to inject SSL pinning logic into the application's native code, enhancing security by verifying server certificates.

## Key Features

- **Android SSL Pinning:** Uses OkHttp and a custom Smali class to pin certificates for specific domains.
- **iOS SSL Pinning:** Employs a dynamic library (dylib) and method swizzling to perform certificate pinning.
- **Automated Build Process:** Includes shell scripts and `watchman` for automated builds upon code changes.
- **Cross-Platform Implementation:** Demonstrates a consistent approach to securing network communication across Android and iOS.

## Technologies Used

- **Android:** Kotlin, Gradle, OkHttp, Apktool, apksigner, Android Studio
- **iOS:** Swift, Xcode, Objective-C, `insert_dylib`

## Prerequisites

**For both Android and iOS:**

- Git
- Python 3

**Android Specific:**

- Java Development Kit (JDK) 1.8 or higher. The path to your JDK should be set in the `JAVA_HOME` environment variable.
- Android SDK. The path to your Android SDK should be configured in `android/android_example/local.properties` (and you may need to install the necessary build-tools through the SDK Manager in Android Studio).
- Android Studio (recommended)
- `apktool` : `brew install apktool` (on macOS using Homebrew)
- `zipalign` : `brew install zipalign` (on macOS using Homebrew)
- `apksigner` : `brew install apksigner` (on macOS using Homebrew)

**iOS Specific:**

- Xcode 14 or higher
- Command-line tools (ensure they are installed through Xcode)
- `insert_dylib`: This tool is used for injecting the dylib into the iOS application binary. You will need to clone it: `git clone https://github.com/Tyilo/insert_dylib.git`. Remember to adjust the paths accordingly.

## Installation

**1. Clone the Repository:**

```bash
git clone https://github.com/PivaRos/FortiSign
cd FortiSign
```

**2. Install Dependencies:**

- **Android:** Follow the instructions in the "Android Specific" section of the Prerequisites above. Ensure that `apktool`, `zipalign`, and `apksigner` are accessible in your PATH. You also need to install Android SDK through Android Studio.
- **iOS:** Follow the instructions in the "iOS Specific" section of the Prerequisites above. Ensure `insert_dylib` is accessible in your path. This will also require the installation of Xcode. `cp /path/to/insert_dylib /usr/local/bin/insert_dylib`

**3. Set up Watchman (Optional but Recommended):**

Watchman monitors the source code and triggers automatic builds for both platforms using the included scripts (`start_android.sh` and `start_ios.sh`).

- Install watchman following the instructions on the official watchman github site [https://facebook.github.io/watchman/](https://facebook.github.io/watchman/).
- run `start_android.sh` or `start_ios.sh` depending on which build system you are going to use.

**4. Configure Keystore (Android Only):**

For Android, you need a keystore file (`./bin/Untitled1` in this case) containing the signing key for your application. The scripts expect the keystore path, key alias, and passwords to be provided as command-line arguments (see Usage Examples below).

## Usage Examples

**Android:**

To build and sign the Android application, run the `build_android.sh` script. You will be prompted for the keystore and password. This is already set in the `build_android.sh` file and works out of the box.

```bash
./build_android.sh
```

**iOS:**

Building the iOS application requires the following steps:

1. Open `ios/GoogleFetcher/GoogleFetcher.xcodeproj` or `ios/SSLPinningDylib/SSLPinningDylib.xcodeproj` in Xcode and build both targets. (Make sure you have a valid signing certificate and provisioning profile configured within Xcode). You'll then need to copy the built framework to the `ios` folder: `/path/to/your/built/SSLPinningDylib.framework`.
2. Run `./build_ios.sh`. This will execute the python script which embeds the dylib and rebuilds the IPA. This script is set up to work out of the box in the same way as the android script, but you might need to add the provisioning profile path (`PROVISIONING_PROFILE`) to the command-line arguments to get it to work.

```bash
./build_ios.sh
```

## Project Structure

```
FortiSign/
├── android/                     # Android project
│   ├── android_example/          # Android app source code
│   │   ├── app/                 # Android app module
│   │   └── ...
│   └── ...
├── ios/                         # iOS project
│   ├── GoogleFetcher/           # iOS app
│   │   ├── GoogleFetcher.xcodeproj/ # Xcode project
│   │   └── ...
│   └── ...
└── readme.md                    # This README file
```

## Scripts

- **`android/build_android.sh`:** Builds and signs the Android APK.
- **`android/start_android.sh`:** Starts a watchman process to monitor for changes and automatically rebuild the android project.
- **`ios/build_ios.sh`:** Builds and signs the iOS IPA.
- **`ios/start_ios.sh`:** Starts a watchman process to monitor for changes and automatically rebuild the ios project.
- **`android/android_ssl_pinning.py`:** Python script for Android SSL pinning injection.
- **`ios/ios_ssl_pinning.py`:** Python script for iOS SSL pinning injection.

## Configuration

- **`android/android_example/local.properties`:** Specifies the Android SDK location. **Do not commit this file to version control.**
- **`android/android_example/gradle.properties`:** Contains Gradle build settings.
- **`ios/GoogleFetcher/GoogleFetcher/Base.lproj/Main.storyboard`:** The main UI storyboard for the iOS application.
- **`ios/SSLPinningDylib/SSLPinningDylib/SSLPinningDylib.m`:** The implementation of the iOS SSL pinning dylib. The expected fingerprint is read from `expected_fingerprint.txt` which is injected into the application bundle.

## Contributing

This repository is not set up for contributions.

## License

License information was not found in the provided codebase.

## Troubleshooting

**Android:**

- **`Error running command: apktool ...`:** Ensure `apktool` is installed and in your PATH.
- **`Error signing APK ...`:** Verify your keystore file path, key alias, and passwords are correct.

**iOS:**

- **`Error running command: insert_dylib ...`:** Ensure `insert_dylib` is installed and in your PATH. The path to `insert_dylib` may need to be adjusted in `ios/build_ios.sh`.
- **Code signing errors:** Ensure your Xcode setup is correct (signing certificates, provisioning profiles).

This README provides a comprehensive overview of the project. Please refer to the individual code files for more detailed information on specific implementation aspects.
