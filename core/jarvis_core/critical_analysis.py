"""Política de crítica analítica basada en evidencias, sin oposición automática.

La clasificación usa señales explícitas aportadas por el sistema; no inventa
pruebas, hechos o resultados. La inferencia semántica avanzada requiere un
modelo de lenguaje y recuperación de fuentes verificables.
"""
from dataclasses import dataclass,asdict

@dataclass(frozen=True)
class CriticalAssessment:
 verdict:str
 confidence:str
 facts:tuple[str,...]
 concerns:tuple[str,...]
 unknowns:tuple[str,...]
 recommendation:str
 action_allowed:bool

def assess(proposal,evidence=(),risks=(),unknowns=(),requires_production=False):
 if not isinstance(proposal,str) or not proposal.strip() or len(proposal)>3000:
  raise ValueError("propuesta inválida")
 for values in (evidence,risks,unknowns):
  if not isinstance(values,(tuple,list)) or len(values)>30 or any(
      not isinstance(v,str) or not v.strip() or len(v)>1000 for v in values):
   raise ValueError("evidencias inválidas")
 facts=tuple(evidence);concerns=tuple(risks);missing=tuple(unknowns)
 if concerns:
  verdict="question"
  recommendation="Resolver los riesgos identificados antes de avanzar."
 elif missing or not facts:
  verdict="insufficient_evidence"
  recommendation="Obtener y verificar las evidencias pendientes antes de concluir."
 else:
  verdict="conditionally_supported"
  recommendation="La evidencia aportada respalda continuar con validaciones controladas."
 if requires_production:
  recommendation+=" El despliegue a producción requiere autorización explícita."
 return CriticalAssessment(verdict,"limited_to_supplied_evidence",facts,concerns,
                           missing,recommendation,False)
