import streamlit as st
import pandas as pd
import numpy as np
import math
import logging
import traceback
import time
import warnings
from datetime import datetime
import plotly.graph_objects as go
import io

pd.set_option("styler.render.max_elements", 400000)  # O un valor mayor al de tus celdas
warnings.filterwarnings("ignore")


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

from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX
from prophet import Prophet
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_percentage_error

logging.basicConfig(filename='forecast_errors.log', level=logging.ERROR,
                    format='%(asctime)s:%(levelname)s:%(message)s')

st.title("WIREBI FEU With Alerts - Forecast & Alerts Dashboard")

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
if uploaded_file is not None:
    start_time = time.time()
    try:
        df = pd.read_excel(uploaded_file)
        df['Month'] = pd.to_datetime(df['Month'])
        st.write("Data Preview (puedes editar los valores temporalmente para ver el efecto en el forecast):")

        # Crea un filtro para cada columna
        df_filtered = df.copy()
        for col in df.columns:
            if df[col].dtype == 'object' or df[col].dtype.name == 'category':
                unique_vals = df[col].dropna().unique()
                selected = st.multiselect(f"{col} Filter", options=unique_vals, default=unique_vals)
                df_filtered = df_filtered[df_filtered[col].isin(selected)]
            elif pd.api.types.is_numeric_dtype(df[col]):
                min_val, max_val = float(df[col].min()), float(df[col].max())
                selected = st.slider(f"{col} Filter", min_value=min_val, max_value=max_val, value=(min_val, max_val))
                df_filtered = df_filtered[df_filtered[col].between(*selected)]
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                min_date, max_date = df[col].min(), df[col].max()
                selected = st.date_input(f"{col} Filter", value=(min_date, max_date))
                if isinstance(selected, tuple) and len(selected) == 2:
                    # Convierte los valores seleccionados a datetime
                    left = pd.to_datetime(selected[0])
                    right = pd.to_datetime(selected[1])
                    df_filtered = df_filtered[df_filtered[col].between(left, right)]

        # Editor interactivo sobre el DataFrame filtrado
        df_editado = st.data_editor(
            df_filtered,
            num_rows="dynamic",
            use_container_width=True,
            key="input_editor"
        )

        # Detectar celdas modificadas
        # Normaliza tipos antes de comparar
        df_compare = df_filtered.copy()
        df_edit_compare = df_editado.copy()
        for col in df_compare.columns:
            if pd.api.types.is_datetime64_any_dtype(df_compare[col]):
                df_compare[col] = df_compare[col].astype(str)
                df_edit_compare[col] = pd.to_datetime(df_edit_compare[col], errors='coerce').astype(str)
            elif pd.api.types.is_numeric_dtype(df_compare[col]):
                df_compare[col] = pd.to_numeric(df_compare[col], errors='coerce')
                df_edit_compare[col] = pd.to_numeric(df_edit_compare[col], errors='coerce')
            else:
                df_compare[col] = df_compare[col].astype(str)
                df_edit_compare[col] = df_edit_compare[col].astype(str)

        mask = df_compare.ne(df_edit_compare)
        rows_modified = mask.any(axis=1)
        df_modificados = df_editado[rows_modified].copy()
        mask_modificados = mask[rows_modified]

        def highlight_mods(data, mask):
            return mask.replace({True: 'border: 2px solid orange;', False: ''})

        if not df_modificados.empty:
            st.write("Update rows (Orange border celds = updated):")
            styled = df_modificados.style.apply(lambda _: highlight_mods(df_modificados, mask_modificados), axis=None)
            st.dataframe(styled, use_container_width=True)
        else:
            st.info("There are not updated rows.")

        # Botón para ejecutar el forecast solo cuando el usuario lo desee
        if st.button("Forecast with the changes"):
            # Aquí va tu código de forecast, usando df_editado en vez de df
            # Por ejemplo:
            # results = tu_funcion_de_forecast(df_editado)
            st.success("¡Forecast Executed with Changes!")
            # ...mostrar resultados...

        # Usa df_editado para el forecast

        analysis_level = st.selectbox("Select Analysis Level", ["SKU/DPG", "SKU"])
        model_selection_details = []

        # --- Forecasting Functions ---
        def enrich_features(df, date_col='ds'):
            df = df.copy()
            df[date_col] = pd.to_datetime(df[date_col])
            df['time_index'] = df[date_col].map(datetime.toordinal)
            df['month'] = df[date_col].dt.month
            df['quarter'] = df[date_col].dt.quarter
            df['year'] = df[date_col].dt.year
            return df

        def exp_smooth_forecast(series, periods):
            try:
                model = ExponentialSmoothing(series, trend='add', seasonal='add', seasonal_periods=12)
                fitted = model.fit(optimized=True, maxiter=500, initialization_method='estimated')
                return fitted.forecast(periods)
            except Exception:
                fallback_val = np.mean(series.iloc[-6:]) if len(series) >= 6 else np.mean(series)
                return [fallback_val] * periods

        def croston(ts, extra_periods=1, alpha=0.1):
            ts = np.array(ts)
            n = len(ts)
            nonzero_indices = np.where(ts > 0)[0]
            if nonzero_indices.size == 0:
                return [0] * extra_periods, 0
            first_nonzero = nonzero_indices[0]
            a = ts[first_nonzero]
            p = first_nonzero + 1
            for i in range(first_nonzero + 1, n):
                if ts[i] > 0:
                    a = alpha * ts[i] + (1 - alpha) * a
                    p = alpha * (i - first_nonzero) + (1 - alpha) * p
            overall_forecast = a / p if p != 0 else 0
            forecast_extension = [overall_forecast] * extra_periods
            return forecast_extension, overall_forecast

        def croston_forecast(data, periods=24):
            forecast, _ = croston(data, extra_periods=periods)
            return forecast

        def prepare_data(df, sku, dpg):
            df_agg = df.groupby('Month', as_index=False)['Sum of Quantity'].sum()
            full_range = pd.date_range(start=df_agg['Month'].min(), end=df_agg['Month'].max(), freq='MS')
            df_agg = df_agg.set_index('Month').reindex(full_range, fill_value=0).reset_index()
            df_agg.rename(columns={'index': 'Month'}, inplace=True)
            df_agg['SKU'] = sku
            df_agg['DPG'] = dpg
            df_agg['KeyFigure'] = 'Orders'
            df_agg['Sum of Quantity'] = df_agg['Sum of Quantity'].fillna(0)
            df_agg['Month'] = df_agg['Month'].dt.strftime('%Y-%m-%d')
            non_zero = df_agg['Sum of Quantity'].ne(0)
            if non_zero.any():
                df_agg = df_agg.loc[non_zero.idxmax():non_zero[::-1].idxmax()]
            return df_agg

        def get_forecast_start(historical_records):
            current_month = pd.Timestamp(datetime.today().replace(day=1))
            last_hist = pd.to_datetime(historical_records[-1]['Month']) if historical_records else current_month - pd.DateOffset(months=1)
            forecast_start = last_hist + pd.DateOffset(months=1)
            return max(forecast_start, current_month)

        def evaluate_models(sales_series, forecast_horizon=24):
            candidate_scores = {}
            best_score = np.inf
            best_forecast = None
            best_model_name = ""
            if sales_series['y'].sum() == 0:
                candidate_scores["No Model"] = "Insufficient data"
                return [0] * forecast_horizon, "No Data", best_score, candidate_scores
            n_splits = 3
            split_size = len(sales_series) // (n_splits + 1)
            full_forecasts = {}
            models = ['Exponential Smoothing', 'SARIMAX', 'Prophet', 'XGBoost']
            for m_name in models:
                try:
                    mape_scores = []
                    for i in range(n_splits):
                        train = sales_series.iloc[:split_size*(i+1)]
                        test = sales_series.iloc[split_size*(i+1):split_size*(i+2)]
                        if m_name == 'Exponential Smoothing':
                            forecast_cv = exp_smooth_forecast(train['y'], len(test))
                        elif m_name == 'SARIMAX':
                            model_cv = SARIMAX(train['y'], order=(1,1,1), seasonal_order=(1,1,1,12),
                                               enforce_stationarity=False, enforce_invertibility=False)
                            fitted_model = model_cv.fit(disp=False)
                            forecast_cv = fitted_model.forecast(len(test))
                        elif m_name == 'Prophet':
                            if len(train) < 12:
                                raise ValueError("Not enough data for Prophet")
                            m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
                            m.fit(train)
                            forecast_df = m.predict(test[['ds']])
                            forecast_cv = forecast_df['yhat'].values
                        elif m_name == 'XGBoost':
                            train_enriched = enrich_features(train, date_col='ds')
                            test_enriched = enrich_features(test, date_col='ds')
                            x_train = train_enriched[['time_index', 'month', 'quarter', 'year']]
                            y_train = train_enriched['y'].values
                            x_test = test_enriched[['time_index', 'month', 'quarter', 'year']]
                            xgb = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.1)
                            xgb.fit(x_train, y_train)
                            forecast_cv = xgb.predict(x_test)
                        mape = mean_absolute_percentage_error(test['y'], forecast_cv)
                        mape_scores.append(mape)
                    avg_mape = np.mean(mape_scores)
                    candidate_scores[m_name] = avg_mape
                    # Full forecast
                    if m_name == 'Exponential Smoothing':
                        full_forecasts[m_name] = exp_smooth_forecast(sales_series['y'], forecast_horizon)
                    elif m_name == 'SARIMAX':
                        fitted_model = SARIMAX(sales_series['y'], order=(1,1,1), seasonal_order=(1,1,1,12),
                                               enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
                        full_forecasts[m_name] = fitted_model.forecast(forecast_horizon)
                    elif m_name == 'Prophet':
                        if len(sales_series) < 12:
                            raise ValueError("Not enough data for Prophet (full series)")
                        m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
                        m.fit(sales_series)
                        future = m.make_future_dataframe(periods=forecast_horizon, freq='MS')
                        forecast_df = m.predict(future)
                        full_forecasts[m_name] = forecast_df['yhat'].iloc[-forecast_horizon:].values
                    elif m_name == 'XGBoost':
                        full_enriched = enrich_features(sales_series, date_col='ds')
                        x_train_full = full_enriched[['time_index','month','quarter','year']]
                        y_train_full = sales_series['y'].values
                        last_date = sales_series['ds'].max()
                        future_dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=forecast_horizon, freq='MS')
                        future_df = pd.DataFrame({'ds': future_dates})
                        future_df = enrich_features(future_df, date_col='ds')
                        x_future = future_df[['time_index','month','quarter','year']]
                        xgb = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.1)
                        xgb.fit(x_train_full, y_train_full)
                        full_forecasts[m_name] = xgb.predict(x_future)
                    if avg_mape < best_score:
                        best_score = avg_mape
                        best_model_name = m_name
                        best_forecast = full_forecasts[m_name]
                except Exception as e:
                    logging.error(f"{m_name} failed during CV: {e}\n{traceback.format_exc()}")
                    candidate_scores[m_name] = "Error"
                    continue
            # Ensemble
            ensemble_forecasts = []
            ensemble_weights = []
            for m_name, score in candidate_scores.items():
                if isinstance(score, (float, int)) and score > 0 and m_name in full_forecasts:
                    weight = 1 / score
                    ensemble_forecasts.append(np.array(full_forecasts[m_name]))
                    ensemble_weights.append(weight)
            if ensemble_forecasts:
                ensemble_forecast = np.average(ensemble_forecasts, axis=0, weights=ensemble_weights)
                final_forecast = 0.5 * (np.array(best_forecast) + ensemble_forecast)
                best_model_name = "Ensemble (" + best_model_name + " + others)"
            else:
                final_forecast = best_forecast
            if final_forecast is None:
                try:
                    final_forecast = exp_smooth_forecast(sales_series['y'], forecast_horizon)
                    best_model_name = "Exponential Smoothing (Fallback)"
                except Exception:
                    fallback_val = np.mean(sales_series['y'].iloc[-6:]) if len(sales_series) >= 6 else np.mean(sales_series['y'])
                    final_forecast = [fallback_val] * forecast_horizon
                    best_model_name = "AvgLast6 (Fallback)"
            return final_forecast, best_model_name, best_score, candidate_scores

        def choose_model(sales_series, forecast_horizon=24):
            if len(sales_series) < 12:
                fallback_val = sales_series['y'].iloc[-1]
                candidate = {"Naive": "Insufficient observations"}
                return [fallback_val] * forecast_horizon, "Naive (Insufficient data)", np.inf, candidate
            total = len(sales_series)
            zeros = (sales_series['y'] == 0).sum()
            if total > 0 and (zeros / total > 0.5):
                candidate = {"Croston": "Intermittent demand > 50% zeros"}
                return croston_forecast(sales_series['y'].values, forecast_horizon), "Croston", np.inf, candidate
            else:
                return evaluate_models(sales_series, forecast_horizon)

        def process_forecast(sku, dpg, df, level):
            try:
                prepared_df = prepare_data(df, sku, dpg)
                historical_records = prepared_df.to_dict('records')
                forecast_start = get_forecast_start(historical_records)
                sales_series = prepared_df[['Month', 'Sum of Quantity']].copy()
                sales_series['ds'] = pd.to_datetime(sales_series['Month'])
                sales_series.rename(columns={'Sum of Quantity': 'y'}, inplace=True)
                sales_series.sort_values('ds', inplace=True)
                forecast_values, best_model, best_score, candidate_scores = choose_model(sales_series)
                # Alerts
                alerts = {}
                if any(keyword in best_model.lower() for keyword in ["fallback", "naive", "croston"]):
                    alerts["Fallback Alert"] = f"Model used: {best_model}"
                else:
                    alerts["Fallback Alert"] = ""
                if best_score > 0.3:
                    alerts["High MAPE Alert"] = f"MAPE: {best_score*100:.1f}%"
                else:
                    alerts["High MAPE Alert"] = ""
                historical_std = np.std(sales_series['y'])
                forecast_std = np.std(forecast_values)
                if historical_std > 0 and forecast_std < 0.1 * historical_std:
                    alerts["Flat Forecast Alert"] = f"Forecast std ({forecast_std:.2f}) < 10% of historical std ({historical_std:.2f})"
                else:
                    alerts["Flat Forecast Alert"] = ""
                try:
                    x_hist = np.arange(len(sales_series['y']))
                    hist_slope = np.polyfit(x_hist, sales_series['y'], 1)[0]
                    x_forecast = np.arange(len(forecast_values))
                    forecast_slope = np.polyfit(x_forecast, forecast_values, 1)[0]
                    if (hist_slope * forecast_slope < 0) or \
                       (hist_slope > 0 and forecast_slope < 0.5 * hist_slope) or \
                       (hist_slope < 0 and forecast_slope > 0.5 * hist_slope):
                        alerts["Trend Inconsistency Alert"] = f"Historical slope: {hist_slope:.2f}, Forecast slope: {forecast_slope:.2f}"
                    else:
                        alerts["Trend Inconsistency Alert"] = ""
                except Exception as e:
                    alerts["Trend Inconsistency Alert"] = f"Trend slope estimation error: {str(e)}"
                numeric_scores = [score for score in candidate_scores.values() if isinstance(score, (int, float)) and score > 0]
                if numeric_scores:
                    mean_score = np.mean(numeric_scores)
                    std_score = np.std(numeric_scores)
                    cv = std_score / mean_score if mean_score != 0 else 0
                    if cv > 0.2:
                        alerts["Model Consensus Alert"] = f"Candidate MAPEs CV: {cv:.2f}"
                    else:
                        alerts["Model Consensus Alert"] = ""
                else:
                    alerts["Model Consensus Alert"] = ""
                model_details = {
                    'Level': level,
                    'SKU': sku,
                    'DPG': dpg,
                    'Best_Model': best_model,
                    'Best_Score': best_score if best_score < np.inf else None,
                    'Candidate_Scores': str(candidate_scores)
                }
                model_details.update(alerts)
                model_selection_details.append(model_details)
                for record in historical_records:
                    record['ModelUsed'] = best_model
                forecast_dates = pd.date_range(start=forecast_start, periods=24, freq='MS')
                forecast_records = []
                for date, qty in zip(forecast_dates, forecast_values):
                    if not np.isfinite(qty):
                        qty = np.mean(sales_series['y'])
                    forecast_records.append({
                        'Month': date.strftime('%Y-%m-%d'),
                        'SKU': sku,
                        'DPG': dpg,
                        'KeyFigure': 'Forecast',
                        'Sum of Quantity': max(0, qty),
                        'ModelUsed': best_model
                    })
                return historical_records + forecast_records
            except Exception as e:
                logging.error(f"Critical error for SKU: {sku}, DPG: {dpg} - Error: {e}\n{traceback.format_exc()}")
                raise

        # --- Run analysis ---
        results = []
        if analysis_level == "SKU/DPG":
            for (sku, dpg), group in df.groupby(['SKU', 'DPG']):
                res = process_forecast(sku, dpg, group, level="DPG")
                if res:
                    results.extend(res)
        else:
            for sku, group in df.groupby('SKU'):
                res = process_forecast(sku, "ALL", group, level="SKU")
                if res:
                    results.extend(res)

        forecast_df = pd.DataFrame(results)
        model_selection_df = pd.DataFrame(model_selection_details)

        # Alerts tab
        alert_cols = ['SKU', 'Fallback Alert', 'High MAPE Alert', 'Flat Forecast Alert', 'Trend Inconsistency Alert', 'Model Consensus Alert']
        if analysis_level == "SKU/DPG":
            alert_cols.insert(1, 'DPG')
        alerts_df = model_selection_df[alert_cols]

        forecast_df["Sum of Quantity"] = pd.to_numeric(forecast_df["Sum of Quantity"], errors="coerce").astype(float)

        st.write("Forecast Results: ")



        # Forzar columnas numéricas a enteros
        for col in forecast_df.select_dtypes(include=[np.number]).columns:
            forecast_df[col] = forecast_df[col].fillna(0).astype(int)

        def to_excel_bytes(df):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            return output.getvalue()

        if st.button("Save edited Excel file"):
            output_bytes = to_excel_bytes(forecast_df)
            st.download_button(
                label="Download Excel file",
                data=output_bytes,
                file_name="forecast_editted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


        st.write("Model Selection & Alerts", model_selection_df)
        st.write("Alerts", alerts_df)

        # Visualization
        sku_options = forecast_df['SKU'].unique()
        selected_sku = st.selectbox("Select SKU for visualization", sku_options)
        subset = forecast_df[forecast_df['SKU'] == selected_sku]
        if analysis_level == "SKU/DPG":
            dpg_options = subset['DPG'].unique()
            selected_dpg = st.selectbox("Select DPG for visualization", dpg_options)
            subset = subset[subset['DPG'] == selected_dpg]
        historical = subset[subset['KeyFigure'] == 'Orders']
        forecasted = subset[subset['KeyFigure'] == 'Forecast']
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=historical['Month'], y=historical['Sum of Quantity'],
                                 mode='lines+markers', name='Historical Orders'))
        fig.add_trace(go.Scatter(x=forecasted['Month'], y=forecasted['Sum of Quantity'],
                                 mode='lines+markers', name='Forecast', line=dict(dash='dash')))
        st.plotly_chart(fig, use_container_width=True)
        st.write("Total processing time: {:.2f} seconds".format(time.time() - start_time))

    except Exception as e:
        st.error("An error occurred during execution.")
        st.error(f"Error: {e}")
        st.error(traceback.format_exc())
else:
    st.info("Please upload an Excel file to begin analysis.")