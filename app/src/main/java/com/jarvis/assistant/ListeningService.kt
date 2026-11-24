package com.jarvis.assistant

import android.app.*
import android.content.Intent
import android.os.*
import android.content.pm.ServiceInfo
import android.speech.*
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import java.util.Locale
import kotlin.concurrent.thread

class ListeningService: Service(), TextToSpeech.OnInitListener {
 companion object { const val START="jarvis.START"; const val STOP="jarvis.STOP"; const val CHANNEL="jarvis_microphone" }
 private val handler=Handler(Looper.getMainLooper())
 private var recognizer: SpeechRecognizer?=null
 private var tts:TextToSpeech?=null
 private var running=false
 private var errors=0
 private var useDeviceRecognition=true
 private var retryPending=false
 private var lastStart=0L
 private var conversationUntil=0L
 private var speaking=false
 private var ttsReady=false
 private val pendingSpeech=StringBuilder()
 private var flushSpeech:Runnable?=null
 private var sessionActive=false
 private val pauseBeforeProcessingMs=2400L
 private var speechInProgress=false
 private var generation=0
 private var pendingReply:String?=null
 private var history=""
 private var utterance=0
 private var flushDeadline=0L
 private fun report(message:String){ android.util.Log.i("JarvisVoice",message); getSystemService(NotificationManager::class.java).notify(1,Notification.Builder(this,CHANNEL).setContentTitle("JARVIS").setContentText(message).setSmallIcon(android.R.drawable.ic_btn_speak_now).setOngoing(true).build()) }
 override fun onBind(intent:Intent?)=null
 override fun onCreate(){ super.onCreate(); tts=TextToSpeech(this,this) }
 override fun onStartCommand(intent:Intent?,flags:Int,startId:Int):Int{
  if(intent?.action==STOP){getSharedPreferences("jarvis_service",MODE_PRIVATE).edit().putBoolean("enabled",false).apply();running=false;shutdown();stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();return START_NOT_STICKY}
  if(intent?.action!=START && !getSharedPreferences("jarvis_service",MODE_PRIVATE).getBoolean("enabled",false)) {stopSelf();return START_NOT_STICKY}
  if(running)return START_STICKY
  getSharedPreferences("jarvis_service",MODE_PRIVATE).edit().putBoolean("enabled",true).apply()
  running=true
  sessionActive=true
  conversationUntil=System.currentTimeMillis()+180000L
  val mgr=getSystemService(NotificationManager::class.java)
  mgr.createNotificationChannel(NotificationChannel(CHANNEL,"Micrófono de JARVIS",NotificationManager.IMPORTANCE_LOW))
  val stopIntent=PendingIntent.getService(this,1,Intent(this,ListeningService::class.java).setAction(STOP),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
  val notification=Notification.Builder(this,CHANNEL).setContentTitle("JARVIS escuchando").setContentText("Conversación activa: el audio de voz se envía al servidor.").setSmallIcon(android.R.drawable.ic_btn_speak_now).setOngoing(true).addAction(Notification.Action.Builder(null,"Detener",stopIntent).build()).build()
  if(Build.VERSION.SDK_INT>=29) startForeground(1,notification,ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE) else startForeground(1,notification)
  handler.post { listen() }
  return START_STICKY
 }
 private var capture:SilentAudioCapture?=null
 private fun listen(){
  if(!running || speaking || capture!=null)return
  retryPending=false
  if(!sessionActive || System.currentTimeMillis()>=conversationUntil){
   sessionActive=false
   report("Conversación cerrada. Activa el micrófono desde JARVIS.")
   getSharedPreferences("jarvis_service",MODE_PRIVATE).edit().putBoolean("enabled",false).apply()
   stopSelf();return
  }
  if(!JarvisOpenAi(this).configured()){report("Configura el token del puente en JARVIS");stopSelf();return}
  val current=++generation
  val engine=SilentAudioCapture()
  capture=engine
  report("Escuchando conversación")
  thread {
   var audio:ByteArray?=null
   var failure:Exception?=null
   engine.capture({audio=it},{failure=it})
   val wav=audio
   val spoken=if(wav!=null)try{JarvisOpenAi(this).transcribe(wav)}catch(e:Exception){failure=e;null}else null
   handler.post {
    if(current==generation && running){
     capture=null
     if(failure!=null){report("Error de audio: "+(failure?.message?:"desconocido").take(100));retry(3000)}
     else if(!spoken.isNullOrBlank()){
      val phrase=spoken.trim().replace(Regex("^\\s*(?:hey\\s+)?(?:jarvis|yarvis|yárvis)[,.:! ]*",RegexOption.IGNORE_CASE),"").trim()
      conversationUntil=System.currentTimeMillis()+180000L
      if(phrase.isBlank())say("Te escucho.") else {pendingSpeech.append(phrase);finishSpeech()}
     }else retry(300)
    }
   }
  }
  handler.postDelayed({if(current==generation && capture===engine && System.currentTimeMillis()>=conversationUntil)engine.stop()},180000L)
 }
 private fun finishSpeech(){
  if(!running || speaking)return
  if(speechInProgress){flushDeadline=SystemClock.elapsedRealtime()+pauseBeforeProcessingMs;flushSpeech?.let{handler.postDelayed(it,pauseBeforeProcessingMs)};return}
  flushSpeech?.let{handler.removeCallbacks(it)}
  flushSpeech=null
  val phrase=pendingSpeech.toString().trim()
   .replace(Regex("(terminé|he terminado|eso es todo|ejecuta ahora)[.! ]*$"),"").trim()
  pendingSpeech.setLength(0)
  if(phrase.isBlank()){retry(1500);return}
  sessionActive=true
  conversationUntil=System.currentTimeMillis()+180000L
     val prefs=getSharedPreferences("jarvis_lessons",MODE_PRIVATE)
     val lessons=prefs.getStringSet("lessons",emptySet()).orEmpty()
     val normalized=phrase.lowercase(Locale.ROOT)
     val answer=when {
      normalized.startsWith("recuerda que ") || normalized.startsWith("aprende que ") || normalized.startsWith("aprende:") -> {
       val lesson=phrase.substringAfter("que ",phrase.substringAfter(":","")).trim()
       if(lesson.isBlank()) "Dime qué deseas que recuerde."
       else if(lessons.size>=100) "Mi memoria local llegó al límite de cien enseñanzas."
       else { val next=lessons.toMutableSet();next.add(lesson);prefs.edit().putStringSet("lessons",next).apply(); "Entendido. Recordaré: "+lesson }
      }
      normalized.contains("qué recuerdas") || normalized.contains("que recuerdas") -> {
       if(lessons.isEmpty()) "Aún no tengo enseñanzas guardadas."
       else "Recuerdo: "+lessons.sorted().take(5).joinToString(". ")
      }
      normalized.startsWith("olvida que ") -> {
       val target=phrase.removePrefix("olvida que ").trim()
       val matching=lessons.filter { it.lowercase(Locale.ROOT).contains(target) }
       if(target.isBlank() || matching.isEmpty()) "No encontré esa enseñanza."
       else {prefs.edit().putStringSet("lessons",lessons.minus(matching.toSet())).apply();"He olvidado "+matching.size+" enseñanza."}
      }
      normalized=="terminar conversación" || normalized=="termina la conversación" -> {
       sessionActive=false;conversationUntil=0L;history=""
       "Conversación terminada. Activa el micrófono para volver a hablar."
      }
      normalized=="hola" || normalized=="buenas" -> "Hola. Te escucho, ¿qué necesitas?"
      phrase.isBlank() -> "Aquí estoy. Puedes continuar hablando."
      else -> {
       val tokens=phrase.split(Regex("\\s+")).filter { it.length>3 }.toSet()
       val match=lessons.map { lesson -> lesson to lesson.lowercase(Locale.ROOT).split(Regex("\\s+")).count { it in tokens } }.maxByOrNull { it.second }
       if(JarvisOpenAi(this).configured()) null
       else if(match!=null && match.second>=2) "Según lo que me enseñaste: "+match.first
       else "Todavía no tengo la conexión OpenAI configurada. Configúrala en la aplicación para analizar solicitudes abiertas."
      }
     }
     speaking=true
     generation++
     handler.removeCallbacksAndMessages(null)
     retryPending=false
     recognizer?.cancel()
     if(answer==null){
      speaking=true
      thread {
       val previous=history
       val reply=try {JarvisOpenAi(this).ask("JARVIS",phrase,previous)}
        catch(e:Exception){val detail=e.message.orEmpty();when {detail.contains("401")->"El token del puente no es válido. Configúralo en JARVIS.";detail.contains("503")->"El servidor no tiene configurada la clave de OpenAI.";detail.contains("502")->"El servidor no pudo obtener una respuesta de OpenAI.";else->"No pude conectar con el servidor. Revisa la conexión y la configuración del puente."}}
       handler.post {if(running){history=(previous+"\nUsuario: "+phrase+"\nJARVIS: "+reply).takeLast(4000);say(reply)}}
      }
      return
     }
     say(answer)
 }
 private fun say(answer:String){
     report("Respondiendo por voz")
     if(ttsReady && tts!=null){
      speaking=true
      val id=++utterance
      val result=tts?.speak(answer,TextToSpeech.QUEUE_FLUSH,null,"jarvis-$id")
      if(result==TextToSpeech.ERROR){speaking=false;report("Error de voz: revisa el motor de síntesis");retry(600)} else handler.postDelayed({if(speaking && id==utterance){speaking=false;retry(700)}},maxOf(30000L,answer.length*150L))
     } else {pendingReply=answer; speaking=false; report("Motor de voz no disponible; revisa síntesis de voz");retry(600)}
 }
 private fun retry(delay:Long){
  if(!running || retryPending)return
  retryPending=true
  val sinceStart=System.currentTimeMillis()-lastStart
  val safeDelay=maxOf(delay,1200L-sinceStart)
  handler.postDelayed({retryPending=false;if(running && !speaking)listen()},safeDelay)
 }
 private fun shutdown(){capture?.stop();capture=null;generation++;speaking=false;retryPending=false;sessionActive=false;pendingSpeech.setLength(0);flushSpeech=null;handler.removeCallbacksAndMessages(null);recognizer?.cancel();recognizer?.destroy();recognizer=null;tts?.stop();tts?.shutdown();tts=null}
 override fun onInit(status:Int){
  if(status==TextToSpeech.SUCCESS){
   configureVoice()
   ttsReady=true
   tts?.setOnUtteranceProgressListener(object:UtteranceProgressListener(){
    override fun onStart(utteranceId:String?){}
    override fun onDone(utteranceId:String?){handler.post {if(utteranceId=="jarvis-$utterance"){speaking=false;if(sessionActive)conversationUntil=System.currentTimeMillis()+180000L;retry(350)}}}
    override fun onError(utteranceId:String?){handler.post {if(utteranceId=="jarvis-$utterance"){speaking=false;retry(700)}}}
   })
   pendingReply?.let{pendingReply=null;say(it)}
  } else if(running) report("No se pudo iniciar el motor de voz")
 }
 private fun configureVoice(){
  val engine=tts ?: return
  val british=false
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
   engine.language=Locale("es","ES")
  }
  engine.setSpeechRate(if(british) 0.88f else 0.95f)
  engine.setPitch(if(british) 0.90f else 1.0f)
 }
 override fun onDestroy(){running=false;shutdown();super.onDestroy()}
}
