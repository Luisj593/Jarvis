import unittest
from unittest.mock import patch
from project_queries import query
class ProjectQueryTests(unittest.TestCase):
    def test_selection(self):
        self.assertEqual(query("selecciona Plazado")["project"],"plazado")
    def test_missing_token(self):
        with patch.dict("os.environ",{"JARVIS_GITHUB_READ_TOKEN":""}):
            self.assertIn("Falta configurar",query("estado","plazado")["text"])
    def test_ambiguous(self):
        self.assertEqual(query("Plazado y Jarvis")["project"],"")
    def test_railway_not_claimed(self):
        with patch.dict("os.environ",{"JARVIS_RAILWAY_READ_TOKEN":""}):
            self.assertIn("Falta configurar",query("despliegue","jarvis")["text"])
if __name__=="__main__":unittest.main()
