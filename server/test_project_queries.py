import unittest
from unittest.mock import patch
from project_queries import query
class ProjectQueryTests(unittest.TestCase):
    def test_selection(self):
        self.assertEqual(query("selecciona Plazado")["project"],"plazado")
    def test_missing_token(self):
        with patch.dict("os.environ",{"JARVIS_GITHUB_READ_TOKEN":"","JARVIS_MONITOR_GITHUB_TOKEN":""}):
            self.assertIn("Falta configurar",query("estado","plazado")["text"])
    def test_ambiguous(self):
        self.assertEqual(query("Plazado y Jarvis")["project"],"")
    def test_railway_not_claimed(self):
        with patch.dict("os.environ",{"JARVIS_RAILWAY_READ_TOKEN":"","JARVIS_MONITOR_RAILWAY_TOKEN":""}):
            self.assertIn("Falta configurar",query("despliegue","jarvis")["text"])
    def test_evaluation_all(self):
        with patch("project_evaluation.evaluate",return_value={"text":"informe"}) as evaluate:
            self.assertEqual(query("Evalúa todos mis proyectos")["text"],"informe")
            evaluate.assert_called_once_with([])
    def test_evaluation_specific(self):
        with patch("project_evaluation.evaluate",return_value={"text":"informe"}) as evaluate:
            query("Haz una evaluación de Plazado")
            evaluate.assert_called_once_with(["plazado"])
    def test_evidence(self):
        from project_evaluation import evaluate
        data={"github":[{"repository":"Luisj593/Plazado","last_workflow":{"conclusion":"failure"}}],"alerts":[{"project":"Luisj593/Plazado","detail":"failure"}]}
        result=evaluate(["plazado"],lambda:data)
        self.assertIn("Prioridad",result["text"])
        self.assertIn("failure",result["text"])
if __name__=="__main__":unittest.main()
