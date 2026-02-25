from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Literal

app = FastAPI(title="Perplexity MCP Test Server")


# ----- MODELOS DE ENTRADA (lo que envía la APK) -----

class Element(BaseModel):
    id: str
    text: Optional[str] = None
    content_desc: Optional[str] = None
    class_name: Optional[str] = None
    role: Optional[str] = None
    package_name: Optional[str] = None
    clickable: Optional[bool] = None
    enabled: Optional[bool] = None
    focused: Optional[bool] = None
    bounds: Optional[List[int]] = None  # [left, top, right, bottom]


class HistoryItem(BaseModel):
    step: int
    action: str
    target_app: Optional[str] = None


class Screen(BaseModel):
    activity_name: Optional[str] = None
    title: Optional[str] = None
    url_like: Optional[str] = None


class Constraints(BaseModel):
    max_steps: int
    current_step: int


class DecideActionRequest(BaseModel):
    session_id: str
    device_info: dict
    app_under_test: str
    screen: Screen
    elements: List[Element]
    history: List[HistoryItem]
    data_rules_summary: dict
    constraints: Constraints


# ----- MODELOS DE SALIDA (acción que vuelve a la APK) -----

ActionType = Literal["tap", "input", "scroll", "back", "wait", "terminate"]
ScrollDirection = Literal["up", "down"]


class DecideActionResponse(BaseModel):
    action: ActionType
    target_element_id: Optional[str] = None
    input_value_key: Optional[str] = None
    scroll_direction: Optional[ScrollDirection] = None
    notes: Optional[str] = None


# ----- ENDPOINTS -----

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/decide_action", response_model=DecideActionResponse)
def decide_action(payload: DecideActionRequest):
    """
    Por ahora: lógica de ejemplo (no usa Perplexity aún).
    Solo demuestra el formato de entrada/salida.
    """

    # Si ya hemos llegado al máximo de pasos, terminamos
    if payload.constraints.current_step >= payload.constraints.max_steps:
        return DecideActionResponse(
            action="terminate",
            notes="Se alcanzó el máximo de pasos configurado en constraints."
        )

    # Intentar encontrar un botón 'Login' como ejemplo
    for el in payload.elements:
        if el.clickable and (el.text and "login" in el.text.lower()):
            return DecideActionResponse(
                action="tap",
                target_element_id=el.id,
                notes="Ejemplo: pulsar botón con texto 'Login'."
            )

    # Si hay algún campo de texto y hay alguna regla de datos, hacer input de ejemplo
    for el in payload.elements:
        if el.role == "input" and payload.data_rules_summary:
            # Coger la primera clave de data_rules_summary
            first_key = list(payload.data_rules_summary.keys())[0]
            return DecideActionResponse(
                action="input",
                target_element_id=el.id,
                input_value_key=first_key,
                notes=f"Ejemplo: rellenar input con la clave {first_key}."
            )

    # Si no encontramos nada especial, hacer scroll hacia abajo como ejemplo
    return DecideActionResponse(
        action="scroll",
        scroll_direction="down",
        notes="Ejemplo: no hay acción clara, hacemos scroll hacia abajo."
    )
