import altair as alt
import pandas as pd
import streamlit as st

def mostrar_grafico_clustered_line(data, data_ajustada, forecast=None):
    # Prepara los datos en formato largo
    data_long = data.melt(
        id_vars=['DPG', 'SKU', 'Month'],
        value_vars=['Sum of Quantity'],
        var_name='Tipo',
        value_name='Valor'
    )
    data_long['Tipo'] = 'Original'

    chart_data = [data_long]

    if data_ajustada is not None:
        data_ajustada_long = data_ajustada.melt(
            id_vars=['DPG', 'SKU'],
            var_name='Month',
            value_name='Valor'
        )
        data_ajustada_long['Tipo'] = 'Ajustado'
        data_ajustada_long['Month'] = pd.to_datetime(data_ajustada_long['Month'], format='%Y-%m')
        chart_data.append(data_ajustada_long)

    if forecast is not None:
        forecast_long = forecast.melt(
            id_vars=['DPG', 'SKU'],
            var_name='Month',
            value_name='Valor'
        )
        forecast_long['Tipo'] = 'Pronóstico'
        forecast_long['Month'] = pd.to_datetime(forecast_long['Month'], format='%Y-%m')
        chart_data.append(forecast_long)

    chart_data = pd.concat(chart_data, ignore_index=True)


    producto = st.selectbox("Selecciona un producto para graficar", chart_data['SKU'].unique())
    dpg = st.selectbox("Selecciona un DPG para graficar", chart_data['DPG'].unique())

    chart_data_sel = chart_data[(chart_data['SKU'] == producto) & (chart_data['DPG'] == dpg)]

    base = alt.Chart(chart_data_sel).encode(
    x=alt.X(
        'Month:T',
        title='Mes',
        axis=alt.Axis(
            format='%Y-%m',           # Muestra solo año-mes
            tickCount='month',        # Un tick por mes
            labelAngle=-45            # Opcional: inclina las etiquetas
        )
    )
)

    columnas = base.mark_bar().encode(
        y=alt.Y('Valor:Q', title='Cantidad'),
        color=alt.Color('Tipo:N', 
            scale=alt.Scale(
                domain=['Original', 'Ajustado'],
                range=['#4C78A8', '#F58518']
            ),
            legend=alt.Legend(title="Tipo de dato")
        )
    ).transform_filter(
        alt.FieldOneOfPredicate(field='Tipo', oneOf=['Original', 'Ajustado'])
    )

    linea = base.mark_line(point=True, size=3).encode(
        y='Valor:Q',
        color=alt.Color('Tipo:N', 
            scale=alt.Scale(
                domain=['Pronóstico'],
                range=["#12E262"]
            ),
            legend=None
        )
    ).transform_filter(
        alt.datum.Tipo == 'Pronóstico'
    )

    st.altair_chart(columnas + linea, use_container_width=True)