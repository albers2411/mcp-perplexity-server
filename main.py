import os
import google.generativeai as genai
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Literal

app = FastAPI(title="Monkey Test Server - Gemini FREE")

# Configurar Gemini (API key gratuita)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')


# Rutas de prueba (sin cambios)
@app.get("/health")
def health_check():
    return {"status": "ok", "gemini_ready": True}


@app.post("/test_action")
def test_action(payload: dict):
    return {
        "action": "tap",
        "target_element_id": "button_login_123",
        "notes": f"¡PRUEBA OK! {payload}"
    }


# ----- CONTRACTO APK -----

class DecideActionRequest(BaseModel):
    session_id: str
    app_under_test: str
    elements: list[dict]
    data_rules_summary: dict
    constraints: dict


class DecideActionResponse(BaseModel):
    action: Literal["tap", "input", "scroll", "back", "wait", "terminate"]
    target_element_id: Optional[str] = None
    input_value_key: Optional[str] = None
    scroll_direction: Optional[Literal["up", "down"]] = None
    notes: Optional[str] = None


@app.post("/decide_action", response_model=DecideActionResponse)
def decide_action(payload: DecideActionRequest):
    """
    GEMINI IA GRATUITA decide la acción inteligente.
    """

    # Resumir elementos para Gemini
    elements_text = "\n".join([
        f"• ID:{el['id']} Texto:'{el.get('text', '')}' Rol:{el.get('role', 'desconocido')} Clickable:{el.get('clickable', False)}"
        for el in payload.elements[:8]
    ])

    prompt = f"""
Explora esta app Android: {payload.app_under_test}

Elementos en pantalla:
{elements_text}

Datos para campos:
{payload.data_rules_summary}

DECIDE UNA ACCIÓN como usuario real. Responde SOLO JSON:

{{
  "action": "tap|input|scroll|back|terminate",
  "target_element_id": "ID_exacto",
  "input_value_key": "clave_data_rules",
  "notes": "razón"
}}

Prioridades: Login > campos input > scroll > back
"""

    try:
        response = model.generate_content(prompt)
        ai_text = response.text.strip()

        # Extraer JSON
        import json, re
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', ai_text)
        if json_match:
            return DecideActionResponse(**json.loads(json_match.group()))
        else:
            return DecideActionResponse(
                action="scroll", scroll_direction="down",
                notes="Gemini OK pero parseo falló"
            )
    except Exception as e:
        return DecideActionResponse(
            action="back", notes=f"Error: {str(e)}"
        )
