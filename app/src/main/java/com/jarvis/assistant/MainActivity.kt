package com.jarvis.assistant

import android.Manifest
import android.app.Activity
import android.os.Bundle
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.RecognitionListener
import android.content.Intent
import android.content.pm.PackageManager
import android.speech.tts.TextToSpeech
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import java.util.Locale

class MainActivity : Activity(), TextToSpeech.OnInitListener {
 private lateinit var status: TextView
 private var speech: SpeechRecognizer? = null
 private var tts: TextToSpeech? = null
 override fun onCreate(savedInstanceState: Bundle?) {
  super.onCreate(savedInstanceState)
  val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(48,72,48,32) }
  status = TextView(this).apply { text = "JARVIS · Android inicial\nPulsa para hablar"; textSize = 23f }
  val button = Button(this).apply { text = "Hablar con JARVIS"; setOnClickListener { listen() } }
  layout.addView(status); layout.addView(button); setContentView(layout)
  tts = TextToSpeech(this,this)
 }
 private fun listen() {
  if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
   requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 11); return
  }
  if (!SpeechRecognizer.isRecognitionAvailable(this)) { status.text="Reconocimiento de voz no disponible"; return }
  speech?.destroy()
  speech = SpeechRecognizer.createSpeechRecognizer(this)
  speech?.setRecognitionListener(object: RecognitionListener {
   override fun onReadyForSpeech(p0: Bundle?) { status.text="Escuchando..." }
   override fun onBeginningOfSpeech() {}
   override fun onRmsChanged(v: Float) {}
   override fun onBufferReceived(b: ByteArray?) {}
   override fun onEndOfSpeech() {}
   override fun onError(code: Int) { status.text="Error de voz: $code" }
   override fun onResults(b: Bundle?) {
    val said=b?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull() ?: ""
    status.text="Dijiste: $said\n\nMotor remoto aún no conectado"
    tts?.speak("Te escuché. La conexión con el servidor está pendiente.",TextToSpeech.QUEUE_FLUSH,null,"response")
   }
   override fun onPartialResults(b: Bundle?) {}
   override fun onEvent(t: Int,b: Bundle?) {}
  })
  speech?.startListening(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
   putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
   putExtra(RecognizerIntent.EXTRA_LANGUAGE,"es-DO")
  })
 }
 override fun onInit(statusCode: Int) { if(statusCode==TextToSpeech.SUCCESS) tts?.language=Locale("es","DO") }
 override fun onDestroy() { speech?.destroy(); tts?.shutdown(); super.onDestroy() }
}
