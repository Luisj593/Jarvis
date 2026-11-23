plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
android {
 namespace = "com.jarvis.assistant"
 compileSdk = 35
 compileOptions {
  sourceCompatibility = JavaVersion.VERSION_17
  targetCompatibility = JavaVersion.VERSION_17
 }
 defaultConfig {
  applicationId = "com.jarvis.assistant"
  minSdk = 26
  targetSdk = 35
  versionCode = 8
  versionName = "0.8"
 }
}

kotlin { jvmToolchain(17) }
