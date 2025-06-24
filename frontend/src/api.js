// frontend/src/api.js - Versión FINAL y Corregida para filtros

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

    // Solo añadir el parámetro si tiene un valor significativo
    // Esto es CLAVE para evitar enviar "?param=null" o "?param="
    if (value !== null && value !== undefined && value !== '') {
      if (Array.isArray(value)) {
        // Si el valor es un array y tiene elementos, agregarlos
        if (value.length > 0) {
          value.forEach(item => params.append(key, String(item)));
        }
      } else {
        // Si no es un array, simplemente agregarlo
        params.append(key, String(value));
      }
    }
  }
  const queryString = params.toString();
  return queryString ? `?${queryString}` : '';
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
  if (!response.ok) {
    // Si la API devuelve un 404, pero es porque no encontró datos (el detalle de FastAPI),
    // no lo tratamos como un error fatal. Esto es para el caso de "No historical data found matching criteria"
    const errorBody = await response.json();
    if (response.status === 404 && errorBody.detail && errorBody.detail.includes("No historical data found matching criteria")) {
      return []; // Devolver un array vacío para que el frontend lo maneje
    }
    throw new Error(`HTTP error! status: ${response.status} - ${errorBody.detail || response.statusText}`);
  }
  return response.json();
};

// Si necesitas llamar a otras tablas como forecast_versioned_data, puedes añadir funciones como:
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
  if (!response.ok) {
    const errorBody = await response.json();
    if (response.status === 404 && errorBody.detail && errorBody.detail.includes("No versioned forecast data found matching criteria")) {
      return [];
    }
    throw new Error(`HTTP error! status: ${response.status} - ${errorBody.detail || response.statusText}`);
  }
  return response.json();
};