import pandas as pd

class ForecastingModel:
    def __init__(self, data):
        self.data = data
        self.model = None  # No se usa en este ejemplo

    def train_model(self):
        # En este ejemplo, no entrenamos nada
        pass

    def predict_sales(self, future_data):
        # Supongamos que tus columnas son: 'DPG', 'SKU', 'Month', 'Sum of Quantity'
        # Calculamos el promedio histórico por DPG y SKU
        avg_sales = (
            self.data.groupby(['DPG', 'SKU'])['Sum of Quantity']
            .mean()
            .reset_index()
            .rename(columns={'Sum of Quantity': 'Forecast'})
        )

        # Cruzamos cada combinación con los meses futuros
        future = future_data.copy()
        future['key'] = 1
        avg_sales['key'] = 1
        pred = pd.merge(avg_sales, future, on='key').drop('key', axis=1)
        pred = pred[['DPG', 'SKU', 'Month', 'Forecast']]
        return pred