# src/utils/charts.py

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression # Para las tendencias lineales

def plot_forecast_chart(df_data, forecast_horizon=6):
    """
    Genera un gráfico interactivo con datos históricos, suavizados,
    pronósticos y tendencias lineales, similar al ejemplo proporcionado.

    Args:
        df_data (pd.DataFrame): DataFrame que contiene los datos históricos
                                (ds, y) y los pronósticos (yhat, yhat_lower, yhat_upper).
                                Debería incluir también columnas para 'Orders' (si aplica),
                                'Smoothed Sales', 'Smoothed Orders',
                                'Linear (Smoothed Sales)', 'Linear (Smoothed Orders)',
                                y 'Final Forecast'.
        forecast_horizon (int): Número de meses pronosticados.
    
    Returns:
        plotly.graph_objects.Figure: Objeto Figure de Plotly.
    """

    fig = go.Figure()

    # Asegúrate de que 'ds' es datetime
    df_data['ds'] = pd.to_datetime(df_data['ds'])

    # --- Preprocesamiento para Suavizado y Tendencias (si no se hizo antes) ---
    # Es crucial que estas columnas existan en df_data antes de graficar.
    # Si no las generas antes, puedes hacer un suavizado básico aquí.

    # Ejemplo de suavizado (Media móvil simple)
    if 'Smoothed Sales' not in df_data.columns:
        df_data['Smoothed Sales'] = df_data['y'].rolling(window=3, min_periods=1, center=True).mean()
    
    # Si tienes 'Orders', haz lo mismo
    # if 'Orders' in df_data.columns and 'Smoothed Orders' not in df_data.columns:
    #     df_data['Smoothed Orders'] = df_data['Orders'].rolling(window=3, min_periods=1, center=True).mean()

    # Ejemplo de tendencia lineal (solo sobre el periodo histórico de 'y' suavizada)
    if 'Linear (Smoothed Sales)' not in df_data.columns:
        # Define el período histórico (asume que 'y' tiene valores no NaN en el histórico)
        df_hist_smoothed = df_data[df_data['y'].notna()].copy()
        
        if not df_hist_smoothed.empty:
            df_hist_smoothed['Days'] = (df_hist_smoothed['ds'] - df_hist_smoothed['ds'].min()).dt.days
            
            # Asegúrate de que 'y' y 'Smoothed Sales' no sean NaN para la regresión
            df_hist_smoothed_valid = df_hist_smoothed.dropna(subset=['Smoothed Sales'])

            if not df_hist_smoothed_valid.empty:
                model_sales = LinearRegression()
                X_sales = df_hist_smoothed_valid['Days'].values.reshape(-1, 1)
                y_sales = df_hist_smoothed_valid['Smoothed Sales'].values
                model_sales.fit(X_sales, y_sales)
                
                # Proyectar la línea de tendencia sobre todas las fechas
                df_data['Linear (Smoothed Sales)'] = model_sales.predict(
                    ((df_data['ds'] - df_hist_smoothed['ds'].min()).dt.days).values.reshape(-1, 1)
                )
            else:
                df_data['Linear (Smoothed Sales)'] = np.nan # No se pudo calcular la tendencia
        else:
            df_data['Linear (Smoothed Sales)'] = np.nan # No hay datos históricos para calcular la tendencia

    # Si tienes 'Orders' y su suavizado, haz lo mismo para 'Linear (Smoothed Orders)'
    # if 'Orders' in df_data.columns and 'Linear (Smoothed Orders)' not in df_data.columns:
    #     df_hist_smoothed_orders = df_data[df_data['Orders'].notna()].copy()
    #     if not df_hist_smoothed_orders.empty:
    #         df_hist_smoothed_orders['Days'] = (df_hist_smoothed_orders['ds'] - df_hist_smoothed_orders['ds'].min()).dt.days
    #         df_hist_smoothed_orders_valid = df_hist_smoothed_orders.dropna(subset=['Smoothed Orders'])
    #         if not df_hist_smoothed_orders_valid.empty:
    #             model_orders = LinearRegression()
    #             X_orders = df_hist_smoothed_orders_valid['Days'].values.reshape(-1, 1)
    #             y_orders = df_hist_smoothed_orders_valid['Smoothed Orders'].values
    #             model_orders.fit(X_orders, y_orders)
    #             df_data['Linear (Smoothed Orders)'] = model_orders.predict(
    #                 ((df_data['ds'] - df_hist_smoothed_orders['ds'].min()).dt.days).values.reshape(-1, 1)
    #             )
    #         else:
    #             df_data['Linear (Smoothed Orders)'] = np.nan
    #     else:
    #         df_data['Linear (Smoothed Orders)'] = np.nan


    # --- Trazar cada serie en el gráfico ---

    # Ventas Históricas
    fig.add_trace(go.Scatter(x=df_data['ds'], y=df_data['y'], mode='lines', name='Sales',
                             line=dict(color='blue', width=2)))

    # Órdenes Históricas (si la columna 'Orders' existe en df_data)
    if 'Orders' in df_data.columns:
        fig.add_trace(go.Scatter(x=df_data['ds'], y=df_data['Orders'], mode='lines', name='Orders',
                                 line=dict(color='green', width=2)))

    # Ventas Suavizadas
    fig.add_trace(go.Scatter(x=df_data['ds'], y=df_data['Smoothed Sales'], mode='lines', name='Smoothed Sales',
                             line=dict(color='blue', dash='dash', width=1.5)))

    # Órdenes Suavizadas (si la columna 'Smoothed Orders' existe)
    if 'Smoothed Orders' in df_data.columns:
        fig.add_trace(go.Scatter(x=df_data['ds'], y=df_data['Smoothed Orders'], mode='lines', name='Smoothed Orders',
                                 line=dict(color='green', dash='dash', width=1.5)))
    
    # Tendencia Lineal (Smoothed Sales)
    if 'Linear (Smoothed Sales)' in df_data.columns:
        fig.add_trace(go.Scatter(x=df_data['ds'], y=df_data['Linear (Smoothed Sales)'], mode='lines', name='Linear (Smoothed Sales)',
                                 line=dict(color='lightblue', dash='dot', width=1.5)))

    # Tendencia Lineal (Smoothed Orders)
    if 'Linear (Smoothed Orders)' in df_data.columns:
        fig.add_trace(go.Scatter(x=df_data['ds'], y=df_data['Linear (Smoothed Orders)'], mode='lines', name='Linear (Smoothed Orders)',
                                 line=dict(color='lightgreen', dash='dot', width=1.5)))

    # Pronóstico Estadístico de Ventas (yhat de Prophet)
    # Asegúrate de que 'yhat' sea solo para el periodo de pronóstico, o que los históricos sean NaN
    fig.add_trace(go.Scatter(x=df_data['ds'], y=df_data['yhat'], mode='lines', name='Statistical Forecast Sales',
                             line=dict(color='darkorange', width=2)))
    
    # Intervalo de confianza del pronóstico
    fig.add_trace(go.Scatter(
        x=df_data['ds'],
        y=df_data['yhat_upper'],
        mode='lines',
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=df_data['ds'],
        y=df_data['yhat_lower'],
        mode='lines',
        fillcolor='rgba(255,165,0,0.1)', # Sombreado naranja suave
        fill='tonexty',
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip'
    ))

    # Pronóstico Final (si existe la columna 'Final Forecast')
    if 'Final Forecast' in df_data.columns:
        fig.add_trace(go.Scatter(x=df_data['ds'], y=df_data['Final Forecast'], mode='lines', name='Final Forecast',
                                 line=dict(color='gold', width=3)))


    # Configuración del Layout
    fig.update_layout(
        title_text='Pronóstico de Ventas y Órdenes a lo Largo del Tiempo',
        xaxis_title='Mes',
        yaxis_title='Cantidad',
        hovermode='x unified', # Muestra la información de todas las líneas en el mismo punto x
        template='plotly_white', # Puedes probar 'plotly_dark', 'ggplot2', 'seaborn'
        height=600, # Altura del gráfico
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(
            type='date',
            tickformat='%b-%y', # Formato "Ago-23"
            tickangle=-45 # Rotar etiquetas
        )
    )

    # Añadir una línea vertical para separar el histórico del pronóstico
    # Encuentra la última fecha del histórico (donde 'y' no es NaN)
    last_historical_date = df_data[df_data['y'].notna()]['ds'].max()
    if pd.notna(last_historical_date):
        # Convertir la fecha a milisegundos desde la época para Plotly
        # Esto es más robusto para add_vline cuando se usa annotation_position
        last_historical_date_ms = last_historical_date.timestamp() * 1000

        fig.add_vline(x=last_historical_date_ms, line_width=1, line_dash="dash", line_color="gray",
                      annotation_text="Fin Histórico / Inicio Pronóstico",
                      annotation_position="top right")

    return fig