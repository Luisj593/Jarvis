import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"server"))
from project_monitor import report,inventory,_request,GITHUB_API,RAILWAY_API
from core_bridge import dispatch
class MonitorTests(unittest.TestCase):
 def test_catalog(self):
  inv=inventory()
  self.assertEqual(len(inv["github"]),2)
  self.assertEqual(len(inv["railway"]),7)
 def test_without_tokens_reports_unknown(self):
  with patch.dict(os.environ,{"JARVIS_MONITOR_GITHUB_TOKEN":"","JARVIS_MONITOR_RAILWAY_TOKEN":""}):
   data=report(fetch=lambda *a: self.fail("must not request network"))
  self.assertEqual(data["summary"]["github_errors"],2)
  self.assertEqual(data["summary"]["railway_errors"],7)
  self.assertTrue(all(p["status"]=="unknown" for p in data["railway"]))
 def test_read_only_calls(self):
  calls=[]
  def fetch(url,token,method="GET",payload=None):
   calls.append((url,method,payload))
   if url==RAILWAY_API:return {"data":{"project":{"id":"a","name":"b","services":{"edges":[]},"environments":{"edges":[]}}}}
   if "/actions/runs" in url:return {"workflow_runs":[{"name":"Build","status":"completed","conclusion":"failure","html_url":"https://github.com/a"}]}
   return {"archived":False,"open_issues_count":2}
  with patch.dict(os.environ,{"JARVIS_MONITOR_GITHUB_TOKEN":"github-secret","JARVIS_MONITOR_RAILWAY_TOKEN":"railway-secret"}):
   data=report(fetch=fetch)
  self.assertEqual(len(calls),11)
  self.assertEqual(data["summary"]["github_errors"],0)
  self.assertEqual(data["summary"]["railway_errors"],0)
  self.assertEqual(data["summary"]["alerts"],2)
  self.assertTrue(all(a["kind"]=="workflow_problem" for a in data["alerts"]))
  self.assertTrue(all(m=="GET" or (m=="POST" and u==RAILWAY_API and "query" in p and "mutation" not in p["query"]) for u,m,p in calls))
  self.assertNotIn("secret",str(data))
 def test_reject_arbitrary_endpoint(self):
  with self.assertRaises(ValueError):_request("https://localhost:8080","token")
  with self.assertRaises(ValueError):_request(GITHUB_API+"/repos/test","token","POST")
 def test_bridge_catalog(self):
  with patch.dict(os.environ,{"JARVIS_OWNER_ID":"monitor-test"}):
   code,data=dispatch("GET","/v1/core/monitor/catalog")
  self.assertEqual(code,200)
  self.assertEqual(len(data["railway"]),7)
if __name__=="__main__":unittest.main()
