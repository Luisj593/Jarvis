package com.jarvis.assistant

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

class MainActivity : Activity() {
 private lateinit var status: TextView
 override fun onCreate(savedInstanceState: Bundle?) {
  super.onCreate(savedInstanceState)
  val layout=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL; setPadding(48,72,48,32) }
  status=TextView(this).apply { text="JARVIS · Escucha continua experimental\n\nActiva una vez y habla sin pulsar cada vez. Di «Jarvis» antes de tu instrucción.\n\nLa escucha puede interrumpirse por restricciones de Android."; textSize=21f }
  val start=Button(this).apply { text="Activar escucha"; setOnClickListener { activate() } }
  val stop=Button(this).apply { text="Detener micrófono"; setOnClickListener { startService(Intent(this@MainActivity,ListeningService::class.java).setAction(ListeningService.STOP)) } }
  val memory=Button(this).apply { text="Ver enseñanzas locales"; setOnClickListener { val saved=getSharedPreferences("jarvis_lessons",MODE_PRIVATE).getStringSet("lessons",emptySet()).orEmpty(); status.text=if(saved.isEmpty()) "Sin enseñanzas guardadas" else saved.joinToString("\n• ","Memoria local:\n• ") } }
  val clear=Button(this).apply { text="Borrar memoria local"; setOnClickListener { getSharedPreferences("jarvis_lessons",MODE_PRIVATE).edit().clear().apply(); status.text="Memoria local borrada" } }
  layout.addView(status); layout.addView(start); layout.addView(stop); layout.addView(memory); layout.addView(clear); setContentView(layout)
  if(Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED) requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS),12)
 }
 private fun activate(){
  if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED){requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO),11);return}
  startForegroundService(Intent(this,ListeningService::class.java).setAction(ListeningService.START))
  status.text="JARVIS activado. Di «Jarvis» para comenzar.\nUsa la notificación o el botón para detenerlo."
 }
 override fun onRequestPermissionsResult(requestCode:Int,permissions:Array<out String>,grantResults:IntArray){
  super.onRequestPermissionsResult(requestCode,permissions,grantResults)
  if(requestCode==11 && grantResults.firstOrNull()==PackageManager.PERMISSION_GRANTED) activate()
 }
}
