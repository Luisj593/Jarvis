import unittest
from jarvis_core.critical_analysis import assess
class CriticalAnalysisTests(unittest.TestCase):
 def test_no_evidence(self):
  r=assess("Desplegar ahora")
  self.assertEqual(r.verdict,"insufficient_evidence")
  self.assertFalse(r.action_allowed)
 def test_challenge_with_grounded_risks(self):
  r=assess("Publicar",["Compilación aprobada"],["Prueba de pago fallida"],requires_production=True)
  self.assertEqual(r.verdict,"question")
  self.assertIn("Prueba de pago fallida",r.concerns)
  self.assertIn("autorización",r.recommendation)
 def test_support_without_flattery(self):
  r=assess("Validar en pruebas",["Pruebas unitarias aprobadas"])
  self.assertEqual(r.verdict,"conditionally_supported")
  self.assertEqual(r.confidence,"limited_to_supplied_evidence")
 def test_unknowns_override_support(self):
  r=assess("Publicar",["Compilación aprobada"],unknowns=["Sin prueba de dispositivo"])
  self.assertEqual(r.verdict,"insufficient_evidence")
 def test_invalid(self):
  with self.assertRaises(ValueError):assess(" ")
if __name__=="__main__":unittest.main()
