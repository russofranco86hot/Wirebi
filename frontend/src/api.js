// frontend/src/api.js - Versión FINAL y Corregida para filtros y múltiples llamadas

const API_BASE_URL = 'http://localhost:8000'; // Asegúrate de que esta URL sea la correcta de tu backend FastAPI

// Función auxiliar para manejar respuestas y errores HTTP
const handleApiResponse = async (response, defaultErrorMessage) => {
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({})); // Intenta parsear, si falla, un objeto vacío
    // Si la API devuelve un 404, pero es porque no encontró datos (el detalle de FastAPI),
    // no lo tratamos como un error fatal, simplemente devolvemos un array vacío.
    if (response.status === 404 && errorBody.detail && errorBody.detail.includes("No historical data found matching criteria")) {
      return [];
    }
    if (response.status === 404 && errorBody.detail && errorBody.detail.includes("No versioned forecast data found matching criteria")) {
        return [];
    }
    // Para otros errores, lanzar una excepción
    throw new Error(`HTTP error! status: ${response.status} - ${errorBody.detail || defaultErrorMessage || response.statusText}`);
  }
  return response.json();
};

// Función auxiliar para construir la URL con parámetros de consulta
const buildQueryParams = (paramsObj) => {
  const params = new URLSearchParams();
  for (const key in paramsObj) {
    const value = paramsObj[key];

    // Solo añadir el parámetro si tiene un valor significativo
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

// --- Funciones de Fetch para tus Routers ---

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

// Puedes añadir más funciones aquí si vas a usar otros endpoints GET
export const fetchForecastVersions = async () => {
    const response = await fetch(`${API_BASE_URL}/data/versions/`);
    return handleApiResponse(response, "Error al cargar versiones de pronóstico.");
};