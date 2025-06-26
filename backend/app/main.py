# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Importar CORSMiddleware

from .routers import clients, skus, keyfigures, sales_forecast

app = FastAPI(
    title="Wirebi Forecasting API",
    description="API para gestionar datos de ventas, pronósticos y ajustes.",
    version="0.1.0",
)

# Configuración de CORS
origins = [
    "http://localhost",
    "http://localhost:5173",  # Origen común de Vite
    "http://127.0.0.1",       # Otra forma común de acceder a localhost
    "http://127.0.0.1:5173",  # Origen común de Vite con 127.0.0.1
    # Puedes añadir otros orígenes aquí si tu frontend se aloja en un dominio diferente
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Permite todos los encabezados
)

app.include_router(clients.router)
app.include_router(skus.router)
app.include_router(keyfigures.router)
app.include_router(sales_forecast.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Wirebi Forecasting API"}