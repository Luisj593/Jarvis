package com.jarvis.assistant

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.ScrollView
import android.widget.LinearLayout
import android.widget.TextView

class MainActivity : Activity() {
 private lateinit var status: TextView
 override fun onCreate(savedInstanceState: Bundle?) {
  super.onCreate(savedInstanceState)
  val layout=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL; setPadding(48,72,48,32) }
  status=TextView(this).apply { text="JARVIS 0.4 · Memoria editable\n\nActiva una vez y habla sin pulsar cada vez. Di «Jarvis» antes de tu instrucción.\n\nLa escucha puede interrumpirse por restricciones de Android."; textSize=21f }
  val start=Button(this).apply { text="Activar escucha"; setOnClickListener { activate() } }
  val stop=Button(this).apply { text="Detener micrófono"; setOnClickListener { startService(Intent(this@MainActivity,ListeningService::class.java).setAction(ListeningService.STOP)) } }
  val memory=Button(this).apply { text="Ver enseñanzas locales"; setOnClickListener { val saved=getSharedPreferences("jarvis_lessons",MODE_PRIVATE).getStringSet("lessons",emptySet()).orEmpty(); status.text=if(saved.isEmpty()) "Sin enseñanzas guardadas" else saved.joinToString("\n• ","Memoria local:\n• ") } }
  val teach=Button(this).apply { text="Enseñar por escrito"; setOnClickListener {
   val field=EditText(this@MainActivity).apply { hint="Ejemplo: Cuando digo valida, revisa todos los módulos"; setSingleLine(false); minLines=3 }
   AlertDialog.Builder(this@MainActivity).setTitle("Nueva enseñanza").setView(field).setNegativeButton("Cancelar",null).setPositiveButton("Guardar") { _,_ ->
    val lesson=field.text.toString().trim()
    val prefs=getSharedPreferences("jarvis_lessons",MODE_PRIVATE)
    val existing=prefs.getStringSet("lessons",emptySet()).orEmpty().toMutableSet()
    when {
     lesson.isBlank() -> status.text="No se guardó: enseñanza vacía."
     lesson.length>500 -> status.text="Máximo 500 caracteres por enseñanza."
     existing.size>=100 && !existing.contains(lesson) -> status.text="Memoria llena (100 enseñanzas)."
     else -> { existing.add(lesson); prefs.edit().putStringSet("lessons",existing).apply();status.text="Enseñanza guardada en este teléfono." }
    }
   }.show()
  } }
  val editMemory=Button(this).apply { text="Editar o eliminar una enseñanza"; setOnClickListener {
   val prefs=getSharedPreferences("jarvis_lessons",MODE_PRIVATE)
   val items=prefs.getStringSet("lessons",emptySet()).orEmpty().sorted()
   if(items.isEmpty()) {status.text="Todavía no hay enseñanzas.";return@setOnClickListener}
   AlertDialog.Builder(this@MainActivity).setTitle("Selecciona una enseñanza").setItems(items.toTypedArray()) { _,position ->
    val original=items[position]
    val field=EditText(this@MainActivity).apply {setText(original);setSelection(text.length)}
    AlertDialog.Builder(this@MainActivity).setTitle("Editar enseñanza").setView(field)
     .setNegativeButton("Cancelar",null)
     .setNeutralButton("Eliminar") { _,_ ->
      AlertDialog.Builder(this@MainActivity).setTitle("Confirmar eliminación").setMessage(original)
       .setNegativeButton("Cancelar",null).setPositiveButton("Eliminar") { _,_ ->
        val updated=prefs.getStringSet("lessons",emptySet()).orEmpty().toMutableSet()
        updated.remove(original);prefs.edit().putStringSet("lessons",updated).apply();status.text="Enseñanza eliminada."
       }.show()
     }
     .setPositiveButton("Guardar") { _,_ ->
      val replacement=field.text.toString().trim()
      if(replacement.isBlank() || replacement.length>500){status.text="La enseñanza debe tener entre 1 y 500 caracteres."}
      else {val updated=prefs.getStringSet("lessons",emptySet()).orEmpty().toMutableSet();updated.remove(original);updated.add(replacement);prefs.edit().putStringSet("lessons",updated).apply();status.text="Enseñanza actualizada."}
     }.show()
   }.show()
  } }
  val clear=Button(this).apply { text="Borrar memoria local"; setOnClickListener { AlertDialog.Builder(this@MainActivity).setTitle("¿Borrar las enseñanzas?").setMessage("Esta acción eliminará toda la memoria guardada en este teléfono y no se puede deshacer.").setNegativeButton("Cancelar",null).setPositiveButton("Borrar") { _,_ -> getSharedPreferences("jarvis_lessons",MODE_PRIVATE).edit().clear().apply(); status.text="Memoria local borrada" }.show() } }
  layout.addView(status); layout.addView(start); layout.addView(stop); layout.addView(teach); layout.addView(memory); layout.addView(editMemory); layout.addView(clear); setContentView(ScrollView(this).apply { addView(layout) })
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
