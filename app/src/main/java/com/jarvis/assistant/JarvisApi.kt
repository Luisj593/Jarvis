package com.jarvis.assistant

import android.content.Context
import android.util.Base64
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import java.security.KeyStore

/** Cliente HTTPS con token cifrado en Android Keystore; no registra credenciales. */
class JarvisApi(private val context: Context) {
 companion object {
  const val BASE = "https://jarvis-api-development.up.railway.app"
  private const val ALIAS = "jarvis_api_token_v1"
 }
 private val prefs=context.getSharedPreferences("jarvis_api",Context.MODE_PRIVATE)
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
 fun saveToken(token:String){
  require(token.length in 16..512 && token.none {it.isWhitespace()}){"Token inválido"}
  val cipher=Cipher.getInstance("AES/GCM/NoPadding")
  cipher.init(Cipher.ENCRYPT_MODE,key())
  val encrypted=cipher.doFinal(token.toByteArray(StandardCharsets.UTF_8))
  prefs.edit().putString("iv",Base64.encodeToString(cipher.iv,Base64.NO_WRAP))
   .putString("token",Base64.encodeToString(encrypted,Base64.NO_WRAP)).apply()
 }
 fun clearToken(){prefs.edit().remove("iv").remove("token").apply()}
 fun configured()=prefs.contains("token")
 private fun token():String {
  val iv=Base64.decode(prefs.getString("iv",null) ?: error("Configura el token"),Base64.NO_WRAP)
  val data=Base64.decode(prefs.getString("token",null) ?: error("Configura el token"),Base64.NO_WRAP)
  val cipher=Cipher.getInstance("AES/GCM/NoPadding")
  cipher.init(Cipher.DECRYPT_MODE,key(),GCMParameterSpec(128,iv))
  return String(cipher.doFinal(data),StandardCharsets.UTF_8)
 }
 fun request(path:String,body:JSONObject?=null):JSONObject {
  require(path.matches(Regex("^/v1/core/[a-zA-Z0-9/_-]{1,120}$"))){"Ruta inválida"}
  val conn=URL(BASE+path).openConnection() as HttpURLConnection
  try {
   conn.connectTimeout=8000;conn.readTimeout=10000
   conn.instanceFollowRedirects=false
   conn.setRequestProperty("Authorization","Bearer "+token())
   conn.setRequestProperty("Accept","application/json")
   if(body!=null){
    conn.requestMethod="POST";conn.doOutput=true
    conn.setRequestProperty("Content-Type","application/json; charset=utf-8")
    conn.outputStream.use {it.write(body.toString().toByteArray(StandardCharsets.UTF_8))}
   }
   val status=conn.responseCode
   val input=if(status in 200..299)conn.inputStream else conn.errorStream
   val response=input?.bufferedReader(StandardCharsets.UTF_8)?.use {it.readText().take(65536)} ?: "{}"
   if(status !in 200..299) throw IllegalStateException("Servidor HTTP $status")
   return JSONObject(response)
  } finally {conn.disconnect()}
 }
}
