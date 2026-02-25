import os
import google.generativeai as genai
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Literal
import json

app = FastAPI(title="Monkey Test Server - Intelligent QA Agent")

# Configurar Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Usamos flash-latest que es la versión estable actual
model = genai.GenerativeModel('gemini-2.0-flash')


@app.get("/health")
def health_check():
    return {"status": "ok", "gemini_ready": True}


# ----- CONTRACTO APK -----

class Element(BaseModel):
    id: str
    text: Optional[str] = ""
    role: Optional[str] = ""
    clickable: Optional[bool] = False

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
    GEMINI QA AGENT analiza el éxito de la acción anterior y decide la siguiente.
    """

    # Resumir elementos para Gemini (Limitamos a 15 para no saturar)
    elements_text = "\n".join([
        f"- ID: {el.id} | Texto: '{el.text}' | Rol: {el.role} | Clickable: {el.clickable}"
        for el in payload.elements[:15]
    ])

    prompt = f"""
Eres un QA Engineer experto explorando una app Android: {payload.app_under_test}

HISTORIAL DE LA SESIÓN:
Acción anterior que intentaste: {payload.last_action_attempted}

ESTADO ACTUAL DE LA PANTALLA:
{elements_text}

DATOS PARA RELLENAR FORMULARIOS:
{json.dumps(payload.data_rules_summary)}

TU TAREA:
1. Evalúa si la acción anterior funcionó. ¿Apareció algún mensaje de error en la pantalla actual? ¿Cambió la pantalla?
2. Decide la siguiente acción lógica para avanzar en la app (Login, aceptar permisos, navegar).

RESPONDE ESTRICTAMENTE EN ESTE FORMATO JSON:
{{
  "analysis": "Tu evaluación de la pantalla actual y el resultado de la acción anterior. Menciona si ves errores.",
  "action": "tap" o "input" o "scroll" o "back" o "terminate",
  "target_element_id": "El ID exacto del elemento (si aplica)",
  "input_value_key": "La clave exacta de los datos a usar (solo si action es input)",
  "notes": "Razón breve de la nueva acción"
}}
"""

    try:
        # Obligamos a Gemini a devolver un JSON estricto
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        
        ai_text = response.text.strip()
        
        # Parseamos el JSON devuelto por Gemini
        action_dict = json.loads(ai_text)
        
        # Validación de seguridad: Asegurar que target_element_id no es inventado
        # (Si es tap o input, el ID debe existir en la lista enviada)
        if action_dict.get("action") in ["tap", "input"]:
            id_en_pantalla = any(el.id == action_dict.get("target_element_id") for el in payload.elements)
            if not id_en_pantalla:
                action_dict["analysis"] += " [CORRECCIÓN: El ID elegido no existe, cambiando a scroll]"
                action_dict["action"] = "scroll"
                action_dict["target_element_id"] = None
                action_dict["notes"] = "ID inventado por IA, fallback a scroll"

        return DecideActionResponse(**action_dict)
        
    except Exception as e:
        print(f"Error procesando Gemini: {e}")
        return DecideActionResponse(
            analysis=f"Fallo en el servidor o IA: {str(e)}",
            action="back",
            notes="Fallback de seguridad"
        )
