package com.jarvis.assistant

import android.app.*
import android.content.Intent
import android.os.*
import android.content.pm.ServiceInfo
import android.speech.*
import android.speech.tts.TextToSpeech
import java.util.Locale

class ListeningService: Service(), TextToSpeech.OnInitListener {
 companion object { const val START="jarvis.START"; const val STOP="jarvis.STOP"; const val CHANNEL="jarvis_microphone" }
 private val handler=Handler(Looper.getMainLooper())
 private var recognizer: SpeechRecognizer?=null
 private var tts:TextToSpeech?=null
 private var running=false
 private var errors=0
 override fun onBind(intent:Intent?)=null
 override fun onCreate(){ super.onCreate(); tts=TextToSpeech(this,this) }
 override fun onStartCommand(intent:Intent?,flags:Int,startId:Int):Int{
  if(intent?.action==STOP){running=false;shutdown();stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();return START_NOT_STICKY}
  if(running)return START_NOT_STICKY
  running=true
  val mgr=getSystemService(NotificationManager::class.java)
  mgr.createNotificationChannel(NotificationChannel(CHANNEL,"Micrófono de JARVIS",NotificationManager.IMPORTANCE_LOW))
  val stopIntent=PendingIntent.getService(this,1,Intent(this,ListeningService::class.java).setAction(STOP),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
  val notification=Notification.Builder(this,CHANNEL).setContentTitle("JARVIS escuchando").setContentText("Micrófono activo. Di Jarvis para hablar.").setSmallIcon(android.R.drawable.ic_btn_speak_now).setOngoing(true).addAction(Notification.Action.Builder(null,"Detener",stopIntent).build()).build()
  if(Build.VERSION.SDK_INT>=29) startForeground(1,notification,ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE) else startForeground(1,notification)
  handler.post { listen() }
  return START_NOT_STICKY
 }
 private fun listen(){
  if(!running)return
  if(!SpeechRecognizer.isRecognitionAvailable(this)){running=false;stopSelf();return}
  recognizer?.destroy()
  recognizer=SpeechRecognizer.createSpeechRecognizer(this)
  recognizer?.setRecognitionListener(object:RecognitionListener{
   override fun onReadyForSpeech(params:Bundle?){}
   override fun onBeginningOfSpeech(){}
   override fun onRmsChanged(rmsdB:Float){}
   override fun onBufferReceived(buffer:ByteArray?){}
   override fun onEndOfSpeech(){}
   override fun onError(error:Int){errors++; if(error==SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS || errors>=12){running=false;stopSelf();return};retry(if(error==SpeechRecognizer.ERROR_RECOGNIZER_BUSY)1500 else 700)}
   override fun onResults(results:Bundle?){
    errors=0
    val spoken=results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()
    if(spoken.contains("jarvis",ignoreCase=true)){
     // Prototipo: respuesta local. No se graba ni transmite audio a nuestro servidor.
     val phrase=spoken.lowercase(Locale.ROOT).substringAfter("jarvis").trim()
     val prefs=getSharedPreferences("jarvis_lessons",MODE_PRIVATE)
     val answer=when {
      phrase.startsWith("recuerda que ") -> {
       val lesson=spoken.substringAfter("recuerda que ",missingDelimiterValue="").trim()
       if(lesson.isNotBlank()) {
        val existing=prefs.getStringSet("lessons",emptySet()).orEmpty().toMutableSet()
        if(existing.size>=50) "Mi memoria local está llena. Borra las enseñanzas desde la aplicación."
        else { existing.add(lesson); prefs.edit().putStringSet("lessons",existing).apply(); "He guardado esa enseñanza en este teléfono." }
       } else "Di Jarvis recuerda que, y lo que deseas enseñarme."
      }
      phrase.contains("qué recuerdas") || phrase.contains("que recuerdas") -> {
       val lessons=prefs.getStringSet("lessons",emptySet()).orEmpty()
       if(lessons.isEmpty()) "Todavía no me has enseñado nada."
       else "Recuerdo: "+lessons.take(3).joinToString(". ")
      }
      else -> "Te escucho. Puedes decir Jarvis recuerda que, para enseñarme algo."
     }
     tts?.speak(answer,TextToSpeech.QUEUE_FLUSH,null,"jarvis-reply")
     retry(3000)
    } else retry(350)
   }
   override fun onPartialResults(partialResults:Bundle?){}
   override fun onEvent(eventType:Int,params:Bundle?){}
  })
  try{
   recognizer?.startListening(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply{
    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
    putExtra(RecognizerIntent.EXTRA_LANGUAGE,"es-DO")
    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS,false)
   })
  }catch(e:Exception){errors++;if(errors<12)retry(2000) else stopSelf()}
 }
 private fun retry(delay:Long){handler.postDelayed({if(running)listen()},delay)}
 private fun shutdown(){handler.removeCallbacksAndMessages(null);recognizer?.cancel();recognizer?.destroy();recognizer=null;tts?.stop();tts?.shutdown();tts=null}
 override fun onInit(status:Int){if(status==TextToSpeech.SUCCESS)tts?.language=Locale("es","DO")}
 override fun onDestroy(){running=false;shutdown();super.onDestroy()}
}
