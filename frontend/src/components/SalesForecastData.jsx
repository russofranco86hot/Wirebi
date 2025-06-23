// frontend/src/components/SalesForecastData.jsx - Versión completa

import React, { useState, useEffect } from 'react';
import { fetchClients, fetchSkus, fetchKeyFigures, fetchHistoricalData, fetchForecastVersionedData } from '../api';

function SalesForecastData() {
  // Estados para los datos y el estado de carga/error
  const [historyData, setHistoryData] = useState([]);
  const [forecastData, setForecastData] = useState([]);
  const [loadingData, setLoadingData] = useState(false); // Inicia como false, se activa al buscar
  const [errorData, setErrorData] = useState(null);

  // Estados para los datos de dimensiones (para los filtros)
  const [clients, setClients] = useState([]);
  const [skus, setSkus] = useState([]);
  const [keyFigures, setKeyFigures] = useState([]);
  const [versions, setVersions] = useState([]); // Necesitarás un endpoint para esto en el futuro

  // Estados para los filtros seleccionados por el usuario
  const [selectedClient, setSelectedClient] = useState(''); // UUID del cliente seleccionado
  const [selectedSku, setSelectedSku] = useState('');       // UUID del SKU seleccionado
  const [startDate, setStartDate] = useState('');           // Fecha de inicio (YYYY-MM-DD)
  const [endDate, setEndDate] = useState('');               // Fecha de fin (YYYY-MM-DD)
  const [selectedKeyFigures, setSelectedKeyFigures] = useState([]); // IDs de KeyFigures seleccionadas

  // Efecto para cargar las dimensiones (clientes, SKUs, KeyFigures) al inicio
  useEffect(() => {
    const loadDimensions = async () => {
      try {
        const [clientsData, skusData, keyFiguresData] = await Promise.all([
          fetchClients(),
          fetchSkus(),
          fetchKeyFigures(),
          // En el futuro, podrías tener también fetchForecastVersions() aquí
        ]);
        setClients(clientsData);
        setSkus(skusData);
        setKeyFigures(keyFiguresData);
      } catch (e) {
        // Manejar errores de carga de dimensiones
        console.error("Error loading dimensions:", e);
      }
    };
    loadDimensions();
  }, []);

  // Función para manejar la búsqueda de datos
  const handleSearch = async () => {
    setLoadingData(true);
    setErrorData(null);
    try {
      // Prepara los parámetros para la API
      const filterParams = {
        clientIds: selectedClient ? [selectedClient] : null,
        skuIds: selectedSku ? [selectedSku] : null,
        startPeriod: startDate || null,
        endPeriod: endDate || null,
        keyFigureIds: selectedKeyFigures.length > 0 ? selectedKeyFigures.map(Number) : null, // Asegurar que sean números
      };

      // Realiza las peticiones a la API
      const historical = await fetchHistoricalData(filterParams);
      // Para forecast_versioned, necesitamos un version_id.
      // Por ahora, si no seleccionas una versión específica, podrías obtener todas las versiones del cliente.
      // Aquí estamos simplificando, asumiendo que no hay filtro de versión aún.
      // Para un uso real, el usuario probablemente elegiría una versión o habría una versión 'actual'.
      const forecast = await fetchForecastVersionedData({
        ...filterParams,
        versionIds: null, // Por ahora, no filtramos por versión aquí. Se podría añadir un filtro en la UI.
        // O podrías buscar una versión por defecto para el cliente/SKU seleccionado.
      });

      setHistoryData(historical);
      setForecastData(forecast);

    } catch (e) {
      setErrorData(e.message);
    } finally {
      setLoadingData(false);
    }
  };

  // Función para manejar el cambio en los filtros de KeyFigures
  const handleKeyFigureChange = (event) => {
    const { value, checked } = event.target;
    setSelectedKeyFigures(prev => 
      checked ? [...prev, value] : prev.filter(kfId => kfId !== value)
    );
  };

  return (
    <section>
      <h2>Datos de Ventas y Pronóstico</h2>

      {/* Controles de Filtro */}
      <div style={{ marginBottom: '20px', border: '1px solid #ccc', padding: '15px' }}>
        <h3>Filtros</h3>
        <div>
          <label>Cliente:</label>
          <select value={selectedClient} onChange={e => setSelectedClient(e.target.value)}>
            <option value="">Todos los clientes</option>
            {clients.map(client => (
              <option key={client.client_id} value={client.client_id}>
                {client.client_name}
              </option>
            ))}
          </select>
        </div>
        <div style={{ marginTop: '10px' }}>
          <label>SKU:</label>
          <select value={selectedSku} onChange={e => setSelectedSku(e.target.value)}>
            <option value="">Todos los SKUs</option>
            {skus.map(sku => (
              <option key={sku.sku_id} value={sku.sku_id}>
                {sku.sku_name}
              </option>
            ))}
          </select>
        </div>
        <div style={{ marginTop: '10px' }}>
          <label>Fecha Inicio:</label>
          <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
        </div>
        <div style={{ marginTop: '10px' }}>
          <label>Fecha Fin:</label>
          <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />
        </div>
        <div style={{ marginTop: '10px' }}>
          <label>Figuras Clave:</label>
          {keyFigures.map(kf => (
            <label key={kf.key_figure_id} style={{ marginLeft: '10px' }}>
              <input
                type="checkbox"
                value={kf.key_figure_id}
                checked={selectedKeyFigures.includes(String(kf.key_figure_id))} // Asegurarse de que el tipo coincida
                onChange={handleKeyFigureChange}
              />
              {kf.name}
            </label>
          ))}
        </div>
        <button onClick={handleSearch} style={{ marginTop: '20px', padding: '10px 20px', cursor: 'pointer' }}>
          Buscar Datos
        </button>
      </div>

      {/* Mostrar Datos */}
      {loadingData ? (
        <p>Cargando datos...</p>
      ) : errorData ? (
        <p style={{ color: 'red' }}>Error al cargar datos: {errorData}</p>
      ) : (
        <>
          <h3>Datos Históricos ({historyData.length} registros)</h3>
          {historyData.length === 0 ? (
            <p>No hay datos históricos para los filtros seleccionados.</p>
          ) : (
            <table border="1" style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }}>
              <thead>
                <tr>
                  <th>Cliente</th>
                  <th>SKU</th>
                  <th>Período</th>
                  <th>Figura Clave</th>
                  <th>Valor</th>
                  <th>Fuente</th>
                </tr>
              </thead>
              <tbody>
                {historyData.map((item, index) => (
                  <tr key={index}>
                    <td>{item.client?.client_name || item.client_id}</td>
                    <td>{item.sku?.sku_name || item.sku_id}</td>
                    <td>{item.period}</td>
                    <td>{item.key_figure?.name || item.key_figure_id}</td>
                    <td>{item.value}</td>
                    <td>{item.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <h3 style={{ marginTop: '30px' }}>Datos de Pronóstico Versionado ({forecastData.length} registros)</h3>
          {forecastData.length === 0 ? (
            <p>No hay datos de pronóstico versionado para los filtros seleccionados.</p>
          ) : (
            <table border="1" style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }}>
              <thead>
                <tr>
                  <th>Versión</th>
                  <th>Cliente</th>
                  <th>SKU</th>
                  <th>Período</th>
                  <th>Figura Clave</th>
                  <th>Valor</th>
                </tr>
              </thead>
              <tbody>
                {forecastData.map((item, index) => (
                  <tr key={index}>
                    <td>{item.version?.name || item.version_id}</td> {/* Asumiendo que ForecastVersion tiene un 'name' */}
                    <td>{item.client?.client_name || item.client_id}</td>
                    <td>{item.sku?.sku_name || item.sku_id}</td>
                    <td>{item.period}</td>
                    <td>{item.key_figure?.name || item.key_figure_id}</td>
                    <td>{item.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </section>
  );
}

export default SalesForecastData;