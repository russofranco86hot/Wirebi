// frontend/src/api.js - Versión FINAL y Consolidada

const API_BASE_URL = 'http://localhost:8000'; // Asegúrate de que esta URL sea la correcta de tu backend FastAPI

export const fetchClients = async () => {
  const response = await fetch(`${API_BASE_URL}/clients/`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
};

export const fetchSkus = async () => {
  const response = await fetch(`${API_BASE_URL}/skus/`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
};

export const fetchKeyFigures = async () => {
  const response = await fetch(`${API_BASE_URL}/keyfigures/`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
};

// Función auxiliar para construir la URL con parámetros de consulta
const buildQueryParams = (paramsObj) => {
  const params = new URLSearchParams();
  for (const key in paramsObj) {
    const value = paramsObj[key];
    if (value !== null && value !== undefined && value !== '') {
      if (Array.isArray(value)) {
        value.forEach(item => params.append(key, String(item)));
      } else {
        params.append(key, String(value));
      }
    }
  }
  const queryString = params.toString();
  return queryString ? `?${queryString}` : '';
};


export const fetchHistoricalData = async ({ clientIds, skuIds, startPeriod, endPeriod, keyFigureIds, sources }) => {
  const params = {
    client_ids: clientIds ? clientIds.map(String) : [],
    sku_ids: skuIds ? skuIds.map(String) : [],
    start_period: startPeriod,
    end_period: endPeriod,
    key_figure_ids: keyFigureIds || [],
    sources: sources || [], // Añadir el nuevo parámetro de fuentes
  };

  const queryString = buildQueryParams(params);
  const url = `${API_BASE_URL}/data/history/${queryString}`;
  
  console.log("Fetching historical data from:", url); 
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
};

// Eliminamos fetchForecastVersionedData ya que todo va a fact_history
// export const fetchForecastVersionedData = async (...) { ... }