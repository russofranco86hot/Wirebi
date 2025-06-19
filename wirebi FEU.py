import pandas as pd
import numpy as np
import os
import math
import logging
import traceback
import time
import warnings
from datetime import datetime
from tqdm import tqdm
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog


# Suppress warnings globally
warnings.filterwarnings("ignore")

# Import models
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX
from prophet import Prophet
from xgboost import XGBRegressor

# Import metrics
from sklearn.metrics import mean_absolute_percentage_error

# Configure logging
logging.basicConfig(filename='forecast_errors.log', level=logging.ERROR,
                    format='%(asctime)s:%(levelname)s:%(message)s')

print("Current working directory:", os.getcwd())

# File paths
#input_path = r'C:\Users\msilb\Desktop\DB.xlsx'
#output_path = r'C:\Users\msilb\Desktop\DBforecast.xlsx'

root = tk.Tk()
root.withdraw()  # Oculta la ventana principal

# Selección del archivo de entrada
input_path = filedialog.askopenfilename(
    title="Seleccione el archivo para importar la base de datos",
    filetypes=[("Archivos Excel", "*.xlsx")]
)
if not input_path:
    raise Exception("No se seleccionó ningún archivo.")

# Pregunta al usuario sobre la ubicación del archivo de salida
usar_mismo_path = messagebox.askyesno(
    "Guardar archivo de salida",
    "¿Desea guardar el archivo de salida en la misma carpeta que el archivo de entrada agregando '_out' al nombre?"
)

if usar_mismo_path:
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_out{ext}"
    counter = 1
    while os.path.exists(output_path):
        output_path = f"{base}_out_{counter}{ext}"
        counter += 1
else:
    carpeta_salida = filedialog.askdirectory(
        title="Seleccione la carpeta para guardar el archivo de salida"
    )
    if not carpeta_salida:
        raise Exception("No se seleccionó ninguna carpeta de salida.")
    base_name = os.path.basename(input_path)
    nombre_base, ext = os.path.splitext(base_name)
    output_path = os.path.join(carpeta_salida, f"{nombre_base}_out{ext}")
    counter = 1
    while os.path.exists(output_path):
        output_path = os.path.join(carpeta_salida, f"{nombre_base}_out_{counter}{ext}")
        counter += 1



# Global list to store model selection and alert details
model_selection_details = []

# ----- Auxiliary Functions for Feature Engineering -----
def enrich_features(df, date_col='ds'):
    """
    From a date column, generate additional features:
      - time_index: ordinal value of the date
      - month, quarter, and year.
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df['time_index'] = df[date_col].apply(lambda d: d.toordinal())
    df['month'] = df[date_col].dt.month
    df['quarter'] = df[date_col].dt.quarter
    df['year'] = df[date_col].dt.year
    return df

# ----- Improved Exponential Smoothing -----
def exp_smooth_forecast(series, periods):
    """
    Attempts to fit both multiplicative and additive Exponential Smoothing models
    (if the series is strictly positive) and chooses the one with the lower AIC.
    Extra parameters (maxiter=500 and initialization_method='estimated') are provided
    to improve convergence.
    If the series contains zeros or there are insufficient seasonal cycles,
    a constant forecast is returned.
    """
    if series.min() > 0:
        try:
            model_mul = ExponentialSmoothing(series, trend='mul', seasonal='mul', seasonal_periods=12)
            fitted_mul = model_mul.fit(optimized=True, maxiter=500, initialization_method='estimated')
            forecast_mul = fitted_mul.forecast(periods)
            aic_mul = fitted_mul.aic
        except Exception:
            aic_mul = np.inf
        try:
            model_add = ExponentialSmoothing(series, trend='add', seasonal='add', seasonal_periods=12)
            fitted_add = model_add.fit(optimized=True, maxiter=500, initialization_method='estimated')
            forecast_add = fitted_add.forecast(periods)
            aic_add = fitted_add.aic
        except Exception as e:
            if "Cannot compute initial seasonals" in str(e):
                fallback_val = np.mean(series.iloc[-6:]) if len(series) >= 6 else np.mean(series)
                return [fallback_val] * periods
            else:
                raise
        return forecast_mul if aic_mul < aic_add else forecast_add
    else:
        try:
            model = ExponentialSmoothing(series, trend='add', seasonal='add', seasonal_periods=12)
            fitted = model.fit(optimized=True, maxiter=500, initialization_method='estimated')
            return fitted.forecast(periods)
        except ValueError as e:
            if "Cannot compute initial seasonals" in str(e):
                fallback_val = np.mean(series.iloc[-6:]) if len(series) >= 6 else np.mean(series)
                return [fallback_val] * periods
            else:
                raise

# ----- Implementation of the Croston Method -----
def croston(ts, extra_periods=1, alpha=0.1):
    ts = np.array(ts)
    n = len(ts)
    nonzero_indices = np.where(ts > 0)[0]
    if nonzero_indices.size == 0:
        return [0] * extra_periods, 0
    first_nonzero = nonzero_indices[0]
    a = ts[first_nonzero]
    p = first_nonzero + 1
    forecast = [a / p] * n
    for i in range(first_nonzero + 1, n):
        if ts[i] > 0:
            a = alpha * ts[i] + (1 - alpha) * a
            p = alpha * (i - first_nonzero) + (1 - alpha) * p
        forecast[i] = a / p if p != 0 else 0
    overall_forecast = a / p if p != 0 else 0
    forecast_extension = [overall_forecast] * extra_periods
    return forecast_extension, overall_forecast

def croston_forecast(data, periods=24):
    forecast, _ = croston(data, extra_periods=periods)
    return forecast

# ----- Data Preparation -----
def prepare_data(df, sku, dpg):
    """
    Aggregates monthly data, reindexes to a continuous monthly series,
    and trims leading and trailing zeros. Adds SKU, DPG, and KeyFigure columns.
    """
    df_agg = df.groupby('Month', as_index=False).agg({'Sum of Quantity': 'sum'})
    full_range = pd.date_range(start=df_agg['Month'].min(), end=df_agg['Month'].max(), freq='MS')
    df_agg = df_agg.set_index('Month').reindex(full_range, fill_value=0)
    df_agg.index.name = 'Month'
    df_agg = df_agg.reset_index()
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
    """
    Returns the forecast start date as the month following the last historical record.
    However, if that month is in the past compared to the current month, the current month is used.
    """
    current_month = pd.Timestamp(datetime.today().replace(day=1))
    if historical_records:
        last_hist = pd.to_datetime(historical_records[-1]['Month'])
    else:
        last_hist = current_month - pd.DateOffset(months=1)
    forecast_start = last_hist + pd.DateOffset(months=1)
    if forecast_start < current_month:
        forecast_start = current_month
    return forecast_start

# ----- Model Evaluation and Ensemble -----
def evaluate_models(sales_series, forecast_horizon=24):
    """
    Performs cross-validation for each model and returns:
      - the forecast from the best model,
      - the best model name,
      - the best (lowest) MAPE,
      - and candidate model scores.
    Adjustments are made for SARIMAX (log transformation), Prophet (minimum data validation),
    and XGBoost (enriched features). Finally, a weighted ensemble is calculated.
    """
    candidate_scores = {}
    best_score = np.inf
    best_forecast = None
    best_model_name = ""
    
    if sales_series['y'].sum() == 0:
        candidate_scores["No Model"] = "Insufficient data"
        return [0] * forecast_horizon, "No Data", best_score, candidate_scores
    
    n_splits = 3
    split_size = len(sales_series) // (n_splits + 1)
    
    # Dictionary to store forecasts on the full series
    full_forecasts = {}
    models = ['Exponential Smoothing', 'SARIMAX', 'Prophet', 'XGBoost']
    
    for m_name in models:
        try:
            mape_scores = []
            # Cross-validation loop
            for i in range(n_splits):
                train = sales_series.iloc[:split_size*(i+1)]
                test = sales_series.iloc[split_size*(i+1):split_size*(i+2)]
                
                if m_name == 'Exponential Smoothing':
                    forecast_cv = exp_smooth_forecast(train['y'], len(test))
                elif m_name == 'SARIMAX':
                    if train['y'].min() > 0:
                        train_y = np.log(train['y'])
                        model_cv = SARIMAX(train_y, order=(1,1,1), 
                                             seasonal_order=(1,1,1,12),
                                             enforce_stationarity=False,
                                             enforce_invertibility=False)
                        fitted_model = model_cv.fit(disp=False)
                        forecast_cv = np.exp(fitted_model.forecast(len(test)))
                    else:
                        model_cv = SARIMAX(train['y'], order=(1,1,1),
                                             seasonal_order=(1,1,1,12),
                                             enforce_stationarity=False,
                                             enforce_invertibility=False)
                        fitted_model = model_cv.fit(disp=False)
                        forecast_cv = fitted_model.forecast(len(test))
                elif m_name == 'Prophet':
                    if len(train) < 12:
                        raise ValueError("Not enough data for Prophet")
                    m = Prophet(changepoint_prior_scale=0.5,
                                yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False,
                                mcmc_samples=0, uncertainty_samples=0)
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
            
            # Forecast on full series for ensemble
            if m_name == 'Exponential Smoothing':
                full_forecasts[m_name] = exp_smooth_forecast(sales_series['y'], forecast_horizon)
            elif m_name == 'SARIMAX':
                if sales_series['y'].min() > 0:
                    y_full = np.log(sales_series['y'])
                    fitted_model = SARIMAX(y_full, order=(1,1,1),
                                           seasonal_order=(1,1,1,12),
                                           enforce_stationarity=False,
                                           enforce_invertibility=False).fit(disp=False)
                    full_forecasts[m_name] = np.exp(fitted_model.forecast(forecast_horizon))
                else:
                    fitted_model = SARIMAX(sales_series['y'], order=(1,1,1),
                                           seasonal_order=(1,1,1,12),
                                           enforce_stationarity=False,
                                           enforce_invertibility=False).fit(disp=False)
                    full_forecasts[m_name] = fitted_model.forecast(forecast_horizon)
            elif m_name == 'Prophet':
                if len(sales_series) < 12:
                    raise ValueError("Not enough data for Prophet (full series)")
                m = Prophet(changepoint_prior_scale=0.5,
                            yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False,
                            mcmc_samples=0, uncertainty_samples=0)
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

    # Compute weighted ensemble
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
        except Exception as e:
            fallback_val = np.mean(sales_series['y'].iloc[-6:]) if len(sales_series) >= 6 else np.mean(sales_series['y'])
            final_forecast = [fallback_val] * forecast_horizon
            best_model_name = "AvgLast6 (Fallback)"

    return final_forecast, best_model_name, best_score, candidate_scores

def choose_model(sales_series, forecast_horizon=24):
    """
    If the series has less than 12 observations, a naive forecast is used;
    if more than 50% of the values are zero, Croston's method is used;
    otherwise, the models are evaluated.
    """
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

# ----- Unified Forecast Function with Alerts -----
def process_forecast(sku, dpg, df, level):
    """
    Processes the forecast at both SKU/DPG and SKU levels,
    calculates various alerts, and returns historical and forecast records.
    """
    try:
        prepared_df = prepare_data(df, sku, dpg)
        historical_records = prepared_df.to_dict('records')
        forecast_start = get_forecast_start(historical_records)
        
        sales_series = prepared_df[['Month', 'Sum of Quantity']].copy()
        sales_series['ds'] = pd.to_datetime(sales_series['Month'])
        sales_series.rename(columns={'Sum of Quantity': 'y'}, inplace=True)
        sales_series.sort_values('ds', inplace=True)
        
        forecast_values, best_model, best_score, candidate_scores = choose_model(sales_series)
        
        # Compute alerts
        alerts = {}
        # 1. Fallback Model Alert
        if any(keyword in best_model.lower() for keyword in ["fallback", "naive", "croston"]):
            alerts["Fallback Alert"] = f"Model used: {best_model}"
        else:
            alerts["Fallback Alert"] = ""
        # 2. High MAPE Alert (threshold: 30%)
        if best_score > 0.3:
            alerts["High MAPE Alert"] = f"MAPE: {best_score*100:.1f}%"
        else:
            alerts["High MAPE Alert"] = ""
        # 3. Flat Forecast Alert (forecast std < 10% of historical std)
        historical_std = np.std(sales_series['y'])
        forecast_std = np.std(forecast_values)
        if historical_std > 0 and forecast_std < 0.1 * historical_std:
            alerts["Flat Forecast Alert"] = f"Forecast std ({forecast_std:.2f}) < 10% of historical std ({historical_std:.2f})"
        else:
            alerts["Flat Forecast Alert"] = ""
        # 4. Trend Inconsistency Alert (using linear regression slopes)
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
        # 5. Model Consensus Alert (CV of candidate MAPEs)
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
        
        # Append alerts to model selection details
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
                'Sum of Quantity': max(0, math.ceil(qty)),
                'ModelUsed': best_model
            })
        
        return historical_records + forecast_records
    except Exception as e:
        logging.error(f"Critical error for SKU: {sku}, DPG: {dpg} - Error: {e}\n{traceback.format_exc()}")
        raise

def process_group(args):
    sku, dpg, group = args
    return process_forecast(sku, dpg, group.copy(), level="DPG")

def process_sku(sku, group):
    return process_forecast(sku, "ALL", group.copy(), level="SKU")

# ----- Main Function -----
def main():
    start_time = time.time()
    try:
        print("Starting the forecasting script...")
        df = pd.read_excel(input_path)
        df['Month'] = pd.to_datetime(df['Month'])
        
        # Process SKU/DPG groups with progress bar
        groups = df.groupby(['SKU', 'DPG'])
        args_list = [(sku, dpg, group.copy()) for (sku, dpg), group in groups]
        print("Processing SKU/DPG groups. Number of groups:", len(args_list))
        results_dpg = []
        for args in tqdm(args_list, desc="Processing SKU/DPG groups"):
            res = process_group(args)
            if res:
                results_dpg.extend(res)
        
        # Process SKU groups with progress bar
        sku_groups = df.groupby('SKU')
        results_sku = []
        for sku, group in tqdm(sku_groups, desc="Processing SKU groups"):
            res = process_sku(sku, group.copy())
            if res:
                results_sku.extend(res)
        
        forecast_df_dpg = pd.DataFrame(results_dpg)
        forecast_df_sku = pd.DataFrame(results_sku)
        model_selection_df = pd.DataFrame(model_selection_details)
        
        # Create separate tabs for alerts
        alerts_sku_dpg = model_selection_df[model_selection_df['Level'] == "DPG"][
            ['SKU', 'DPG', 'Fallback Alert', 'High MAPE Alert', 'Flat Forecast Alert',
             'Trend Inconsistency Alert', 'Model Consensus Alert']]
        alerts_sku = model_selection_df[model_selection_df['Level'] == "SKU"][
            ['SKU', 'Fallback Alert', 'High MAPE Alert', 'Flat Forecast Alert',
             'Trend Inconsistency Alert', 'Model Consensus Alert']]
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            forecast_df_dpg.to_excel(writer, sheet_name='Forecast_DPG', index=False)
            forecast_df_sku.to_excel(writer, sheet_name='Forecast_SKU', index=False)
            model_selection_df.to_excel(writer, sheet_name='Model_Selection', index=False)
            alerts_sku_dpg.to_excel(writer, sheet_name='Alerts_SKU_DPG', index=False)
            alerts_sku.to_excel(writer, sheet_name='Alerts_SKU', index=False)
        
        total_rows = len(results_dpg) + len(results_sku)
        print("Processing completed. Total rows generated:", total_rows)
        print("Forecast completed successfully. File saved at:", output_path)
        
        elapsed_time = time.time() - start_time
        print("Total processing time: {:.2f} seconds".format(elapsed_time))
    except Exception as e:
        logging.error(f"Critical error in main execution - Error: {e}\n{traceback.format_exc()}")
        print("An error occurred during execution.")
        print(f"Error: {e}")
        print(traceback.format_exc())

if __name__ == '__main__':
    main()
