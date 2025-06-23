from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware # Importa el middleware CORS
from sqlalchemy.orm import Session

from . import models
from .database import engine, get_db
from .routers import clients, skus, keyfigures, sales_forecast # <-- ¡Asegúrate de que 'sales_forecast' esté aquí!

# Crea las tablas en la base de datos (solo si no existen)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Wirebi Forecast API",
    description="API para gestionar datos de ventas históricas y pronósticos versionados.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# --- CONFIGURACIÓN CORS ---
origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://127.0.0.1",       # Añade esto
    "http://127.0.0.1:5173",  # Añade esto
    # Otros orígenes si tu frontend se desplegara en un dominio diferente
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- FIN CONFIGURACIÓN CORS ---


# Incluye los routers en la aplicación principal de FastAPI
app.include_router(clients.router)
app.include_router(skus.router)
app.include_router(keyfigures.router)
app.include_router(sales_forecast.router) # <-- ¡Asegúrate de que esta línea exista!

@app.get("/")
async def root():
    return {"message": "Welcome to the Wirebi Forecast API!"}

# Puedes agregar más endpoints aquí, como autenticación, etc.