import os
import google.generativeai as genai
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Literal
import json

app = FastAPI(title="Monkey Test Server - QA Agent Compacto")

# Configurar Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# El mejor modelo del nivel gratuito (15 RPM, 1M tokens)
model = genai.GenerativeModel('gemini-2.0-flash')


@app.get("/health")
def health_check():
    return {"status": "ok", "gemini_ready": True}


# ----- CONTRATO DE DATOS (PYDANTIC) -----

class Element(BaseModel):
    id: str
    text: Optional[str] = ""
    role: Optional[str] = ""

class DecideActionRequest(BaseModel):
    session_id: str
    app_under_test: str
    last_action_attempted: Optional[str] = "ninguna"
    elements: list[Element]
    data_rules_summary: dict
    constraints: dict

class DecideActionResponse(BaseModel):
    analysis: str
    action: Literal["tap", "input", "scroll", "back", "terminate"]
    target_element_id: Optional[str] = None
    input_value_key: Optional[str] = None
    notes: Optional[str] = None


@app.post("/decide_action", response_model=DecideActionResponse)
def decide_action(payload: DecideActionRequest):
    """
    GEMINI QA AGENT analiza el éxito de la acción anterior y decide la siguiente (Optimizado para tokens).
    """

    # Resumen hiper-compacto de los elementos en pantalla
    elements_text = "\n".join([
        f"[{el.id}] {el.role}: '{el.text}'"
        for el in payload.elements
    ])

    # PROMPT COMPACTO: Ahorramos hasta un 30% de tokens de entrada
    prompt = f"""
Eres un QA tester en la app Android: {payload.app_under_test}

MEMORIA:
Última acción intentada: {payload.last_action_attempted}

PANTALLA ACTUAL:
{elements_text}

DATOS DE PRUEBA:
{json.dumps(payload.data_rules_summary)}

INSTRUCCIONES:
1. Evalúa si la última acción funcionó o si ves un mensaje de error.
2. Decide el siguiente paso lógico.

RESPONDE SOLO EN ESTE FORMATO JSON:
{{
  "analysis": "Breve evaluación del estado actual y éxito de la acción previa",
  "action": "tap|input|scroll|back|terminate",
  "target_element_id": "ID exacto del elemento destino (o null)",
  "input_value_key": "Clave del dato a escribir (o null)",
  "notes": "Razón"
}}
"""

    try:
        # Obligamos a Gemini a devolver un JSON válido
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        
        ai_text = response.text.strip()
        action_dict = json.loads(ai_text)
        
        # Validación de seguridad: evitar IDs inventados por la IA
        if action_dict.get("action") in ["tap", "input"]:
            id_elegido = action_dict.get("target_element_id")
            if id_elegido and not any(el.id == id_elegido for el in payload.elements):
                action_dict["analysis"] += " [CORRECCIÓN SISTEMA: ID inventado, fallback a scroll]"
                action_dict["action"] = "scroll"
                action_dict["target_element_id"] = None
                action_dict["notes"] = "ID inventado por IA, aplicando fallback"

        return DecideActionResponse(**action_dict)
        
    except Exception as e:
        print(f"Error procesando Gemini: {e}")
        return DecideActionResponse(
            analysis=f"Fallo en el servidor o IA: {str(e)}",
            action="scroll",
            notes="Fallback de seguridad por excepción"
        )
