"""Evaluación estática, explicable y de solo lectura de módulos e-CF.
No certifica emisores ni modifica sistemas auditados.
"""
from dataclasses import dataclass,asdict
import re

CHECKS=(
 ("tipos_ecf","Tipos de comprobantes electrónicos","e31|e32|e33|e34|ecf|e-cf|comprobante"),
 ("secuencias","Control de secuencias y e-NCF","encf|e-ncf|secuencia|secuencial"),
 ("xml","Generación de XML","xml|etree|lxml"),
 ("xsd","Validación de esquemas XSD","xsd|xmlschema|schema"),
 ("firma","Firma digital","firma digital|signature|xmlsec|certificado"),
 ("envio","Comunicación con DGII","dgii|recepcion|recepción|enviar"),
 ("respuesta","Estados y respuestas DGII","aceptado|rechazado|acuse|estado"),
 ("notas","Notas de crédito y débito","nota de credito|nota de crédito|nota de debito|nota de débito|e33|e34"),
 ("contingencia","Contingencias y reintentos","contingencia|retry|reintento"),
 ("auditoria","Trazabilidad y auditoría","auditoria|auditoría|audit|historial"),
)
def assess_ecf_module(project_name,files):
 if not isinstance(project_name,str) or not 1<=len(project_name.strip())<=100:
  raise ValueError("proyecto inválido")
 if not isinstance(files,list) or not 1<=len(files)<=80:
  raise ValueError("archivos inválidos")
 combined=[]
 for file in files:
  if not isinstance(file,dict) or set(file)!={"path","content"}:
   raise ValueError("estructura inválida")
  path,body=file["path"],file["content"]
  if not isinstance(path,str) or not isinstance(body,str) or len(path)>300 or len(body)>100000:
   raise ValueError("archivo inválido")
  combined.append((path,body.lower()))
 findings=[]
 for key,label,pattern in CHECKS:
  evidence=[path for path,body in combined if re.search(pattern,body,re.IGNORECASE)][:5]
  findings.append({"check":key,"description":label,
    "status":"indicio_en_codigo" if evidence else "no_identificado",
    "evidence_files":evidence,
    "recommendation":("Verificar ejecución real, configuración y pruebas; la coincidencia textual no demuestra cumplimiento."
       if evidence else "Inspeccionar código, configuración y pruebas para determinar si existe la función.")})
 return {"project":project_name,"mode":"analisis_estatico_solo_lectura",
   "scope":"No certificación; no se accede al proyecto sin aportar archivos.",
   "checks":findings,"reviewed_files":len(files),
   "limitations":"Los hallazgos son indicios textuales. No demuestran funcionamiento ni conformidad DGII.",
   "source":"Documentación DGII almacenada en JARVIS"}
