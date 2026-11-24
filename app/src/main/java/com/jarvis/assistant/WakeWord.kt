package com.jarvis.assistant

object WakeWord {
 private val wake = Regex("\\b(?:hey\\s+|oye\\s+)?(?:jarvis|yarvis|yárvis|yervis|harvis)\\b", RegexOption.IGNORE_CASE)
 fun command(text:String, active:Boolean):String? {
  val clean=text.trim()
  if(clean.isEmpty())return null
  val match=wake.find(clean)
  if(active && (match==null || match.range.first>0))return clean
  return if(match!=null)clean.substring(match.range.last+1).trimStart(' ', ',', '.', ':', '!','¿','¡') else null
 }
}
