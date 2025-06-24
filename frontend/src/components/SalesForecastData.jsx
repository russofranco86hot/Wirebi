// frontend/src/components/SalesForecastData.jsx - Versión FINAL y COMPLETA

import React, { useState, useEffect } from 'react';
import { fetchClients, fetchSkus, fetchKeyFigures, fetchHistoricalData, fetchForecastVersionedData } from '../api'; 

function SalesForecastData() {
  // Estados para los datos y el estado de carga/error
  const [historyData, setHistoryData] = useState([]);
  const [forecastVersionedData, setForecastVersionedData] = useState([]); // Reactivamos este estado
  const [loadingData, setLoadingData] = useState(false);
  const [errorData, setErrorData] = useState(null);

  // Estados para los datos de dimensiones (para los filtros)
  const [clients, setClients] = useState([]);
  const [skus, setSkus] = useState([]);
  const [keyFigures, setKeyFigures] = useState([]);

  // Estados para los filtros seleccionados por el usuario
  const [selectedClient, setSelectedClient] = useState('');
  const [selectedSku, setSelectedSku] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedKeyFigures, setSelectedKeyFigures] = useState(null); 
  const [selectedSources, setSelectedSources] = useState(null); 

  // Efecto para cargar las dimensiones (clientes, SKUs, KeyFigures) al inicio
  useEffect(() => {
    const loadDimensions = async () => {
      try {
        const [clientsData, skusData, keyFiguresData] = await Promise.all([
          fetchClients(),
          fetchSkus(),
          fetchKeyFigures(),
        ]);
        setClients(clientsData);
        setSkus(skusData);
        setKeyFigures(keyFiguresData);
      } catch (e) {
        console.error("Error loading dimensions:", e);
        setErrorData("Error al cargar dimensiones para filtros: " + e.message); // Set error si las dimensiones fallan
      }
    };
    loadDimensions();
  }, []);

  // Función para manejar la búsqueda de datos
  const handleSearch = async () => {
    setLoadingData(true);
    setErrorData(null);
    try {
      const filterParams = {
        clientIds: selectedClient ? [selectedClient] : null,
        skuIds: selectedSku ? [selectedSku] : null,
        startPeriod: startDate || null,
        endPeriod: endDate || null,
        keyFigureIds: selectedKeyFigures, 
        sources: selectedSources, 
      };

      const [historical, versioned] = await Promise.all([
        fetchHistoricalData(filterParams), // Obtener datos históricos
        fetchForecastVersionedData(filterParams), // Obtener datos de pronóstico versionado
      ]);

      setHistoryData(historical);
      setForecastVersionedData(versioned); 

    } catch (e) {
      // Manejamos errores generales de fetch o si no es un 404 de "No data found"
      setErrorData(e.message);
    } finally {
      setLoadingData(false);
    }
  };

  // Función para manejar el cambio en los filtros de KeyFigures
  const handleKeyFigureChange = (event) => {
    const { value, checked } = event.target;
    setSelectedKeyFigures(prev => {
        const currentSelection = prev || []; 
        const newSelection = checked ? [...currentSelection, value] : currentSelection.filter(kfId => kfId !== value);
        return newSelection.length > 0 ? newSelection : null; 
    });
  };

  // Función para manejar el cambio en los filtros de Fuentes
  const handleSourceChange = (event) => {
    const { value, checked } = event.target;
    setSelectedSources(prev => {
        const currentSelection = prev || [];
        const newSelection = checked ? [...currentSelection, value] : currentSelection.filter(source => source !== value);
        return newSelection.length > 0 ? newSelection : null;
    });
  };

  return (
    <section>
      <h2>Datos de Demanda y Pronóstico</h2>

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
                checked={selectedKeyFigures?.includes(String(kf.key_figure_id)) || false}
                onChange={handleKeyFigureChange}
              />
              {kf.name}
            </label>
          ))}
        </div>
        <div style={{ marginTop: '10px' }}>
          <label>Fuente (solo Histórico):</label>
          {['sales', 'order'].map(sourceOption => (
            <label key={sourceOption} style={{ marginLeft: '10px' }}>
              <input
                type="checkbox"
                value={sourceOption}
                checked={selectedSources?.includes(sourceOption) || false}
                onChange={handleSourceChange}
              />
              {sourceOption.charAt(0).toUpperCase() + sourceOption.slice(1)}
            </label>
          ))}
        </div>
        <button onClick={handleSearch} style={{ marginTop: '20px', padding: '10px 20px', cursor: 'pointer' }}>
          Buscar Datos
        </button>
      </div>

      {/* Mostrar Datos Históricos */}
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
                {historyData.map((item) => (
                  <tr key={`${item.client_id}-${item.sku_id}-${item.period}-${item.key_figure_id}-${item.source}`}>
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

          <h3 style={{ marginTop: '30px' }}>Datos de Pronóstico Versionado ({forecastVersionedData.length} registros)</h3>
          {forecastVersionedData.length === 0 ? (
            <p>No hay datos de pronóstico versionado para los filtros seleccionados.</p>
          ) : (
            <table border="1" style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }}>
              <thead>
                <tr>
                  <th>Versión ID</th>
                  <th>Cliente</th>
                  <th>SKU</th>
                  <th>Período</th>
                  <th>Figura Clave</th>
                  <th>Valor</th>
                </tr>
              </thead>
              <tbody>
                {forecastVersionedData.map((item) => (
                  <tr key={`${item.version_id}-${item.client_id}-${item.sku_id}-${item.period}-${item.key_figure_id}`}>
                    <td>{item.version?.name || String(item.version_id).substring(0, 8)}...</td> {/* Mostrar solo una parte del UUID si no hay nombre */}
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