package com.jarvis.assistant

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.*
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.net.Uri
import android.view.Gravity
import android.view.View
import android.widget.*
import java.util.Locale

/** Interfaz futurista nativa; no necesita conexión ni assets externos. */
class MainActivity : Activity() {
 private val navy=Color.rgb(3,10,30)
 private val cyan=Color.rgb(0,220,255)
 private val violet=Color.rgb(159,65,255)
 private lateinit var status:TextView
 private fun dp(v:Int)=(v*resources.displayMetrics.density).toInt()
 private fun rounded(stroke:Int=cyan):GradientDrawable =
  GradientDrawable(GradientDrawable.Orientation.TL_BR,intArrayOf(Color.rgb(10,37,82),Color.rgb(10,12,45))).apply {
   cornerRadius=dp(21).toFloat();setStroke(dp(1),stroke)
  }
 private fun text(value:String,size:Float,color:Int=Color.WHITE):TextView =
  TextView(this).apply { text=value;textSize=size;setTextColor(color);gravity=Gravity.CENTER }
 private fun card(label:String,icon:String,onClick:()->Unit):TextView =
  text("$icon   $label",16f).apply {
   gravity=Gravity.CENTER_VERTICAL;setPadding(dp(22),0,dp(14),0)
   background=rounded();setOnClickListener {onClick()}
   layoutParams=LinearLayout.LayoutParams(-1,dp(64)).apply {bottomMargin=dp(11)}
  }
 override fun onCreate(savedInstanceState:Bundle?){
  super.onCreate(savedInstanceState)
  window.statusBarColor=navy;window.navigationBarColor=navy
  val root=LinearLayout(this).apply {
   orientation=LinearLayout.VERTICAL;setBackgroundColor(navy)
   setPadding(dp(18),dp(16),dp(18),dp(18))
  }
  val header=text("J A R V I S",36f,cyan).apply {setTypeface(null,1)}
  root.addView(header)
  root.addView(text("TU ASISTENTE VIRTUAL",13f,Color.rgb(190,215,255)))
  val orb=OrbView()
  root.addView(orb,LinearLayout.LayoutParams(-1,dp(260)).apply {topMargin=dp(10)})
  status=text("¿En qué puedo ayudarte?",19f).apply {
   setPadding(dp(8),dp(4),dp(8),dp(16))
  }
  root.addView(status)
  val start=card("Hey Jarvis · Activar micrófono","🎙") { activate() }
  root.addView(start)
  val stop=card("Detener escucha","■") {
   startService(Intent(this,ListeningService::class.java).setAction(ListeningService.STOP))
   status.text="Micrófono detenido"
  }
  root.addView(stop)
  root.addView(card("Configurar voz de JARVIS","♫") {
   val profiles=arrayOf("Británica · estilo asistente","Español · pronunciación natural")
   val prefs=getSharedPreferences("jarvis_voice",MODE_PRIVATE)
   val selected=if(prefs.getString("profile","british")=="british") 0 else 1
   AlertDialog.Builder(this).setTitle("Voz de JARVIS")
    .setSingleChoiceItems(profiles,selected){dialog,which->
     prefs.edit().putString("profile",if(which==0)"british" else "spanish").apply()
     status.text="Voz actualizada. Detén y vuelve a activar el micrófono para aplicarla."
     dialog.dismiss()
    }.setNegativeButton("Cancelar",null).show()
  })
  root.addView(card("Configurar batería en segundo plano","◉") {
   AlertDialog.Builder(this).setTitle("Permitir actividad en segundo plano")
    .setMessage("Para mejorar la continuidad de JARVIS, configura la batería de la aplicación como Sin restricciones, si tu teléfono ofrece esa opción. Android puede interrumpir el micrófono incluso con este ajuste. JARVIS no se activará automáticamente tras reiniciar el teléfono.")
    .setNegativeButton("Cancelar",null)
    .setPositiveButton("Abrir ajustes"){_,_->
     startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,Uri.parse("package:$packageName")))
    }.show()
  })
  root.addView(card("Gestiona tus proyectos","✦") {
   showInfo("Proyectos","El núcleo de proyectos está disponible en la API protegida de JARVIS. La sincronización móvil requiere autenticación adicional.")
  })
  root.addView(card("Organiza tu agenda","▦") {
   showInfo("Agenda","La integración con el calendario del dispositivo está pendiente. No se ha creado ninguna cita.")
  })
  root.addView(card("Analiza tu información","▥") { showLessons() })
  root.addView(card("Automatiza tareas","⚙") {
   showInfo("Automatizaciones","Las acciones externas todavía no están habilitadas. El núcleo requiere permisos y confirmación.")
  })
  root.addView(card("Te da recomendaciones","✧") {
   showInfo("Recomendaciones","JARVIS utiliza reglas y enseñanzas explícitas, sin modelos externos de IA.")
  })
  root.addView(card("Enseñar a JARVIS","＋") {teach()})
  root.addView(card("Editar memoria","✎") {editMemory()})
  root.addView(card("Borrar memoria local","×") {clearMemory()})
  val scroll=ScrollView(this).apply {isFillViewport=true;addView(root)}
  setContentView(scroll)
  if(Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)
   requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS),12)
 }
 private fun showInfo(title:String,message:String){
  AlertDialog.Builder(this).setTitle(title).setMessage(message).setPositiveButton("Entendido",null).show()
 }
 private fun showLessons(){
  val lessons=getSharedPreferences("jarvis_lessons",MODE_PRIVATE).getStringSet("lessons",emptySet()).orEmpty()
  showInfo("Memoria local",if(lessons.isEmpty()) "No hay enseñanzas guardadas." else lessons.sorted().joinToString("\n• ","• "))
 }
 private fun teach(){
  val field=EditText(this).apply {hint="Ejemplo: Cuando diga valida, revisa todos los módulos";minLines=3}
  AlertDialog.Builder(this).setTitle("Nueva enseñanza").setView(field).setNegativeButton("Cancelar",null).setPositiveButton("Guardar"){_,_->
   val lesson=field.text.toString().trim()
   val prefs=getSharedPreferences("jarvis_lessons",MODE_PRIVATE)
   val existing=prefs.getStringSet("lessons",emptySet()).orEmpty().toMutableSet()
   status.text=when{
    lesson.isBlank()->"La enseñanza está vacía."
    lesson.length>500->"Máximo 500 caracteres."
    existing.size>=100 && !existing.contains(lesson)->"Memoria llena (100 enseñanzas)."
    else->{existing.add(lesson);prefs.edit().putStringSet("lessons",existing).apply();"Enseñanza guardada en el teléfono."}
   }
  }.show()
 }
 private fun editMemory(){
  val prefs=getSharedPreferences("jarvis_lessons",MODE_PRIVATE)
  val items=prefs.getStringSet("lessons",emptySet()).orEmpty().sorted()
  if(items.isEmpty()){showInfo("Memoria","No hay enseñanzas.");return}
  AlertDialog.Builder(this).setTitle("Selecciona una enseñanza").setItems(items.toTypedArray()){_,index->
   val original=items[index]
   val field=EditText(this).apply {setText(original)}
   AlertDialog.Builder(this).setTitle("Editar enseñanza").setView(field).setNegativeButton("Cancelar",null)
    .setNeutralButton("Eliminar"){_,_->
     AlertDialog.Builder(this).setTitle("Confirmar eliminación").setMessage(original).setNegativeButton("Cancelar",null)
      .setPositiveButton("Eliminar"){_,_->
       val updated=prefs.getStringSet("lessons",emptySet()).orEmpty().toMutableSet()
       updated.remove(original);prefs.edit().putStringSet("lessons",updated).apply();status.text="Enseñanza eliminada."
      }.show()
    }.setPositiveButton("Guardar"){_,_->
     val replacement=field.text.toString().trim()
     if(replacement.isBlank() || replacement.length>500){status.text="Entre 1 y 500 caracteres."}
     else{
      val updated=prefs.getStringSet("lessons",emptySet()).orEmpty().toMutableSet()
      updated.remove(original);updated.add(replacement)
      prefs.edit().putStringSet("lessons",updated).apply();status.text="Enseñanza actualizada."
     }
    }.show()
  }.show()
 }
 private fun clearMemory(){
  AlertDialog.Builder(this).setTitle("Borrar memoria local").setMessage("Se eliminarán todas las enseñanzas guardadas en este teléfono.")
   .setNegativeButton("Cancelar",null).setPositiveButton("Borrar"){_,_->
    getSharedPreferences("jarvis_lessons",MODE_PRIVATE).edit().clear().apply()
    status.text="Memoria local borrada"
   }.show()
 }
 private fun activate(){
  if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED){
   requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO),11);return
  }
  startForegroundService(Intent(this,ListeningService::class.java).setAction(ListeningService.START))
  status.text="JARVIS escuchando · Di «Jarvis»"
 }
 override fun onRequestPermissionsResult(requestCode:Int,permissions:Array<out String>,grantResults:IntArray){
  super.onRequestPermissionsResult(requestCode,permissions,grantResults)
  if(requestCode==11 && grantResults.firstOrNull()==PackageManager.PERMISSION_GRANTED)activate()
 }
 inner class OrbView:View(this){
  private val paint=Paint(Paint.ANTI_ALIAS_FLAG)
  override fun onDraw(canvas:Canvas){
   super.onDraw(canvas)
   val cx=width/2f;val cy=height/2f;val r=minOf(width,height)*0.37f
   paint.style=Paint.Style.FILL
   paint.shader=RadialGradient(cx,cy,r*1.4f,intArrayOf(Color.argb(100,0,150,255),Color.argb(40,140,40,255),Color.TRANSPARENT),null,Shader.TileMode.CLAMP)
   canvas.drawCircle(cx,cy,r*1.4f,paint);paint.shader=null
   paint.style=Paint.Style.STROKE;paint.strokeWidth=dp(5).toFloat()
   paint.shader=SweepGradient(cx,cy,intArrayOf(cyan,violet,Color.rgb(20,75,250),cyan),null)
   canvas.drawCircle(cx,cy,r,paint)
   paint.strokeWidth=dp(2).toFloat();canvas.drawCircle(cx,cy,r*1.13f,paint)
   paint.shader=null
   paint.style=Paint.Style.FILL
   paint.shader=RadialGradient(cx-r*.2f,cy-r*.3f,r*1.4f,intArrayOf(Color.rgb(17,68,135),Color.rgb(2,7,35)),null,Shader.TileMode.CLAMP)
   canvas.drawCircle(cx,cy,r*.91f,paint);paint.shader=null
   val bars=floatArrayOf(.22f,.43f,.7f,.42f,.95f,.55f,.32f)
   paint.color=cyan;paint.strokeWidth=dp(7).toFloat();paint.strokeCap=Paint.Cap.ROUND
   val gap=r*.23f
   for(i in bars.indices){
    val x=cx+(i-3)*gap;val half=r*.52f*bars[i]
    canvas.drawLine(x,cy-half,x,cy+half,paint)
   }
   paint.strokeCap=Paint.Cap.BUTT
  }
 }
}
