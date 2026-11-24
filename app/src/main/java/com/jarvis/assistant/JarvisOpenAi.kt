package com.jarvis.assistant

import android.content.Context
import android.util.Base64
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Development-only OpenAI bridge client. Never embeds API keys in the APK. */
class JarvisOpenAi(private val context:Context) {
 companion object {
  private const val BASE="https://jarvis-openai-bridge-test-development.up.railway.app"
  private const val ALIAS="jarvis_bridge_device_key_v1"
 }
 private val prefs=context.getSharedPreferences("jarvis_bridge",Context.MODE_PRIVATE)
 private fun key():SecretKey {
  val store=KeyStore.getInstance("AndroidKeyStore").apply {load(null)}
  (store.getKey(ALIAS,null) as? SecretKey)?.let{return it}
  val generator=KeyGenerator.getInstance("AES","AndroidKeyStore")
  generator.init(android.security.keystore.KeyGenParameterSpec.Builder(ALIAS,
   android.security.keystore.KeyProperties.PURPOSE_ENCRYPT or android.security.keystore.KeyProperties.PURPOSE_DECRYPT)
   .setBlockModes(android.security.keystore.KeyProperties.BLOCK_MODE_GCM)
   .setEncryptionPaddings(android.security.keystore.KeyProperties.ENCRYPTION_PADDING_NONE).build())
  return generator.generateKey()
 }
 fun configured()=prefs.contains("token")
 fun clear(){prefs.edit().clear().apply()}
 fun saveToken(value:String){
  require(value.length in 24..512 && value.none {it.isWhitespace()}){"Token inválido"}
  val cipher=Cipher.getInstance("AES/GCM/NoPadding")
  cipher.init(Cipher.ENCRYPT_MODE,key())
  prefs.edit().putString("iv",Base64.encodeToString(cipher.iv,Base64.NO_WRAP))
   .putString("token",Base64.encodeToString(cipher.doFinal(value.toByteArray(StandardCharsets.UTF_8)),Base64.NO_WRAP)).apply()
 }
 private fun token():String {
  val cipher=Cipher.getInstance("AES/GCM/NoPadding")
  cipher.init(Cipher.DECRYPT_MODE,key(),GCMParameterSpec(128,Base64.decode(prefs.getString("iv",null) ?: error("Sin token"),Base64.NO_WRAP)))
  return String(cipher.doFinal(Base64.decode(prefs.getString("token",null) ?: error("Sin token"),Base64.NO_WRAP)),StandardCharsets.UTF_8)
 }
 fun transcribe(wav:ByteArray):String {
  val conn=URL("$BASE/v1/transcribe").openConnection() as HttpURLConnection
  try {
   conn.requestMethod="POST";conn.connectTimeout=10000;conn.readTimeout=35000;conn.doOutput=true;conn.instanceFollowRedirects=false
   conn.setRequestProperty("Authorization","Bearer "+token())
   conn.setRequestProperty("Content-Type","audio/wav")
   conn.setFixedLengthStreamingMode(wav.size)
   conn.outputStream.use {it.write(wav)}
   val status=conn.responseCode
   if(status !in 200..299) error("Transcripción HTTP $status")
   return JSONObject(conn.inputStream.bufferedReader().use {it.readText()}).optString("text")
  } finally {conn.disconnect()}
 }
 fun ask(project:String,instruction:String, history:String=""):String {
  require(project.length<=120 && instruction.isNotBlank() && instruction.length<=8000)
  val conn=URL("$BASE/v1/command").openConnection() as HttpURLConnection
  try {
   conn.requestMethod="POST";conn.connectTimeout=10000;conn.readTimeout=35000
   conn.instanceFollowRedirects=false;conn.doOutput=true
   conn.setRequestProperty("Authorization","Bearer "+token())
   conn.setRequestProperty("Content-Type","application/json; charset=utf-8")
   val data=JSONObject().put("project",project).put("instruction",instruction).put("history",history.takeLast(4000)).toString()
   conn.outputStream.use {it.write(data.toByteArray(StandardCharsets.UTF_8))}
   val status=conn.responseCode
   val response=(if(status in 200..299)conn.inputStream else conn.errorStream)
    ?.bufferedReader(StandardCharsets.UTF_8)?.use {it.readText().take(65536)} ?: "{}"
   if(status !in 200..299) throw IllegalStateException("Puente OpenAI HTTP $status")
   return JSONObject(response).optString("answer","Sin respuesta de OpenAI")
  } finally {conn.disconnect()}
 }
}
