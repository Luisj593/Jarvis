import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"server"))
from core_bridge import dispatch
from jarvis_core.research import Research
RSS=b'<rss><channel><item><title>Android seguro</title><link>https://example.org/a</link></item></channel></rss>'
class ResearchBridgeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.env=patch.dict(os.environ,{"JARVIS_OWNER_ID":"research-test","JARVIS_DB_PATH":str(Path(self.tmp.name)/"db.sqlite")})
  self.env.start()
 def tearDown(self):
  self.env.stop();self.tmp.cleanup()
 def test_query(self):
  with patch.object(Research,"_fetch",return_value=RSS):
   code,body=dispatch("POST","/v1/core/research/query",{"topic":"Android","source":"tecnologia"})
  self.assertEqual(code,200)
  self.assertEqual(len(body["result"]["findings"]),1)
 def test_schedule_and_cancel(self):
  code,body=dispatch("POST","/v1/core/research/schedule",{"topic":"Android","source":"tecnologia","interval_minutes":60})
  self.assertEqual(code,201)
  self.assertEqual(body["execution"],"requires_scheduler")
  job=body["job_id"]
  self.assertEqual(len(dispatch("GET","/v1/core/research/jobs")[1]["jobs"]),1)
  self.assertTrue(dispatch("POST","/v1/core/research/cancel",{"job_id":job})[1]["cancelled"])
 def test_invalid_source_and_extraneous_owner(self):
  self.assertEqual(dispatch("POST","/v1/core/research/query",{"topic":"x","source":"http://127.0.0.1"})[0],400)
  self.assertEqual(dispatch("POST","/v1/core/research/query",{"topic":"x","source":"mundo","owner_id":"other"})[0],400)
 def test_missing_owner(self):
  with patch.dict(os.environ,{"JARVIS_OWNER_ID":""}):
   with self.assertRaises(RuntimeError):dispatch("GET","/v1/core/research/jobs")
if __name__=="__main__":unittest.main()
