import streamlit as st
import pandas as pd
import numpy as np

from utils.excel_importer import import_excel
from utils.charts import plot_forecast_chart
from models.forecasting import TimeSeriesForecaster
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter

st.set_page_config(layout="wide")
st.markdown("""
    <style>
        .stDataFrame, .stTable {
            width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)

def main():
    st.title("WIREBI - Aplicación de Pronóstico de Ventas")

    uploaded_file = st.file_uploader("Sube un archivo Excel con datos de clientes, productos y cantidades", type=["xlsx"])
    
    if uploaded_file is not None:
        data = import_excel(uploaded_file)
        data['Month'] = pd.to_datetime(data['Month'])
        data_pivot = data.pivot_table(
            index=['DPG', 'SKU'],
            columns=data['Month'].dt.strftime('%Y-%m'),
            values='Sum of Quantity',
            aggfunc='sum'
        ).reset_index()

        # Inicializar ajustes y valores ajustados en session_state
        if 'ajustes' not in st.session_state:
            st.session_state['ajustes'] = data_pivot.copy()
            for col in data_pivot.columns:
                if col not in ['DPG', 'SKU']:
                    st.session_state['ajustes'][col] = 0
        if 'data_ajustada' not in st.session_state:
            st.session_state['data_ajustada'] = data_pivot.copy()

        st.write("Valores ajustados (original + ajuste):")
        st.dataframe(st.session_state['data_ajustada'])

        with st.form("ajustes_form"):
            st.write("Ajustes (edita aquí para sumar/restar cantidades):")
            ajustes_editados = st.data_editor(
                st.session_state['ajustes'],
                key="ajustes_editor"
            )
            aplicar = st.form_submit_button("Aplicar ajustes")

        if aplicar:
            st.session_state['ajustes'] = ajustes_editados
            data_ajustada = data_pivot.copy()
            for col in data_pivot.columns:
                if col not in ['DPG', 'SKU']:
                    data_ajustada[col] = data_pivot[col] + st.session_state['ajustes'][col]
            st.session_state['data_ajustada'] = data_ajustada
            st.warning("Si acabas de editar una celda, por favor presiona 'Aplicar ajustes' una segunda vez para que se apliquen los cambios.")

        n_months = st.number_input(
            "¿Cuántos meses quieres pronosticar?", min_value=1, max_value=48, value=12
        )

        data_ajustada_long = st.session_state['data_ajustada'].melt(
            id_vars=['DPG', 'SKU'],
            var_name='Month',
            value_name='Sum of Quantity'
        )
        data_ajustada_long = data_ajustada_long[~data_ajustada_long['Month'].isin(['index'])]
        data_ajustada_long['Month'] = pd.to_datetime(data_ajustada_long['Month'], format='%Y-%m')

        # Renombrar para Prophet
        df_prophet = data_ajustada_long.rename(columns={
            'Month': 'ds',
            'Sum of Quantity': 'y'
        })[['ds', 'y']]

        model = TimeSeriesForecaster()
        forecast_result = model.fit_and_predict(df_prophet, periods_to_forecast=n_months)

        if st.button("Realizar Pronóstico"):
            st.write("Pronóstico de ventas ajustado:")
            st.dataframe(forecast_result[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(n_months))

            st.subheader("Gráfico de Pronóstico de Ventas:")
            fig = plot_forecast_chart(forecast_result, n_months)
            st.plotly_chart(fig, use_container_width=True)

            # Descargar pronóstico en Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                forecast_result.to_excel(writer, index=False, sheet_name='Pronostico')
            output.seek(0)
            wb = load_workbook(output)
            ws = wb.active
            max_row = ws.max_row
            max_col = ws.max_column
            last_col_letter = get_column_letter(max_col)
            table_ref = f"A1:{last_col_letter}{max_row}"
            table = Table(displayName="Pronostico", ref=table_ref)
            style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,
                                   showLastColumn=False, showRowStripes=True, showColumnStripes=False)
            table.tableStyleInfo = style
            ws.add_table(table)
            output_final = BytesIO()
            wb.save(output_final)
            output_final.seek(0)
            st.download_button(
                label="Descargar pronóstico (XLSX)",
                data=output_final,
                file_name="pronostico_forecast.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()