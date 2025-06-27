# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging # Importar logging

from .routers import clients, skus, keyfigures, sales_forecast

# Configurar el nivel de logging para que los mensajes INFO sean visibles
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Wirebi Forecasting API",
    description="API para gestionar datos de ventas, pronósticos y ajustes.",
    version="0.1.0",
)

# Configuración de CORS
origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://127.0.0.1",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clients.router)
app.include_router(skus.router)
app.include_router(keyfigures.router)
app.include_router(sales_forecast.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Wirebi Forecasting API"}