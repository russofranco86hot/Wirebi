// frontend/src/api.js - Versión FINAL y Corregida

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
        // Si el valor es un array, se agregan múltiples parámetros con el mismo nombre de clave
        value.forEach(item => params.append(key, String(item)));
      } else {
        // Si no es un array, se agrega un solo parámetro
        params.append(key, String(value));
      }
    }
  }
  const queryString = params.toString();
  return queryString ? `?${queryString}` : '';
};


export const fetchHistoricalData = async ({ clientIds, skuIds, startPeriod, endPeriod, keyFigureIds }) => {
  // Asegurarse de que los IDs se pasen como arrays de strings, incluso si solo hay uno
  const params = {
    client_ids: clientIds ? clientIds.map(String) : [], // Convertir a string y asegurar array
    sku_ids: skuIds ? skuIds.map(String) : [],           // Convertir a string y asegurar array
    start_period: startPeriod,
    end_period: endPeriod,
    key_figure_ids: keyFigureIds || [],                 // Asegurar array de ints
  };

  const queryString = buildQueryParams(params);
  const url = `${API_BASE_URL}/data/history/${queryString}`;
  
  console.log("Fetching historical data from:", url); // Para depuración
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
};

export const fetchForecastVersionedData = async ({ versionIds, clientIds, skuIds, startPeriod, endPeriod, keyFigureIds }) => {
    // Asegurarse de que los IDs se pasen como arrays de strings
    const params = {
        version_ids: versionIds ? versionIds.map(String) : [],
        client_ids: clientIds ? clientIds.map(String) : [],
        sku_ids: skuIds ? skuIds.map(String) : [],
        start_period: startPeriod,
        end_period: endPeriod,
        key_figure_ids: keyFigureIds || [],
    };

    const queryString = buildQueryParams(params);
    const url = `${API_BASE_URL}/data/forecast/versioned/${queryString}`;

    console.log("Fetching forecast data from:", url); // Para depuración
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
};

// Puedes añadir más funciones aquí para otras interacciones con la API (POST, PUT, DELETE)