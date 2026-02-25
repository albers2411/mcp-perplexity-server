from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Literal

app = FastAPI(title="Perplexity MCP Test Server")


# ----- RUTA DE PRUEBA SIMPLE -----

class TestActionRequest(BaseModel):
    session_id: str
    app_name: str


class TestActionResponse(BaseModel):
    action: Literal["tap", "input", "scroll", "back"]
    target_element_id: Optional[str] = None
    input_value_key: Optional[str] = None
    scroll_direction: Optional[Literal["up", "down"]] = None
    notes: str


@app.post("/test_action", response_model=TestActionResponse)
def test_action(payload: TestActionRequest):
    """
    RUTA DE PRUEBA: devuelve siempre la misma acción fija.
    Úsala para simular la APK sin necesidad de JSON complejo.
    """
    return TestActionResponse(
        action="tap",
        target_element_id="button_login_123",
        notes=f"¡PRUEBA OK! Simulando tap en app {payload.app_name}, sesión {payload.session_id}"
    )


# ----- ANTES (sin cambios) -----

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
    bounds: Optional[list] = None


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
    elements: list[Element]
    history: list[HistoryItem]
    data_rules_summary: dict
    constraints: Constraints


class DecideActionResponse(BaseModel):
    action: Literal["tap", "input", "scroll", "back", "wait", "terminate"]
    target_element_id: Optional[str] = None
    input_value_key: Optional[str] = None
    scroll_direction: Optional[Literal["up", "down"]] = None
    notes: Optional[str] = None


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/decide_action", response_model=DecideActionResponse)
def decide_action(payload: DecideActionRequest):
    """
    Por ahora: lógica de ejemplo (no usa Perplexity aún).
    """
    if payload.constraints.current_step >= payload.constraints.max_steps:
        return DecideActionResponse(
            action="terminate",
            notes="Se alcanzó el máximo de pasos configurado."
        )

    for el in payload.elements:
        if el.clickable and (el.text and "login" in el.text.lower()):
            return DecideActionResponse(
                action="tap",
                target_element_id=el.id,
                notes="Ejemplo: pulsar botón con texto 'Login'."
            )

    for el in payload.elements:
        if el.role == "input" and payload.data_rules_summary:
            first_key = list(payload.data_rules_summary.keys())[0]
            return DecideActionResponse(
                action="input",
                target_element_id=el.id,
                input_value_key=first_key,
                notes=f"Ejemplo: rellenar input con la clave {first_key}."
            )

    return DecideActionResponse(
        action="scroll",
        scroll_direction="down",
        notes="Ejemplo: no hay acción clara, hacemos scroll hacia abajo."
    )
