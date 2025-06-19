# Ventas Pronóstico App

## Descripción
La aplicación "Ventas Pronóstico" es una herramienta web desarrollada con Python y Streamlit que permite a los usuarios realizar pronósticos de ventas. Los usuarios pueden importar un archivo Excel que contenga datos de clientes, productos y cantidades, y la aplicación procesará estos datos para generar pronósticos de ventas.

## Estructura del Proyecto
El proyecto está organizado de la siguiente manera:

```
ventas-pronostico-app
├── src
│   ├── app.py                # Punto de entrada de la aplicación Streamlit
│   ├── data
│   │   └── __init__.py       # Inicializa el módulo de datos
│   ├── utils
│   │   └── excel_importer.py  # Función para importar archivos Excel
│   └── models
│       └── forecasting.py     # Modelo de pronóstico de ventas
├── requirements.txt           # Dependencias del proyecto
└── README.md                  # Documentación del proyecto
```

## Instalación
Para instalar las dependencias necesarias, ejecute el siguiente comando en su terminal:

```
pip install -r requirements.txt
```

## Uso
1. Inicie la aplicación ejecutando el siguiente comando:

```
streamlit run src/app.py
```

2. En la interfaz de usuario, cargue su archivo Excel con los datos de ventas.
3. La aplicación procesará los datos y generará pronósticos de ventas.

## Contribuciones
Las contribuciones son bienvenidas. Si desea contribuir, por favor abra un issue o envíe un pull request.

## Licencia
Este proyecto está bajo la Licencia MIT.