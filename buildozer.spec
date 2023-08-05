[app]
title = An26MTOW
package.name = an26MTOW
package.domain = com.github.isayeu
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db
#requirements = python3,kivy
requirements = python3,Cython==0.29.36,kivy,numpy
#requirements = python3,Cython==3.0.0,kivy
python_version = 3.8
cython.language_level = 3
version = 2.9.4
# Release signing configuration
android.p4a_release_keyalias = andrei
android.p4a_release_keystore = my-release-key.keystore
android.p4a_release_keystore_pass = my_keystore_vfcnth
android.p4a_release_keyalias_pass = my_keyalias_vfcnth
#__version__ = "0.1.2"
#requirements.source.kivy = ~/kivy-android/kivy
orientation = portrait
fullscreen = 0
# (int) Target Android API, should be as high as possible.
android.api = 30
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.sdk_platform = 34
# Android NDK directory (if empty, it will be automatically downloaded.)
#android.ndk_path = /opt/android-sdk/ndk/25.2.9519653
#android.add_compile_options = "sourceCompatibility = 1.8", "targetCompatibility = 1.8"
# Android SDK directory (if empty, it will be automatically downloaded.)
android.sdk_path = /opt/android-sdk
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1

