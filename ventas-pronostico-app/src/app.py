import streamlit as st
import pandas as pd
from utils.excel_importer import import_excel
from utils.charts import mostrar_grafico_clustered_line
from models.forecasting import ForecastingModel

st.set_page_config(layout="wide")

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

        # -------- FILTROS --------
        dpgs = data_pivot['DPG'].unique().tolist()
        dpg_seleccionado = st.selectbox("Selecciona un DPG para graficar y visualizar", options=dpgs)
        skus_filtrados = data_pivot[data_pivot['DPG'] == dpg_seleccionado]['SKU'].unique().tolist()
        sku_seleccionado = st.selectbox("Selecciona un producto (SKU) para graficar y visualizar", options=skus_filtrados)

        # Filtrar la tabla para el DPG y SKU seleccionado
        df_filtro = data_pivot[(data_pivot['DPG'] == dpg_seleccionado) & (data_pivot['SKU'] == sku_seleccionado)].copy()
        meses = [col for col in df_filtro.columns if col not in ['DPG', 'SKU']]

        # Inicializar ajustes manuales en session_state
        key_ajustes = f"ajustes_{dpg_seleccionado}_{sku_seleccionado}"
        if key_ajustes not in st.session_state:
            st.session_state[key_ajustes] = pd.DataFrame({
                'DPG': [dpg_seleccionado],
                'SKU': [sku_seleccionado],
                **{mes: [0] for mes in meses}
            })

        # Construir tabla para mostrar y editar
        tabla = pd.DataFrame()
        # Fila Input (no editable)
        fila_input = df_filtro.copy()
        fila_input.insert(2, 'Tipo', 'Input')
        # Fila Ajuste Manual (editable)
        fila_ajuste = st.session_state[key_ajustes].copy()
        fila_ajuste.insert(2, 'Tipo', 'Ajuste Manual')
        # Fila Total (no editable)
        fila_total = fila_input[meses].values + fila_ajuste[meses].values
        fila_total = pd.DataFrame({
            'DPG': [dpg_seleccionado],
            'SKU': [sku_seleccionado],
            'Tipo': ['Total'],
            **{mes: [fila_total[0][i]] for i, mes in enumerate(meses)}
        })

        tabla = pd.concat([fila_input, fila_ajuste, fila_total], ignore_index=True)

        # Mostrar y editar solo la fila de Ajuste Manual
        st.write("Datos Según DPG y SKU:")
        disabled_rows = (tabla['Tipo'] != 'Ajuste Manual').tolist()
        edited_tabla = st.data_editor(
            tabla,
            disabled=disabled_rows,
            key=f"editor_{dpg_seleccionado}_{sku_seleccionado}"
        )

        # SIEMPRE usar el valor editado para la siguiente tabla y gráfico
        nueva_ajuste = edited_tabla[edited_tabla['Tipo'] == 'Ajuste Manual'].drop(columns=['Tipo']).reset_index(drop=True)

        # Construir la fila Total usando el ajuste recién editado
        fila_total = fila_input[meses].values + nueva_ajuste[meses].values
        fila_total = pd.DataFrame({
            'DPG': [dpg_seleccionado],
            'SKU': [sku_seleccionado],
            'Tipo': ['Total'],
            **{mes: [fila_total[0][i]] for i, mes in enumerate(meses)}
        })

        # Reconstruir la tabla para mostrar, usando el ajuste recién editado
        tabla_actualizada = pd.concat([fila_input, nueva_ajuste.assign(Tipo='Ajuste Manual'), fila_total], ignore_index=True)

        # --- GRÁFICO ---
        df_plot = pd.melt(tabla_actualizada[tabla_actualizada['Tipo'].isin(['Input', 'Total'])], 
                        id_vars=['Tipo'], 
                        value_vars=meses, 
                        var_name='Month', 
                        value_name='Valor')
        df_plot['Month'] = pd.to_datetime(df_plot['Month'], format='%Y-%m')
        color_map = {'Input': 'orange', 'Total': 'green'}
        import altair as alt
        chart = alt.Chart(df_plot).mark_line(point=True).encode(
            x=alt.X('Month:T', title='Mes'),
            y=alt.Y('Valor:Q', title='Cantidad'),
            color=alt.Color('Tipo:N', scale=alt.Scale(domain=list(color_map.keys()), range=list(color_map.values())))
        ).properties(title=f"Evolución para DPG {dpg_seleccionado} y SKU {sku_seleccionado}")
        st.altair_chart(chart, use_container_width=True)

        # Solo después, actualiza el session_state para persistencia
        st.session_state[key_ajustes] = nueva_ajuste

if __name__ == "__main__":
    main()