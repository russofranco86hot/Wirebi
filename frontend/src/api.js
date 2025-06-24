// frontend/src/api.js - Versión FINAL y Corregida para Fase 2

const API_BASE_URL = 'http://localhost:8000'; 

const handleApiResponse = async (response, defaultErrorMessage) => {
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({})); 
    if (response.status === 404 && errorBody.detail && errorBody.detail.includes("No historical data found matching criteria")) {
      return [];
    }
    if (response.status === 404 && errorBody.detail && errorBody.detail.includes("No versioned forecast data found matching criteria")) {
        return [];
    }
    if (response.status === 404 && errorBody.detail && errorBody.detail.includes("No forecast stat data found matching criteria")) {
        return [];
    }
    throw new Error(`HTTP error! status: ${response.status} - ${errorBody.detail || defaultErrorMessage || response.statusText}`);
  }
  return response.json();
};

const buildQueryParams = (paramsObj) => {
  const params = new URLSearchParams();
  for (const key in paramsObj) {
    const value = paramsObj[key];

    if (value !== null && value !== undefined && value !== '') {
      if (Array.isArray(value)) {
        if (value.length > 0) {
          value.forEach(item => params.append(key, String(item)));
        }
      } else {
        params.append(key, String(value));
      }
    }
  }
  const queryString = params.toString();
  return queryString ? `?${queryString}` : '';
};

export const fetchClients = async () => {
  const response = await fetch(`${API_BASE_URL}/clients/`);
  return handleApiResponse(response, "Error al cargar clientes.");
};

export const fetchSkus = async () => {
  const response = await fetch(`${API_BASE_URL}/skus/`);
  return handleApiResponse(response, "Error al cargar SKUs.");
};

export const fetchKeyFigures = async () => {
  const response = await fetch(`${API_BASE_URL}/keyfigures/`);
  return handleApiResponse(response, "Error al cargar Figuras Clave.");
};

export const fetchHistoricalData = async ({ clientIds, skuIds, startPeriod, endPeriod, keyFigureIds, sources }) => {
  const params = {
    client_ids: clientIds,
    sku_ids: skuIds,
    start_period: startPeriod,
    end_period: endPeriod,
    key_figure_ids: keyFigureIds,
    sources: sources,
  };

  const queryString = buildQueryParams(params);
  const url = `${API_BASE_URL}/data/history/${queryString}`;
  
  console.log("Fetching historical data from:", url); 
  const response = await fetch(url);
  return handleApiResponse(response, "Error al cargar datos históricos.");
};

export const fetchForecastVersionedData = async ({ versionIds, clientIds, skuIds, startPeriod, endPeriod, keyFigureIds }) => {
    const params = {
        version_ids: versionIds,
        client_ids: clientIds,
        sku_ids: skuIds,
        start_period: startPeriod,
        end_period: endPeriod,
        key_figure_ids: keyFigureIds,
    };

    const queryString = buildQueryParams(params);
    const url = `${API_BASE_URL}/data/forecast/versioned/${queryString}`;

    console.log("Fetching forecast versioned data from:", url); 
    const response = await fetch(url);
    return handleApiResponse(response, "Error al cargar datos de pronóstico versionado.");
};

export const generateForecast = async ({ clientId, skuId, historySource, smoothingAlpha, modelName, forecastHorizon }) => {
    const params = {
        client_id: clientId,
        sku_id: skuId,
        history_source: historySource,
        smoothing_alpha: smoothingAlpha,
        model_name: modelName,
        forecast_horizon: forecastHorizon,
    };

    const queryString = buildQueryParams(params);
    const url = `${API_BASE_URL}/data/forecast/generate/${queryString}`;

    console.log("Generating forecast with URL:", url);
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    });
    return handleApiResponse(response, "Error al generar el pronóstico.");
};

// --- NUEVA FUNCIÓN: Para obtener datos de fact_forecast_stat ---
export const fetchForecastStatData = async ({ clientIds, skuIds, startPeriod, endPeriod, forecastRunIds }) => {
    const params = {
        client_ids: clientIds,
        sku_ids: skuIds,
        start_period: startPeriod,
        end_period: endPeriod,
        forecast_run_ids: forecastRunIds,
    };

    const queryString = buildQueryParams(params);
    const url = `${API_BASE_URL}/data/forecast_stat/${queryString}`;

    console.log("Fetching forecast stat data from:", url);
    const response = await fetch(url);
    return handleApiResponse(response, "Error al cargar datos de pronóstico estadístico.");
};