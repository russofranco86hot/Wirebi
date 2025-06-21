import streamlit as st
import pandas as pd
from utils.excel_importer import import_excel
from utils.charts import mostrar_grafico_clustered_line
from models.forecasting import ForecastingModel

st.set_page_config(layout="wide")
def reset_pronostico():
    st.session_state['pronostico_df'] = None
    
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
        dpg_seleccionado = st.selectbox(
            "Selecciona un DPG para graficar y visualizar",
            options=dpgs,
            key="dpg_select",
            on_change=reset_pronostico
        )
        skus_filtrados = data_pivot[data_pivot['DPG'] == dpg_seleccionado]['SKU'].unique().tolist()
        sku_seleccionado = st.selectbox(
            "Selecciona un producto (SKU) para graficar y visualizar",
            options=skus_filtrados,
            key="sku_select",
            on_change=reset_pronostico
        )
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
        # Fila Input (no editable) - siempre basada en los datos originales
        fila_input = df_filtro.copy()
        fila_input.insert(2, 'Tipo', 'Input')

        # Fila Ajuste Manual (editable) - USAMOS st.session_state[key_ajustes] DIRECTAMENTE
        fila_ajuste = st.session_state[key_ajustes].copy()
        fila_ajuste.insert(2, 'Tipo', 'Ajuste Manual')

        # Fila Total (no editable) - Calculada con los valores actuales de fila_input y fila_ajuste
        fila_total_valores = fila_input[meses].values + fila_ajuste[meses].values
        fila_total = pd.DataFrame({
            'DPG': [dpg_seleccionado],
            'SKU': [sku_seleccionado],
            'Tipo': ['Total'],
            **{mes: [fila_total_valores[0][i]] for i, mes in enumerate(meses)}
        })

        # Combinar las filas para mostrar en st.data_editor
        tabla_para_editor = pd.concat([fila_input, fila_ajuste, fila_total], ignore_index=True)

        # Mostrar y editar solo la fila de Ajuste Manual
        st.write("Datos Según DPG y SKU:")
        disabled_rows = (tabla_para_editor['Tipo'] != 'Ajuste Manual').tolist()
        
        edited_tabla = st.data_editor(
            tabla_para_editor,
            disabled=disabled_rows,
            key=f"editor_{dpg_seleccionado}_{sku_seleccionado}"
        )

        # --- Punto CRÍTICO de CAMBIO ---
        # 1. Extraer la fila de 'Ajuste Manual' del DataFrame editado
        nueva_ajuste = edited_tabla[edited_tabla['Tipo'] == 'Ajuste Manual'].drop(columns=['Tipo']).reset_index(drop=True)
        
        # 2. **ACTUALIZAR st.session_state INMEDIATAMENTE**
        if not nueva_ajuste.equals(st.session_state[key_ajustes]):
            st.session_state[key_ajustes] = nueva_ajuste
            st.rerun()

        # 3. Reconstruir la fila 'Total' usando los datos más recientes (que ahora están en session_state)
        fila_ajuste_actualizada = st.session_state[key_ajustes].copy()
        fila_total_valores_actualizados = fila_input[meses].values + fila_ajuste_actualizada[meses].values
        fila_total_actualizada = pd.DataFrame({
            'DPG': [dpg_seleccionado],
            'SKU': [sku_seleccionado],
            'Tipo': ['Total'],
            **{mes: [fila_total_valores_actualizados[0][i]] for i, mes in enumerate(meses)}
        })

        # Reconstruir la tabla final para el gráfico, usando los ajustes más recientes del session_state
        tabla_para_grafico = pd.concat([fila_input, fila_ajuste_actualizada.assign(Tipo='Ajuste Manual'), fila_total_actualizada], ignore_index=True)

        # --- GRÁFICO UNIFICADO ---
        df_plot = pd.melt(tabla_para_grafico[tabla_para_grafico['Tipo'].isin(['Input', 'Total'])], 
                            id_vars=['Tipo'], 
                            value_vars=meses, 
                            var_name='Month', 
                            value_name='Valor')
        df_plot['Month'] = pd.to_datetime(df_plot['Month'], format='%Y-%m')
        color_map = {'Input': 'orange', 'Total': 'green'}

        # Estado para guardar el pronóstico
        if 'pronostico_df' not in st.session_state:
            st.session_state['pronostico_df'] = None

        n_meses_pronostico = st.number_input("¿Cuántos meses quieres pronosticar?", min_value=1, max_value=48, value=24)

        if st.button("Pronosticar"):
            # Tomar la fila "Total" como base histórica
            fila_total_hist = tabla_para_grafico[tabla_para_grafico['Tipo'] == 'Total']
            serie_hist = fila_total_hist.melt(
                id_vars=['DPG', 'SKU', 'Tipo'],
                value_vars=meses,
                var_name='Month',
                value_name='Valor'
            ).sort_values('Month')
            serie_hist['Month'] = pd.to_datetime(serie_hist['Month'], format='%Y-%m')
            serie_hist = serie_hist[['Month', 'Valor']].rename(columns={'Month': 'ds', 'Valor': 'y'})

            # Generar fechas futuras
            last_date = serie_hist['ds'].max()
            future_dates = pd.date_range(
                start=last_date + pd.offsets.MonthBegin(1),
                periods=n_meses_pronostico,
                freq='MS'
            )
            future_df = pd.DataFrame({'ds': future_dates})

            # Pronóstico (usa tu modelo, aquí ejemplo simple de promedio)
            y_mean = serie_hist['y'].mean()
            forecast = future_df.copy()
            forecast['y'] = y_mean  # <-- aquí pon tu modelo real

            # Guardar pronóstico en session_state para usarlo en el gráfico y la tabla
            forecast['DPG'] = dpg_seleccionado
            forecast['SKU'] = sku_seleccionado
            st.session_state['pronostico_df'] = forecast.copy()

        import altair as alt
        base = alt.Chart(df_plot).mark_line(point=True).encode(
            x=alt.X('Month:T', title='Mes'),
            y=alt.Y('Valor:Q', title='Cantidad'),
            color=alt.Color('Tipo:N', scale=alt.Scale(domain=list(color_map.keys()), range=list(color_map.values())))
        )

        # Si hay pronóstico, agrégalo en rojo
        if st.session_state['pronostico_df'] is not None:
            pronostico_chart = alt.Chart(st.session_state['pronostico_df']).mark_line(point=True, color='red').encode(
                x=alt.X('ds:T', title='Mes'),
                y=alt.Y('y:Q', title='Cantidad')
            )
            chart = base + pronostico_chart
        else:
            chart = base

        st.altair_chart(chart, use_container_width=True)

        # --- TABLA DE PRONÓSTICO ---
        if st.session_state['pronostico_df'] is not None:
            df_forecast = st.session_state['pronostico_df'].copy()
            df_forecast['ds'] = df_forecast['ds'].dt.strftime('%Y-%m')
            tabla_pronostico = df_forecast.pivot_table(
                index=['DPG', 'SKU'],
                columns='ds',
                values='y'
            ).reset_index()
            st.write("Pronóstico generado para el DPG y SKU seleccionados:")
            st.dataframe(tabla_pronostico)

if __name__ == "__main__":
    main()