from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer

from src.auth.router import router as auth_router
from src.plant_identification.router import router as plant_router

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

app = FastAPI(
    title="API de Flora find ",
    description="API para manejo de autenticación, usuarios e identificación de plantas",
    version="1.0.0",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# Incluir routers
app.include_router(auth_router)
app.include_router(plant_router, prefix="/plants", tags=["plantas"])

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
