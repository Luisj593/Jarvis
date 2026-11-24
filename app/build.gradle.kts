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
  versionCode = 13
  versionName = "1.3"
 }
}

kotlin { jvmToolchain(17) }

dependencies {
 testImplementation("junit:junit:4.13.2")
 implementation("com.alphacephei:vosk-android:0.3.47")
 implementation("net.java.dev.jna:jna:5.13.0@aar")
}
