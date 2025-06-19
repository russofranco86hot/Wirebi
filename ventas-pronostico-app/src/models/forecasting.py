import pandas as pd
from prophet import Prophet
from sklearn.linear_model import LinearRegression
import numpy as np

class TimeSeriesForecaster:
    def __init__(self):
        self.model = Prophet(
            seasonality_mode='multiplicative',
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False
        )

    def fit_and_predict(self, df_historical, periods_to_forecast):
        if not all(col in df_historical.columns for col in ['ds', 'y']):
            raise ValueError("DataFrame histórico debe contener columnas 'ds' y 'y'.")

        self.model.fit(df_historical[['ds', 'y']])
        future = self.model.make_future_dataframe(periods=periods_to_forecast, freq='M')
        forecast = self.model.predict(future)

        # Unir histórico y pronóstico
        combined_df = pd.merge(df_historical[['ds', 'y']], forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']], on='ds', how='outer')

        # Suavizado de ventas
        combined_df['Smoothed Sales'] = combined_df['y'].rolling(window=3, min_periods=1, center=True).mean()

        # Tendencia lineal (ventas suavizadas)
        df_hist_smoothed = combined_df[combined_df['y'].notna()].copy()
        if not df_hist_smoothed.empty:
            df_hist_smoothed['Days'] = (df_hist_smoothed['ds'] - df_hist_smoothed['ds'].min()).dt.days
            df_hist_smoothed_valid = df_hist_smoothed.dropna(subset=['Smoothed Sales'])
            if not df_hist_smoothed_valid.empty:
                model_linear = LinearRegression()
                X_linear = df_hist_smoothed_valid['Days'].values.reshape(-1, 1)
                y_linear = df_hist_smoothed_valid['Smoothed Sales'].values
                model_linear.fit(X_linear, y_linear)
                combined_df['Linear (Smoothed Sales)'] = model_linear.predict(
                    ((combined_df['ds'] - df_hist_smoothed['ds'].min()).dt.days).values.reshape(-1, 1)
                )
            else:
                combined_df['Linear (Smoothed Sales)'] = np.nan
        else:
            combined_df['Linear (Smoothed Sales)'] = np.nan

        # Final Forecast (puedes personalizar la lógica)
        combined_df['Final Forecast'] = combined_df['yhat']

        return combined_df