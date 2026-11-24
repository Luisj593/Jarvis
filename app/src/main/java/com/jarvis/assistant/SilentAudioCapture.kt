package com.jarvis.assistant

import android.media.AudioRecord
import android.media.AudioFormat
import android.media.MediaRecorder
import android.annotation.SuppressLint
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.sqrt

class SilentAudioCapture {
 @Volatile private var active=false
 @Volatile private var recorder:AudioRecord?=null
 fun stop(){active=false;try{recorder?.stop()}catch(_:Exception){}}
 @SuppressLint("MissingPermission")
 fun capture(onSpeech:(ByteArray)->Unit,onError:(Exception)->Unit){
  active=true
  val rate=16000
  var record:AudioRecord?=null
  try {
   val min=AudioRecord.getMinBufferSize(rate,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT)
   require(min>0){"Formato de audio no disponible"}
   val input=AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION,rate,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT,maxOf(min,6400))
   record=input;recorder=input
   check(input.state==AudioRecord.STATE_INITIALIZED){"Micrófono no disponible"}
   input.startRecording()
   val samples=ShortArray(320)
   val pre=java.util.ArrayDeque<ByteArray>()
   var speech:ByteArrayOutputStream?=null
   var quiet=0
   var voiced=0
   var noise=100.0
   while(active){
    val n=input.read(samples,0,samples.size)
    if(n<=0){if(active)error("Lectura de micrófono: $n");break}
    val rms=sqrt((0 until n).sumOf{samples[it].toDouble()*samples[it]}/n)
    val loud=rms>maxOf(220.0,noise*3.0)
    if(!loud && speech==null)noise=noise*0.98+rms*0.02
    val bytes=ByteBuffer.allocate(n*2).order(ByteOrder.LITTLE_ENDIAN)
    for(i in 0 until n)bytes.putShort(samples[i])
    val frame=bytes.array()
    if(speech==null){
     pre.addLast(frame);while(pre.size>20)pre.removeFirst()
     voiced=if(loud)voiced+1 else 0
     if(voiced>=3){speech=ByteArrayOutputStream();pre.forEach{speech!!.write(it)};pre.clear();quiet=0}
    }else{
     speech.write(frame)
     quiet=if(loud)0 else quiet+1
     if(quiet>=75 || speech.size()>=rate*2*45){
      val pcm=speech.toByteArray();speech=null;voiced=0;quiet=0
      if(pcm.size>rate/2 && active){onSpeech(wav(pcm,rate));break}
     }
    }
   }
  }catch(e:Exception){if(active)onError(e)}
  finally{active=false;recorder=null;try{record?.stop()}catch(_:Exception){};record?.release()}
 }
 private fun wav(pcm:ByteArray,rate:Int):ByteArray{
  val b=ByteBuffer.allocate(44+pcm.size).order(ByteOrder.LITTLE_ENDIAN)
  b.put("RIFF".toByteArray()).putInt(36+pcm.size).put("WAVEfmt ".toByteArray()).putInt(16).putShort(1.toShort()).putShort(1.toShort()).putInt(rate).putInt(rate*2).putShort(2.toShort()).putShort(16.toShort()).put("data".toByteArray()).putInt(pcm.size).put(pcm)
  return b.array()
 }
}
