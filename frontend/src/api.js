// frontend/src/api.js - Versión actualizada con endpoints de Historia Limpia, Pronóstico Final y Comentarios
//                       INCLUYE MEJORA TEMPORAL DE MANEJO DE ERRORES PARA DEBUGGING 422

const API_BASE_URL = 'http://localhost:8000'; // Ajusta esto si tu backend se ejecuta en otra URL

async function handleApiResponse(response) {
    if (!response.ok) {
        // Intenta parsear la respuesta JSON del error.
        // Si no es JSON o hay otro problema, lo maneja.
        let errorData;
        try {
            errorData = await response.json();
        } catch (e) {
            errorData = { detail: `No JSON response or parsing error, status: ${response.status}. Text: ${await response.text()}` };
        }
        
        console.error("API Error Response (raw):", errorData); // <-- MUY IMPORTANTE: REGISTRA LA RESPUESTA COMPLETA DEL ERROR

        let errorMessage = `HTTP error! status: ${response.status}`;

        if (errorData.detail) {
            if (Array.isArray(errorData.detail)) {
                // Si 'detail' es un array (típico de errores 422 de FastAPI)
                errorMessage = "Errores de validación:\n" + errorData.detail.map(err => {
                    const loc = err.loc ? err.loc.join('.') : 'unknown';
                    return `Campo: ${loc}, Mensaje: ${err.msg} (Tipo: ${err.type})`;
                }).join('\n');
            } else {
                // Si 'detail' es un string
                errorMessage = errorData.detail;
            }
        } else if (response.statusText) {
            errorMessage = response.statusText;
        }

        throw new Error(errorMessage);
    }
    return response.json();
}

// --- Clientes ---
export async function fetchClients() {
    const response = await fetch(`${API_BASE_URL}/clients/`);
    return handleApiResponse(response);
}

// --- SKUs ---
export async function fetchSkus() {
    const response = await fetch(`${API_BASE_URL}/skus/`);
    return handleApiResponse(response);
}

// --- Key Figures ---
export async function fetchKeyFigures() {
    const response = await fetch(`${API_BASE_URL}/keyfigures/`);
    return handleApiResponse(response);
}

// --- Adjustment Types ---
export async function fetchAdjustmentTypes() {
    const response = await fetch(`${API_BASE_URL}/data/adjustment_types/`);
    return handleApiResponse(response);
}

// --- Fact History Data ---
export async function fetchHistoricalData(filterParams = {}) {
    const params = new URLSearchParams();
    if (filterParams.clientIds) filterParams.clientIds.forEach(id => params.append('client_ids', id));
    if (filterParams.skuIds) filterParams.skuIds.forEach(id => params.append('sku_ids', id));
    if (filterParams.startPeriod) params.append('start_period', filterParams.startPeriod);
    if (filterParams.endPeriod) params.append('end_period', filterParams.endPeriod);
    if (filterParams.keyFigureIds) filterParams.keyFigureIds.forEach(id => params.append('key_figure_ids', id));
    if (filterParams.sources) filterParams.sources.forEach(source => params.append('sources', source));

    const response = await fetch(`${API_BASE_URL}/data/history/?${params.toString()}`);
    return handleApiResponse(response);
}

// --- Fact Forecast Versioned Data (Si aplica) ---
export async function fetchForecastVersionedData(filterParams = {}) {
    const params = new URLSearchParams();
    if (filterParams.versionIds) filterParams.versionIds.forEach(id => params.append('version_ids', id));
    if (filterParams.clientIds) filterParams.clientIds.forEach(id => params.append('client_ids', id));
    if (filterParams.skuIds) filterParams.skuIds.forEach(id => params.append('sku_ids', id));
    if (filterParams.startPeriod) params.append('start_period', filterParams.startPeriod);
    if (filterParams.endPeriod) params.append('end_period', filterParams.endPeriod);
    if (filterParams.keyFigureIds) filterParams.keyFigureIds.forEach(id => params.append('key_figure_ids', id));

    const response = await fetch(`${API_BASE_URL}/data/forecast/versioned/?${params.toString()}`);
    return handleApiResponse(response);
}

// --- Fact Forecast Stat Data ---
export async function fetchForecastStatData(filterParams = {}) {
    const params = new URLSearchParams();
    if (filterParams.clientIds) filterParams.clientIds.forEach(id => params.append('client_ids', id));
    if (filterParams.skuIds) filterParams.skuIds.forEach(id => params.append('sku_ids', id));
    if (filterParams.startPeriod) params.append('start_period', filterParams.startPeriod);
    if (filterParams.endPeriod) params.append('end_period', filterParams.endPeriod);
    if (filterParams.forecastRunIds) filterParams.forecastRunIds.forEach(id => params.append('forecast_run_ids', id));

    const response = await fetch(`${API_BASE_URL}/data/forecast_stat/?${params.toString()}`);
    return handleApiResponse(response);
}

// --- Generate Forecast ---
export async function generateForecast(forecastParams) {
    const params = new URLSearchParams();
    for (const key in forecastParams) {
        if (forecastParams[key] !== null && forecastParams[key] !== undefined) {
            params.append(key, forecastParams[key]);
        }
    }
    const response = await fetch(`${API_BASE_URL}/data/forecast/generate/?${params.toString()}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        // No body needed for POST with query parameters
    });
    return handleApiResponse(response);
}

// --- Send Manual Adjustment (UPSERT) ---
export async function sendManualAdjustment(adjustmentPayload) {
    console.log("Sending adjustment to URL: ", `${API_BASE_URL}/data/adjustments/`, "with data:", adjustmentPayload);
    const response = await fetch(`${API_BASE_URL}/data/adjustments/`, {
        method: 'POST', // Usamos POST para el upsert
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(adjustmentPayload),
    });
    return handleApiResponse(response);
}

// --- NUEVAS FUNCIONES PARA HISTORIA LIMPIA Y PRONÓSTICO FINAL ---
export async function fetchCleanHistoryData(filterParams = {}) {
    const params = new URLSearchParams();
    // client_id, sku_id, client_final_id, start_period, end_period son requeridos por el endpoint
    if (filterParams.clientId) params.append('client_id', filterParams.clientId);
    if (filterParams.skuId) params.append('sku_id', filterParams.skuId);
    if (filterParams.clientFinalId) params.append('client_final_id', filterParams.clientFinalId);
    if (filterParams.startPeriod) params.append('start_period', filterParams.startPeriod);
    if (filterParams.endPeriod) params.append('end_period', filterParams.endPeriod);
    if (filterParams.historySource) params.append('history_source', filterParams.historySource);

    const response = await fetch(`${API_BASE_URL}/data/clean_history/?${params.toString()}`);
    return handleApiResponse(response);
}

export async function fetchFinalForecastData(filterParams = {}) {
    const params = new URLSearchParams();
    // client_id, sku_id, client_final_id, start_period, end_period son requeridos por el endpoint
    if (filterParams.clientId) params.append('client_id', filterParams.clientId);
    if (filterParams.skuId) params.append('sku_id', filterParams.skuId);
    if (filterParams.clientFinalId) params.append('client_final_id', filterParams.clientFinalId);
    if (filterParams.startPeriod) params.append('start_period', filterParams.startPeriod);
    if (filterParams.endPeriod) params.append('end_period', filterParams.endPeriod);
    
    const response = await fetch(`${API_BASE_URL}/data/final_forecast/?${params.toString()}`);
    return handleApiResponse(response);
}


// --- NUEVAS FUNCIONES PARA COMENTARIOS ---
export async function sendComment(commentPayload) {
    console.log("Sending comment to URL: ", `${API_BASE_URL}/data/comments/`, "with data:", commentPayload);
    const response = await fetch(`${API_BASE_URL}/data/comments/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(commentPayload),
    });
    return handleApiResponse(response);
}

export async function fetchComments(filterParams = {}) {
    const params = new URLSearchParams();
    if (filterParams.clientIds) filterParams.clientIds.forEach(id => params.append('client_ids', id));
    if (filterParams.skuIds) filterParams.skuIds.forEach(id => params.append('sku_ids', id));
    if (filterParams.startPeriod) params.append('start_period', filterParams.startPeriod);
    if (filterParams.endPeriod) params.append('end_period', filterParams.endPeriod);
    if (filterParams.keyFigureIds) filterParams.keyFigureIds.forEach(id => params.append('key_figure_ids', id));

    const response = await fetch(`${API_BASE_URL}/data/comments/?${params.toString()}`);
    return handleApiResponse(response);
}