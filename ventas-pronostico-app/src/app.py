import streamlit as st
import pandas as pd
from utils.excel_importer import import_excel
from models.forecasting import ForecastingModel

# Ajustar el ancho de la página
st.set_page_config(layout="wide")

# Opcional: CSS para tablas más anchas
st.markdown("""
    <style>
        .stDataFrame, .stTable {
            width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)

def main():
    st.title("Aplicación de Pronóstico de Ventas")
    
    uploaded_file = st.file_uploader("Sube un archivo Excel con datos de clientes, productos y cantidades", type=["xlsx"])
    
    if uploaded_file is not None:
        data = import_excel(uploaded_file)
        st.write("Datos importados:")
        # Pivotear datos: cada mes como columna
        data_pivot = data.pivot_table(
            index=['DPG', 'SKU'],
            columns=data['Month'].dt.strftime('%Y-%m'),
            values='Sum of Quantity',
            aggfunc='sum'
        ).reset_index()
        st.dataframe(data_pivot)
        
        # Obtener el último mes de la columna 'Month'
        data['Month'] = pd.to_datetime(data['Month'])
        last_date = data['Month'].max()

        # Input para cantidad de meses a pronosticar
        n_months = st.number_input(
            "¿Cuántos meses quieres pronosticar?", min_value=1, max_value=48, value=12
        )


        model = ForecastingModel(data)
        model.train_model()
        
        if st.button("Realizar Pronóstico"):
            # Procesamiento SOLO al hacer clic en el botón
            data['Month'] = pd.to_datetime(data['Month'])
            last_date = data['Month'].max()
            future_dates = pd.date_range(
                start=last_date + pd.offsets.MonthBegin(1),
                periods=n_months,
                freq='MS'
            )
            future_data = pd.DataFrame({'Month': future_dates})

            predictions = model.predict_sales(future_data)
            st.write("Pronósticos de ventas:")
            # Pivotear predicciones: cada mes como columna
            pred_pivot = predictions.pivot_table(
                index=['DPG', 'SKU'],
                columns=predictions['Month'].dt.strftime('%Y-%m'),
                values='Forecast',
                aggfunc='sum'
            ).reset_index()
            st.dataframe(pred_pivot)

if __name__ == "__main__":
    main()