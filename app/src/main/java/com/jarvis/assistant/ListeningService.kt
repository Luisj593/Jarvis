package com.jarvis.assistant

import android.app.*
import android.content.Intent
import android.os.*
import android.content.pm.ServiceInfo
import android.speech.*
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import java.util.Locale

class ListeningService: Service(), TextToSpeech.OnInitListener {
 companion object { const val START="jarvis.START"; const val STOP="jarvis.STOP"; const val CHANNEL="jarvis_microphone" }
 private val handler=Handler(Looper.getMainLooper())
 private var recognizer: SpeechRecognizer?=null
 private var tts:TextToSpeech?=null
 private var running=false
 private var errors=0
 private var retryPending=false
 private var lastStart=0L
 private var conversationUntil=0L
 private var speaking=false
 private var ttsReady=false
 private val pendingSpeech=StringBuilder()
 private var flushSpeech:Runnable?=null
 private var sessionActive=false
 private val pauseBeforeProcessingMs=4500L
 override fun onBind(intent:Intent?)=null
 override fun onCreate(){ super.onCreate(); tts=TextToSpeech(this,this) }
 override fun onStartCommand(intent:Intent?,flags:Int,startId:Int):Int{
  if(intent?.action==STOP){getSharedPreferences("jarvis_service",MODE_PRIVATE).edit().putBoolean("enabled",false).apply();running=false;shutdown();stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();return START_NOT_STICKY}
  if(intent?.action!=START && !getSharedPreferences("jarvis_service",MODE_PRIVATE).getBoolean("enabled",false)) {stopSelf();return START_NOT_STICKY}
  if(running)return START_STICKY
  getSharedPreferences("jarvis_service",MODE_PRIVATE).edit().putBoolean("enabled",true).apply()
  running=true
  val mgr=getSystemService(NotificationManager::class.java)
  mgr.createNotificationChannel(NotificationChannel(CHANNEL,"Micrófono de JARVIS",NotificationManager.IMPORTANCE_LOW))
  val stopIntent=PendingIntent.getService(this,1,Intent(this,ListeningService::class.java).setAction(STOP),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
  val notification=Notification.Builder(this,CHANNEL).setContentTitle("JARVIS escuchando").setContentText("Micrófono activo. Di Jarvis para hablar.").setSmallIcon(android.R.drawable.ic_btn_speak_now).setOngoing(true).addAction(Notification.Action.Builder(null,"Detener",stopIntent).build()).build()
  if(Build.VERSION.SDK_INT>=29) startForeground(1,notification,ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE) else startForeground(1,notification)
  handler.post { listen() }
  return START_STICKY
 }
 private fun listen(){
  if(!running || speaking)return
  if(!SpeechRecognizer.isRecognitionAvailable(this)){running=false;getSharedPreferences("jarvis_service",MODE_PRIVATE).edit().putBoolean("enabled",false).apply();stopSelf();return}
  retryPending=false
  recognizer?.destroy()
  recognizer=if(Build.VERSION.SDK_INT>=31 && SpeechRecognizer.isOnDeviceRecognitionAvailable(this))
   SpeechRecognizer.createOnDeviceSpeechRecognizer(this)
  else SpeechRecognizer.createSpeechRecognizer(this)
  recognizer?.setRecognitionListener(object:RecognitionListener{
   override fun onReadyForSpeech(params:Bundle?){}
   override fun onBeginningOfSpeech(){}
   override fun onRmsChanged(rmsdB:Float){}
   override fun onBufferReceived(buffer:ByteArray?){}
   override fun onEndOfSpeech(){}
   override fun onError(error:Int){
    errors++
    if(error==SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS){
     running=false;getSharedPreferences("jarvis_service",MODE_PRIVATE).edit().putBoolean("enabled",false).apply();stopSelf();return
    }
    // Avoid rapid recognizer restarts, which can produce repeated system tones.
    retry(if(error==SpeechRecognizer.ERROR_RECOGNIZER_BUSY) 3500L else minOf(15000L,2000L*minOf(errors,7)))
   }
   override fun onResults(results:Bundle?){
    errors=0
    val spoken=results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty().trim()
    val match=Regex("\\bjarvis\\b",RegexOption.IGNORE_CASE).find(spoken)
    if(match!=null || sessionActive){
     sessionActive=true
     conversationUntil=System.currentTimeMillis()+60000L
     val part=(if(match!=null)spoken.substring(match.range.last+1) else spoken).trim()
     if(part.isNotBlank()){
      if(pendingSpeech.isNotEmpty())pendingSpeech.append(' ')
      pendingSpeech.append(part)
     }
     flushSpeech?.let{handler.removeCallbacks(it)}
     val explicitEnd=Regex("(terminé|he terminado|eso es todo|ejecuta ahora)[.! ]*$",RegexOption.IGNORE_CASE).containsMatchIn(pendingSpeech.toString())
     if(explicitEnd)finishSpeech() else {
      val task=Runnable{finishSpeech()}
      flushSpeech=task
      handler.postDelayed(task,pauseBeforeProcessingMs)
      retry(900)
     }
    }else retry(1800)
   }
   override fun onPartialResults(partialResults:Bundle?){}
   override fun onEvent(eventType:Int,params:Bundle?){}
  })
  try{
   lastStart=System.currentTimeMillis()
   recognizer?.startListening(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply{
    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
    putExtra(RecognizerIntent.EXTRA_LANGUAGE,"es-DO")
    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS,false)
    putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE,packageName)
   })
  }catch(e:Exception){errors++;retry(minOf(15000L,2000L*minOf(errors,7)))}
 }
 private fun finishSpeech(){
  flushSpeech?.let{handler.removeCallbacks(it)}
  flushSpeech=null
  val phrase=pendingSpeech.toString().trim().lowercase(Locale.ROOT)
   .replace(Regex("(terminé|he terminado|eso es todo|ejecuta ahora)[.! ]*$"),"").trim()
  pendingSpeech.setLength(0)
  if(phrase.isBlank()){retry(1500);return}
  sessionActive=true
  conversationUntil=System.currentTimeMillis()+60000L
     val prefs=getSharedPreferences("jarvis_lessons",MODE_PRIVATE)
     val lessons=prefs.getStringSet("lessons",emptySet()).orEmpty()
     val answer=when {
      phrase.startsWith("recuerda que ") || phrase.startsWith("aprende que ") || phrase.startsWith("aprende:") -> {
       val lesson=phrase.substringAfter("que ",phrase.substringAfter(":","")).trim()
       if(lesson.isBlank()) "Dime qué deseas que recuerde."
       else if(lessons.size>=100) "Mi memoria local llegó al límite de cien enseñanzas."
       else { val next=lessons.toMutableSet();next.add(lesson);prefs.edit().putStringSet("lessons",next).apply(); "Entendido. Recordaré: "+lesson }
      }
      phrase.contains("qué recuerdas") || phrase.contains("que recuerdas") -> {
       if(lessons.isEmpty()) "Aún no tengo enseñanzas guardadas."
       else "Recuerdo: "+lessons.sorted().take(5).joinToString(". ")
      }
      phrase.startsWith("olvida que ") -> {
       val target=phrase.removePrefix("olvida que ").trim()
       val matching=lessons.filter { it.lowercase(Locale.ROOT).contains(target) }
       if(target.isBlank() || matching.isEmpty()) "No encontré esa enseñanza."
       else {prefs.edit().putStringSet("lessons",lessons.minus(matching.toSet())).apply();"He olvidado "+matching.size+" enseñanza."}
      }
      phrase=="terminar conversación" || phrase=="termina la conversación" -> {
       conversationUntil=0L
       "Conversación terminada. Di Jarvis para volver a hablar."
      }
      phrase=="hola" || phrase=="buenas" -> "Hola. Te escucho, ¿qué necesitas?"
      phrase.isBlank() -> "Aquí estoy. Puedes continuar hablando."
      else -> {
       val tokens=phrase.split(Regex("\\s+")).filter { it.length>3 }.toSet()
       val match=lessons.map { lesson -> lesson to lesson.lowercase(Locale.ROOT).split(Regex("\\s+")).count { it in tokens } }.maxByOrNull { it.second }
       if(match!=null && match.second>=2) "Según lo que me enseñaste: "+match.first
       else "Todavía no conozco cómo responder a eso. Dime aprende que, seguido de tu preferencia o procedimiento."
      }
     }
     recognizer?.cancel()
     if(ttsReady && tts!=null){
      speaking=true
      val result=tts?.speak(answer,TextToSpeech.QUEUE_FLUSH,null,"jarvis-reply")
      if(result==TextToSpeech.ERROR){speaking=false;retry(600)}
     } else retry(600)

 }
 private fun retry(delay:Long){
  if(!running || retryPending)return
  retryPending=true
  val sinceStart=System.currentTimeMillis()-lastStart
  val safeDelay=maxOf(delay,1200L-sinceStart)
  handler.postDelayed({retryPending=false;if(running && !speaking)listen()},safeDelay)
 }
 private fun shutdown(){speaking=false;retryPending=false;sessionActive=false;pendingSpeech.setLength(0);flushSpeech=null;handler.removeCallbacksAndMessages(null);recognizer?.cancel();recognizer?.destroy();recognizer=null;tts?.stop();tts?.shutdown();tts=null}
 override fun onInit(status:Int){
  if(status==TextToSpeech.SUCCESS){
   configureVoice()
   ttsReady=true
   tts?.setOnUtteranceProgressListener(object:UtteranceProgressListener(){
    override fun onStart(utteranceId:String?){}
    override fun onDone(utteranceId:String?){handler.post {speaking=false;retry(350)}}
    override fun onError(utteranceId:String?){handler.post {speaking=false;retry(700)}}
   })
  }
 }
 private fun configureVoice(){
  val engine=tts ?: return
  val british=getSharedPreferences("jarvis_voice",MODE_PRIVATE).getString("profile","british")=="british"
  val target=if(british) Locale.UK else Locale("es","DO")
  val available=engine.isLanguageAvailable(target)
  if(available>=TextToSpeech.LANG_AVAILABLE){
   engine.language=target
   val voices=engine.voices.orEmpty()
   val selected=voices.filter { it.locale.language==target.language && it.locale.country==target.country }
    .sortedWith(compareBy<android.speech.tts.Voice> {it.isNetworkConnectionRequired}.thenByDescending {it.quality})
    .firstOrNull()
   if(selected!=null) engine.voice=selected
  }else{
   engine.language=Locale("es","DO")
  }
  engine.setSpeechRate(if(british) 0.88f else 0.95f)
  engine.setPitch(if(british) 0.90f else 1.0f)
 }
 override fun onDestroy(){running=false;shutdown();super.onDestroy()}
}
