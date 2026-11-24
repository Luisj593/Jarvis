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
 private var selectedProject=""
 private var utterance=0
 private var flushDeadline=0L
 private fun report(message:String){ getSharedPreferences("jarvis_status",MODE_PRIVATE).edit().putString("state",message).apply(); android.util.Log.i("JarvisVoice",message); getSystemService(NotificationManager::class.java).notify(1,Notification.Builder(this,CHANNEL).setContentTitle("JARVIS").setContentText(message).setSmallIcon(android.R.drawable.ic_btn_speak_now).setOngoing(true).setOnlyAlertOnce(true).addAction(Notification.Action.Builder(null,"Detener",PendingIntent.getService(this,1,Intent(this,ListeningService::class.java).setAction(STOP),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)).build()).build()) }
 override fun onBind(intent:Intent?)=null
 override fun onCreate(){ super.onCreate(); tts=TextToSpeech(this,this) }
 override fun onStartCommand(intent:Intent?,flags:Int,startId:Int):Int{
  if(intent?.action==STOP){getSharedPreferences("jarvis_service",MODE_PRIVATE).edit().putBoolean("enabled",false).apply();running=false;shutdown();stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();return START_NOT_STICKY}
  if(intent?.action!=START && !getSharedPreferences("jarvis_service",MODE_PRIVATE).getBoolean("enabled",false)) {stopSelf();return START_NOT_STICKY}
  if(running)return START_STICKY
  getSharedPreferences("jarvis_service",MODE_PRIVATE).edit().putBoolean("enabled",true).apply()
  running=true
  localFallback=false
  sessionActive=false
  conversationUntil=System.currentTimeMillis()+180000L
  val mgr=getSystemService(NotificationManager::class.java)
  mgr.createNotificationChannel(NotificationChannel(CHANNEL,"Micrófono de JARVIS",NotificationManager.IMPORTANCE_LOW))
  val stopIntent=PendingIntent.getService(this,1,Intent(this,ListeningService::class.java).setAction(STOP),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
  val notification=Notification.Builder(this,CHANNEL).setContentTitle("JARVIS escuchando").setContentText("Micrófono activo. Di Jarvis para hablar.").setSmallIcon(android.R.drawable.ic_btn_speak_now).setOngoing(true).addAction(Notification.Action.Builder(null,"Detener",stopIntent).build()).build()
  if(Build.VERSION.SDK_INT>=29) startForeground(1,notification,ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE) else startForeground(1,notification)
  handler.post { listen() }
  return START_STICKY
 }
 private var offlineModel:org.vosk.Model?=null
 private var offlineSpeech:org.vosk.android.SpeechService?=null
 private var offlineRecognizer:org.vosk.Recognizer?=null
 private var lastPartial=""
 private var offlineDraft=""
 private var offlineLoading=false
 private var offlineUnavailable=false
 private fun stopOffline(){
  offlineSpeech?.let{try{it.cancel();it.shutdown()}catch(_:Exception){}}
  offlineSpeech=null
  try{offlineRecognizer?.close()}catch(_:Exception){}
  offlineRecognizer=null
  lastPartial=""
  offlineDraft=""
 }
 private fun listenOffline(){
  if(!running || speaking || offlineSpeech!=null || offlineLoading)return
  val model=offlineModel
  if(model==null){
   offlineLoading=true
   report("Preparando reconocimiento local")
   org.vosk.android.StorageService.unpack(this,"model-es","model-es",
    {loaded->handler.post{offlineLoading=false;if(running){offlineModel=loaded;listen()}else loaded.close()}},
    {_->handler.post{offlineLoading=false;offlineUnavailable=true;if(running)retry(500)}})
   return
  }
  val current=++generation
  try{
   val rec=org.vosk.Recognizer(model,16000f)
   offlineRecognizer=rec
   val service=org.vosk.android.SpeechService(rec,16000f)
   offlineSpeech=service
   report(if(sessionActive) "Escuchando conversación" else "En espera silenciosa de Jarvis")
   val started=service.startListening(object:org.vosk.android.RecognitionListener{
    override fun onPartialResult(hypothesis:String?){handler.post{
     if(!running || current!=generation || speaking)return@post
     val partial=try{org.json.JSONObject(hypothesis.orEmpty()).optString("partial")}catch(_:Exception){""}
     if(partial.isNotBlank() && partial!=lastPartial && pendingSpeech.isNotEmpty()){
      flushSpeech?.let{handler.removeCallbacks(it);handler.postDelayed(it,3500)}
     }
     lastPartial=partial
     offlineDraft=partial
    }}
    override fun onResult(hypothesis:String?){handler.post{
     if(!running || current!=generation || speaking)return@post
     val spoken=try{org.json.JSONObject(hypothesis.orEmpty()).optString("text").trim()}catch(_:Exception){""}
     lastPartial=""
     offlineDraft=""
     if(spoken.isBlank())return@post
     if(System.currentTimeMillis()>=conversationUntil && pendingSpeech.isEmpty()){sessionActive=false;history=""}
     val phrase=WakeWord.command(spoken,sessionActive) ?: return@post
     sessionActive=true;conversationUntil=System.currentTimeMillis()+180000L
     if(phrase.isBlank()){if(pendingSpeech.isEmpty()){generation++;stopOffline();say("Te escucho.")};return@post}
     if(pendingSpeech.isNotEmpty())pendingSpeech.append(' ')
     pendingSpeech.append(phrase)
     flushSpeech?.let{handler.removeCallbacks(it)}
     val task=Runnable{
      if(offlineDraft.isNotBlank()){pendingSpeech.append(' ').append(offlineDraft);offlineDraft=""}
      generation++;stopOffline();finishSpeech()
     }
     flushSpeech=task;handler.postDelayed(task,2400)
    }}
    override fun onFinalResult(hypothesis:String?){}
    override fun onError(exception:Exception?){handler.post{if(current==generation && running){generation++;stopOffline();offlineUnavailable=true;retry(500)}}}
    override fun onTimeout(){handler.post{if(current==generation && running){generation++;stopOffline();retry(500)}}}
   })
   check(started){"No se pudo iniciar reconocimiento local"}
  }catch(e:Exception){stopOffline();offlineUnavailable=true;report("Reconocimiento local no disponible");retry(500)}
 }
 private var localFallback=false
 private var capture:SilentAudioCapture?=null
 private fun listen(){
  if(!running || speaking || capture!=null)return
  retryPending=false
  if(!offlineUnavailable){listenOffline();return}
  if(localFallback || !sessionActive || System.currentTimeMillis()>=conversationUntil || !JarvisOpenAi(this).configured()){
   if(!JarvisOpenAi(this).configured() || System.currentTimeMillis()>=conversationUntil)sessionActive=false
   listenLocal();return
  }
  generation++
  recognizer?.destroy();recognizer=null
  val current=generation
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
     if(failure!=null){localFallback=true;report("Audio remoto no disponible; reconocimiento alternativo");retry(1000)}
     else if(!spoken.isNullOrBlank()){
      val phrase=spoken.trim().replace(Regex("^\\s*(?:hey\\s+)?(?:jarvis|yarvis|yárvis)[,.:! ]*",RegexOption.IGNORE_CASE),"").trim()
      conversationUntil=System.currentTimeMillis()+180000L
      if(phrase.isBlank())say("Te escucho.") else {pendingSpeech.append(phrase);finishSpeech()}
     }else retry(300)
    }
   }
  }
  handler.postDelayed({if(current==generation && capture===engine)engine.stop()},maxOf(1000L,conversationUntil-System.currentTimeMillis()))
 }
 private fun listenLocal(){
  if(!running || speaking)return
  if(sessionActive && System.currentTimeMillis()>=conversationUntil && pendingSpeech.isEmpty())sessionActive=false
  if(!SpeechRecognizer.isRecognitionAvailable(this)){report("Reconocedor de voz no instalado");running=false;getSharedPreferences("jarvis_service",MODE_PRIVATE).edit().putBoolean("enabled",false).apply();stopSelf();return}
  retryPending=false
  val current=++generation
  speechInProgress=false
  recognizer?.destroy()
  recognizer=if(useDeviceRecognition && Build.VERSION.SDK_INT>=31 && SpeechRecognizer.isOnDeviceRecognitionAvailable(this))
   SpeechRecognizer.createOnDeviceSpeechRecognizer(this)
  else SpeechRecognizer.createSpeechRecognizer(this)
  recognizer?.setRecognitionListener(object:RecognitionListener{
   override fun onReadyForSpeech(params:Bundle?){if(current==generation)report(if(sessionActive) "Escuchando conversación" else "En espera de Jarvis")}
   override fun onBeginningOfSpeech(){if(current!=generation || speaking)return; speechInProgress=true;flushSpeech?.let{handler.removeCallbacks(it)}}
   override fun onRmsChanged(rmsdB:Float){}
   override fun onBufferReceived(buffer:ByteArray?){}
   override fun onEndOfSpeech(){}
   override fun onError(error:Int){
    if(current!=generation || speaking || !running)return
    speechInProgress=false
    errors++
    report("Reconocimiento Android: código $error")
    if(error==12 || error==13 || (errors>=3 && error!=SpeechRecognizer.ERROR_NO_MATCH && error!=SpeechRecognizer.ERROR_SPEECH_TIMEOUT))useDeviceRecognition=false
    if(sessionActive && pendingSpeech.isNotEmpty() && flushSpeech!=null){handler.removeCallbacks(flushSpeech!!);handler.postDelayed(flushSpeech!!,maxOf(0L,flushDeadline-SystemClock.elapsedRealtime()))}
    if(sessionActive && pendingSpeech.isNotEmpty() && flushSpeech!=null){
     retry(1400);return
    }
    if(error==SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS){
     running=false;getSharedPreferences("jarvis_service",MODE_PRIVATE).edit().putBoolean("enabled",false).apply();stopSelf();return
    }
    // Avoid rapid recognizer restarts, which can produce repeated system tones.
    retry(if(error==SpeechRecognizer.ERROR_RECOGNIZER_BUSY) 3500L else minOf(15000L,2000L*minOf(errors,7)))
   }
   override fun onResults(results:Bundle?){
    if(current!=generation || speaking || !running)return
    speechInProgress=false
    errors=0
    val spoken=results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty().trim()
    val match=Regex("\\b(?:jarvis|yarvis|yárvis|yervis)\\b",RegexOption.IGNORE_CASE).find(spoken)
    if(match!=null || (sessionActive && System.currentTimeMillis()<conversationUntil)){
     sessionActive=true
     conversationUntil=System.currentTimeMillis()+180000L
     val part=(if(match!=null)spoken.substring(match.range.last+1) else spoken).trim()
     if(part.isBlank() && pendingSpeech.isEmpty()){generation++;recognizer?.cancel();say("Te escucho.");return}
     if(part.isNotBlank()){
      if(pendingSpeech.isNotEmpty())pendingSpeech.append(' ')
      pendingSpeech.append(part)
     }
     flushSpeech?.let{handler.removeCallbacks(it)}
     val explicitEnd=Regex("(terminé|he terminado|eso es todo|ejecuta ahora)[.! ]*$",RegexOption.IGNORE_CASE).containsMatchIn(pendingSpeech.toString())
     if(explicitEnd)finishSpeech() else {
      val task=Runnable{finishSpeech()}
      flushSpeech=task
      flushDeadline=SystemClock.elapsedRealtime()+pauseBeforeProcessingMs
      handler.postDelayed(task,pauseBeforeProcessingMs)
      if(localFallback || !JarvisOpenAi(this@ListeningService).configured())retry(900)
     }
    }else {sessionActive=false;retry(1800)}
   }
   override fun onPartialResults(partialResults:Bundle?){}
   override fun onEvent(eventType:Int,params:Bundle?){}
  })
  try{
   lastStart=System.currentTimeMillis()
   recognizer?.startListening(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply{
    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
    putExtra(RecognizerIntent.EXTRA_LANGUAGE,if(useDeviceRecognition) "es-ES" else "es-DO")
    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS,false)
    putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE,packageName)
   })
  }catch(e:Exception){errors++;retry(minOf(15000L,2000L*minOf(errors,7)))}
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
       "Conversación terminada. Di Jarvis para volver a hablar."
      }
      normalized=="hola" || normalized=="buenas" -> "Hola. Te escucho, ¿qué necesitas?"
      phrase.isBlank() -> "Aquí estoy. Puedes continuar hablando."
      else -> {
       val tokens=phrase.split(Regex("\\s+")).filter { it.length>3 }.toSet()
       val match=lessons.map { lesson -> lesson to lesson.lowercase(Locale.ROOT).split(Regex("\\s+")).count { it in tokens } }.maxByOrNull { it.second }
       if(JarvisApi(this).configured()) null
       else if(match!=null && match.second>=2) "Según lo que me enseñaste: "+match.first
       else "Configura Conectar Railway Development para consultar tus proyectos sin OpenAI."
      }
     }
     speaking=true
     generation++
     handler.removeCallbacksAndMessages(null)
     retryPending=false
     recognizer?.cancel()
     if(answer==null){
      report("Procesando tu solicitud")
      speaking=true
      thread {
       val previous=history
       val requestGeneration=generation
       val reply=try {
        val api=JarvisApi(this)
        if(api.configured()){
         val result=api.request("/v1/core/projects/query",org.json.JSONObject().put("message",phrase).put("project",selectedProject))
         val project=result.optString("project")
         handler.post{if(running && requestGeneration==generation)selectedProject=project}
         result.getString("text")
        }else "Configura Conectar Railway Development para consultar tus proyectos."
       }
        catch(e:Exception){val detail=e.message.orEmpty();when {detail.contains("401")->"El token del servidor no es válido. Configúralo en JARVIS.";detail.contains("503") || detail.contains("502")->"El servidor de proyectos no está disponible temporalmente.";else->"No pude consultar el servidor de proyectos. Revisa la conexión Railway."}}
       handler.post {if(running && requestGeneration==generation){history=(previous+"\nUsuario: "+phrase+"\nJARVIS: "+reply).takeLast(4000);say(reply)}}
      }
      return
     }
     say(answer)
 }
 private fun say(answer:String){
     getSharedPreferences("jarvis_status",MODE_PRIVATE).edit().putString("reply",answer.take(4000)).apply()
     generation++;stopOffline();recognizer?.cancel();capture?.stop();capture=null
     report("Respondiendo por voz")
     if(ttsReady && tts!=null){
      speaking=true
      val id=++utterance
      getSharedPreferences("jarvis_status",MODE_PRIVATE).edit().putString("reply",answer.take(4000)).apply()
      val result=tts?.speak(answer,TextToSpeech.QUEUE_FLUSH,null,"jarvis-$id")
      if(result==TextToSpeech.ERROR){speaking=false;report("Error de voz: revisa el motor de síntesis");retry(600)} else handler.postDelayed({if(speaking && id==utterance){utterance++;tts?.stop();speaking=false;report("Tiempo de respuesta de voz agotado");retry(700)}},maxOf(30000L,answer.length*150L))
     } else {pendingReply=answer; speaking=false; report("Motor de voz no disponible; revisa síntesis de voz");retry(600)}
 }
 private fun retry(delay:Long){
  if(!running || retryPending)return
  retryPending=true
  val sinceStart=System.currentTimeMillis()-lastStart
  val safeDelay=maxOf(delay,1200L-sinceStart)
  handler.postDelayed({retryPending=false;if(running && !speaking)listen()},safeDelay)
 }
 private fun shutdown(){stopOffline();offlineModel?.close();offlineModel=null;capture?.stop();capture=null;generation++;speaking=false;retryPending=false;sessionActive=false;pendingSpeech.setLength(0);flushSpeech=null;handler.removeCallbacksAndMessages(null);recognizer?.cancel();recognizer?.destroy();recognizer=null;tts?.stop();tts?.shutdown();tts=null}
 override fun onInit(status:Int){
  if(tts==null)return
  if(status==TextToSpeech.SUCCESS){
   configureVoice()
   ttsReady=true
   tts?.setOnUtteranceProgressListener(object:UtteranceProgressListener(){
    override fun onStart(utteranceId:String?){}
    override fun onDone(utteranceId:String?){handler.post {if(utteranceId=="jarvis-$utterance"){speaking=false;if(sessionActive)conversationUntil=System.currentTimeMillis()+180000L;retry(350)}}}
    override fun onError(utteranceId:String?){handler.post {if(utteranceId=="jarvis-$utterance"){speaking=false;retry(700)}}}
   })
   pendingReply?.let{pendingReply=null;if(running)say(it)}
  } else if(running) report("No se pudo iniciar el motor de voz")
 }
 private fun configureVoice(){
  val engine=tts ?: return
  val british=getSharedPreferences("jarvis_voice",MODE_PRIVATE).getString("profile","spanish")=="british"
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
 override fun onDestroy(){running=false;shutdown();getSharedPreferences("jarvis_status",MODE_PRIVATE).edit().putString("state","Micrófono detenido").apply();super.onDestroy()}
}
