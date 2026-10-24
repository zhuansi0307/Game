import java.net.URI

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.partsvision.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.partsvision.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 2
        versionName = "0.2.0"

        // Real phones only: drops the x86 copies of every native library (much smaller APK).
        ndk { abiFilters += setOf("arm64-v8a", "armeabi-v7a") }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            // Signed with the debug key so the CI-built APK can be installed directly.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
    }
    androidResources {
        noCompress += "onnx"
    }
    packaging {
        resources {
            excludes += setOf(
                "META-INF/DEPENDENCIES", "META-INF/LICENSE*", "META-INF/NOTICE*",
                "META-INF/*.kotlin_module", "META-INF/versions/9/previous-compilation-data.bin",
            )
        }
    }
}

// On-device models, fetched once into assets from this repo's releases:
//  - DINOv2-small int8 (~24 MB) image embedder, tools/export_dinov2.py
//  - FastSAM-s (~47 MB) object proposer, tools/export_fastsam.py
val models = mapOf(
    "dinov2_small_int8.onnx" to "https://github.com/zhuansi0307/Game/releases/download/model-dinov2s-v1/dinov2_small_int8.onnx",
    "fastsam_s_512.onnx" to "https://github.com/zhuansi0307/Game/releases/download/model-fastsam-s-v1/fastsam_s_512.onnx",
)
val downloadModels by tasks.registering {
    val targets = models.keys.map { file("src/main/assets/$it") }
    outputs.files(targets)
    doLast {
        models.forEach { (name, url) ->
            val target = file("src/main/assets/$name")
            if (!target.exists()) {
                target.parentFile.mkdirs()
                URI(url).toURL().openStream().use { input -> target.outputStream().use { input.copyTo(it) } }
            }
        }
    }
}
tasks.named("preBuild") { dependsOn(downloadModels) }

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")

    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.navigation:navigation-compose:2.8.5")
    implementation("androidx.exifinterface:exifinterface:1.3.7")
    implementation("io.coil-kt:coil-compose:2.7.0")

    // Live camera preview + frame analysis
    implementation("androidx.camera:camera-camera2:1.4.1")
    implementation("androidx.camera:camera-lifecycle:1.4.1")
    implementation("androidx.camera:camera-view:1.4.1")

    // On-device recognition: OCR of stamped/printed part numbers; models run on ONNX Runtime
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.20.0")
    implementation("com.google.mlkit:text-recognition:16.0.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-play-services:1.9.0")

    // Cloud AI: photo identification and sketch -> engineering drawing
    implementation("com.anthropic:anthropic-java:2.34.0")
}
