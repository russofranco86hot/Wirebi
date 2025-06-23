from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Variables de entorno para la base de datos
    DATABASE_URL: str
    
    # Configura la ruta al archivo .env
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

# Crea una instancia de Settings para usar en la aplicación
settings = Settings()