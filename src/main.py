from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer
import os

from src.auth.router import router as auth_router
from src.plant_identification.router import router as plant_router

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

app = FastAPI(
    title="API de Flora find ",
    description="API para manejo de autenticación, usuarios e identificación de plantas",
    version="1.0.0",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.swagger_ui_init_oauth = {"usePkceWithAuthorizationCodeGrant": True}

app.include_router(auth_router)
app.include_router(plant_router, prefix="/plants", tags=["plantas"])

# Usar ruta absoluta para los templates
templates_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=templates_path)

original_openapi = app.openapi
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = original_openapi()
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
