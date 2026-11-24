package com.jarvis.assistant
import org.junit.Test
import org.junit.Assert.*
class WakeWordTest {
 @Test fun standbyIgnoresAmbientSpeech(){assertNull(WakeWord.command("vamos a comer",false))}
 @Test fun wakeOnly(){assertEquals("",WakeWord.command("Hey Jarvis",false))}
 @Test fun wakeWithCommand(){assertEquals("revisa Plazado",WakeWord.command("Oye Jarvis, revisa Plazado",false))}
 @Test fun followUpWithoutWake(){assertEquals("continúa con ese proyecto",WakeWord.command("continúa con ese proyecto",true))}
 @Test fun preserveMentionInActiveConversation(){assertEquals("revisa el proyecto Jarvis",WakeWord.command("revisa el proyecto Jarvis",true))}
 @Test fun pronunciationVariant(){assertEquals("hola",WakeWord.command("yarvis hola",false))}
}
