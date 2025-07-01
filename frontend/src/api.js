// frontend/src/api.js

const API_BASE_URL = 'http://localhost:8000'; // Asegúrate de que esta URL sea correcta para tu backend

// Funciones para clientes
export const fetchClients = async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/clients/`);
        if (!response.ok) {
            throw new Error('Error al obtener la lista de clientes.');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching clients:', error);
        throw error;
    }
};

// Funciones para SKUs (ACTUALIZADO para usar el nuevo endpoint /skus?client_id=...)
export const fetchSkus = async (clientId) => {
    try {
        const url = new URL(`${API_BASE_URL}/skus/`); // Ruta base /skus/
        if (clientId) {
            url.searchParams.append('client_id', clientId); // Añadir client_id como query param
        }
        const response = await fetch(url.toString());
        if (!response.ok) {
            throw new Error('Error al obtener la lista de SKUs.');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching SKUs:', error);
        throw error;
    }
};

// Funciones para Key Figures
export const fetchKeyFigures = async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/keyfigures/`);
        if (!response.ok) {
            throw new Error('Error al obtener las figuras clave.');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching key figures:', error);
        throw error;
    }
};

// Funciones para obtener tipos de ajuste
export const fetchAdjustmentTypes = async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/data/adjustment_types/`);
        if (!response.ok) {
            throw new Error('Error al obtener los tipos de ajuste.');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching adjustment types:', error);
        throw error;
    }
};

// Función para obtener datos de ventas y pronósticos (ajustada para el nuevo endpoint)
export const salesForecastApi = async (clientId, skuId, clientFinalId, startPeriod, endPeriod) => {
    try {
        const url = new URL(`${API_BASE_URL}/data/sales_forecast_data`);
        url.searchParams.append('client_id', clientId);
        url.searchParams.append('sku_id', skuId);
        url.searchParams.append('client_final_id', clientFinalId);
        url.searchParams.append('start_period', startPeriod);
        url.searchParams.append('end_period', endPeriod);

        const response = await fetch(url.toString());
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al obtener los datos de pronóstico de ventas.');
        }
        return await response.json();
    } catch (error) {
        console.error('Error in salesForecastApi:', error);
        throw error;
    }
};

// Función para actualizar una celda de ajuste
export const updateAdjustment = async (adjustmentData) => {
    try {
        const response = await fetch(`${API_BASE_URL}/data/adjustments/`, {
            method: 'POST', // Usamos POST para upsert
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(adjustmentData),
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al actualizar el ajuste.');
        }
        return await response.json();
    } catch (error) {
        console.error('Error updating adjustment:', error);
        throw error;
    }
};

// Función para generar el pronóstico estadístico
export const generateStatisticalForecast = async (clientId, skuId, historySource, smoothingAlpha, modelName, forecastHorizon) => {
    try {
        const url = new URL(`${API_BASE_URL}/data/forecast/generate/`);
        url.searchParams.append('clientId', clientId);
        url.searchParams.append('skuId', skuId);
        url.searchParams.append('historySource', historySource); // 'sales', 'shipments', 'order'
        url.searchParams.append('smoothing_alpha', smoothingAlpha);
        url.searchParams.append('model_name', modelName);
        url.searchParams.append('forecast_horizon', forecastHorizon);

        const response = await fetch(url.toString(), {
            method: 'POST',
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al generar el pronóstico estadístico.');
        }
        return await response.json();
    } catch (error) {
        console.error('Error generating statistical forecast:', error);
        throw error;
    }
};

// Función para guardar un comentario
export const saveComment = async (commentData) => {
    try {
        const response = await fetch(`${API_BASE_URL}/data/comments/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(commentData),
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al guardar el comentario.');
        }
        return await response.json();
    } catch (error) {
        console.error('Error saving comment:', error);
        throw error;
    }
};

// Función para obtener comentarios
export const fetchComments = async (clientId, skuId, clientFinalId, period, keyFigureId) => {
    try {
        const url = new URL(`${API_BASE_URL}/data/comments/`);
        const clientIds = clientId ? [clientId] : [];
        const skuIds = skuId ? [skuId] : [];
        const keyFigureIds = keyFigureId ? [keyFigureId] : [];

        if (clientIds.length > 0) url.searchParams.append('client_ids', clientIds.join(','));
        if (skuIds.length > 0) url.searchParams.append('sku_ids', skuIds.join(','));
        if (period) {
            url.searchParams.append('start_period', dayjs(period).format('YYYY-MM-DD'));
            url.searchParams.append('end_period', dayjs(period).format('YYYY-MM-DD'));
        }
        if (keyFigureIds.length > 0) url.searchParams.append('key_figure_ids', keyFigureIds.join(','));

        const response = await fetch(url.toString());
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al obtener los comentarios.');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching comments:', error);
        throw error;
    }
};

// --- FUNCIONES PARA VERSIONES (SNAPSHOTS) ---

// Función para guardar una versión del pronóstico
export const saveForecastVersion = async (versionData) => {
    try {
        const response = await fetch(`${API_BASE_URL}/data/forecast/versions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(versionData),
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al guardar la versión del pronóstico.');
        }
        return await response.json();
    } catch (error) {
        console.error('Error saving forecast version:', error);
        throw error;
    }
};

// Función para obtener la lista de versiones
export const fetchForecastVersions = async (clientId) => {
    try {
        const url = new URL(`${API_BASE_URL}/data/forecast/versions`);
        if (clientId) {
            url.searchParams.append('client_id', clientId);
        }
        const response = await fetch(url.toString());
        if (!response.ok) {
            throw new Error('Error al obtener las versiones del pronóstico.');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching forecast versions:', error);
        throw error;
    }
};

// Función para cargar datos de una versión específica (necesitarás implementar el endpoint en el backend si es diferente a fetchForecastVersionedData)
export const fetchVersionedForecastData = async (versionId, clientId, skuId, clientFinalId, startPeriod, endPeriod) => {
    try {
        const url = new URL(`${API_BASE_URL}/data/forecast/versioned/`);
        
        // Asumiendo que el backend puede filtrar por estos parámetros
        url.searchParams.append('version_ids', versionId);
        url.searchParams.append('client_ids', clientId);
        url.searchParams.append('sku_ids', skuId);
        // clientFinalId no se usa directamente en el endpoint del backend que creamos para fetchVersionedForecastData,
        // se maneja internamente en la relación de base de datos.
        url.searchParams.append('start_period', startPeriod);
        url.searchParams.append('end_period', endPeriod);
        url.searchParams.append('key_figure_ids', 6); // Asumimos que quieres el Forecast Final versionado (ID 9)

        const response = await fetch(url.toString());
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al obtener los datos de la versión del pronóstico.');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching versioned forecast data:', error);
        throw error;
    }
};