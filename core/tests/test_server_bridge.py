"""Pruebas de integración API/núcleo sin sockets ni servicios externos."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"server"))
from core_bridge import dispatch

class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{"JARVIS_OWNER_ID":"test-owner","JARVIS_DB_PATH":str(Path(self.temp.name)/"bridge.sqlite")})
        self.env.start()
    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()
    def test_catalog(self):
        code,data=dispatch("GET","/v1/core/actions")
        self.assertEqual(code,200)
        self.assertTrue(data["strict_policies"])
    def test_project_and_policy_strict(self):
        code,data=dispatch("POST","/v1/core/projects",{"name":"Jarvis","objective":"Probar"})
        self.assertEqual(code,201)
        pid=data["project"]["id"]
        request={"project_id":pid,"action":"project.set_status","params":{"status":"active"}}
        self.assertEqual(dispatch("POST","/v1/core/actions/preview",request)[0],403)
        self.assertEqual(dispatch("POST","/v1/core/actions/policy",{"project_id":pid,"allowed":True,"expected_version":None})[0],200)
        code,data=dispatch("POST","/v1/core/actions/preview",request)
        self.assertEqual(code,200)
        ticket=data["preview"]["ticket"]
        self.assertEqual(dispatch("POST","/v1/core/actions/confirm",{"ticket":ticket,"confirmation":"CONFIRMAR ACCIÓN"})[0],200)
        self.assertEqual(dispatch("POST","/v1/core/actions/confirm",{"ticket":ticket,"confirmation":"CONFIRMAR ACCIÓN"})[0],403)
        self.assertEqual(dispatch("GET","/v1/core/audit")[1]["integrity"],True)
    def test_conversation_unknown_without_execution(self):
        self.assertEqual(dispatch("POST","/v1/core/conversation/select",{"session_id":"s1","project":"Jarvis"})[0],200)
        code,data=dispatch("POST","/v1/core/conversation/respond",{"session_id":"s1","message":"hola"})
        self.assertEqual(code,200)
        self.assertFalse(data["response"]["executed"])
    def test_bad_input(self):
        self.assertEqual(dispatch("POST","/v1/core/projects",{"name":"x","objective":"y","owner_id":"evil"})[0],400)
        self.assertEqual(dispatch("POST","/v1/core/actions/policy",{"project_id":"x","allowed":True})[0],400)
    def test_missing_owner_fails_closed(self):
        with patch.dict(os.environ,{"JARVIS_OWNER_ID":""}):
            with self.assertRaises(RuntimeError):
                dispatch("GET","/v1/core/projects")
    def test_owner_not_supplied_by_client(self):
        self.assertEqual(dispatch("POST","/v1/core/projects",{"name":"A","objective":"B","owner_id":"other"})[0],400)
    def test_not_found(self):
        self.assertEqual(dispatch("GET","/v1/core/nonexistent")[0],404)

if __name__=="__main__":
    unittest.main()
