import tempfile
import threading
import unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from jarvis_core.research import Research,ResearchError
from jarvis_core.security import Principal

RSS=b"""<?xml version="1.0"?><rss><channel>
<item><title>Android mejora seguridad</title><link>https://example.org/android</link><pubDate>Mon, 23 Nov 2026 12:00:00 GMT</pubDate></item>
<item><title>Noticias sobre deporte</title><link>https://example.org/deporte</link></item>
<item><title>Android no seguro</title><link>http://example.org/unsafe</link></item>
</channel></rss>"""
PERMS=frozenset({"memory:read","memory:write"})
class ResearchTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.path=Path(self.tmp.name)/"research.sqlite"
  self.a=Research(self.path,Principal("alice",PERMS),fetch=lambda _:RSS)
  self.b=Research(self.path,Principal("bob",PERMS),fetch=lambda _:RSS)
 def tearDown(self):self.tmp.cleanup()
 def test_research_with_sources(self):
  result=self.a.investigate("Android")
  self.assertEqual(len(result.findings),1)
  self.assertIn("RSS",result.summary)
  self.assertEqual(result.findings[0].source,"BBC Tecnología")
 def test_no_match(self):
  self.assertFalse(self.a.investigate("astronomía").findings)
 def test_allowlist(self):
  with self.assertRaises(ValueError):self.a.investigate("Android","http://localhost:8000")
 def test_invalid_topic(self):
  with self.assertRaises(ValueError):self.a.investigate(" ")
 def test_bounded_jobs(self):
  for bad in (0,59,43201,True):
   with self.assertRaises(ValueError):self.a.schedule("Android",interval_minutes=bad)
 def test_isolation(self):
  job=self.a.schedule("Android",interval_minutes=60)
  self.assertEqual(self.b.jobs(),[])
  self.assertFalse(self.b.cancel(job))
  self.assertTrue(self.a.cancel(job))
 def test_permissions(self):
  readonly=Research(self.path,Principal("reader",frozenset({"memory:read"})),fetch=lambda _:RSS)
  with self.assertRaises(PermissionError):readonly.schedule("Android")
  no_read=Research(self.path,Principal("none",frozenset()),fetch=lambda _:RSS)
  with self.assertRaises(PermissionError):no_read.investigate("Android")
 def test_run_due(self):
  job=self.a.schedule("Android",interval_minutes=60)
  now=datetime.now(timezone.utc)+timedelta(hours=2)
  results=self.a.run_due(now)
  self.assertEqual(len(results),1)
  self.assertEqual(results[0][0],job)
  self.assertEqual(len(self.a.history()),1)
  self.assertEqual(self.a.run_due(now),[])
  self.assertEqual(self.b.history(),[])
 def test_concurrent_run_once(self):
  self.a.schedule("Android",interval_minutes=60)
  now=datetime.now(timezone.utc)+timedelta(hours=2)
  barrier=threading.Barrier(2)
  results=[]
  def worker():
   client=Research(self.path,Principal("alice",PERMS),fetch=lambda _:RSS)
   barrier.wait()
   results.extend(client.run_due(now))
  threads=[threading.Thread(target=worker) for _ in range(2)]
  for t in threads:t.start()
  for t in threads:t.join(10)
  self.assertFalse(any(t.is_alive() for t in threads))
  self.assertEqual(len(results),1)
 def test_fetch_restricts_arbitrary_url(self):
  with self.assertRaises(ResearchError):Research._fetch("https://127.0.0.1/")
 def test_no_implicit_memory(self):
  self.a.investigate("Android")
  self.assertEqual(self.a.history(),[])
 def test_invalid_xml(self):
  broken=Research(self.path,Principal("alice",PERMS),fetch=lambda _:b"<rss")
  with self.assertRaises(ResearchError):broken.investigate("Android")
if __name__=="__main__":unittest.main()
