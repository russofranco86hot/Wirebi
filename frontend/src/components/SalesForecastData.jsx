// frontend/src/components/SalesForecastData.jsx - Versión FINAL y COMPLETA (SOLUCIÓN DEFINITIVA DE HOOKS Y AG GRID)

import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
// Importaciones de API
import { 
  fetchClients, fetchSkus, fetchKeyFigures, 
  fetchHistoricalData, fetchForecastVersionedData, fetchForecastStatData, 
  generateForecast, sendManualAdjustment, fetchAdjustmentTypes 
} from '../api'; 

// Importaciones de AG Grid (estas rutas son CORRECTAS para ag-grid-community)
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css'; 
import 'ag-grid-community/styles/ag-theme-alpine.css';

import SalesChart from './SalesChart'; 

// --- Componente auxiliar para manejar la carga/error y renderizar la tabla AG Grid ---
// Este componente encapsula la lógica condicional para evitar romper las reglas de Hooks
const DataTableRenderer = React.memo(({ loading, error, rowData, columnDefs, onGridReady, onCellValueChanged, defaultColDef, gridRef }) => {
  // Manejamos la lógica de carga y error DENTRO de este componente auxiliar
  if (loading) {
    return <p>Cargando datos...</p>;
  }

  if (error) {
    return <p style={{ color: 'red' }}>Error al cargar datos: {error}</p>;
  }

  // --- Renderiza AG Grid solo si no hay carga ni error ---
  return (
    <div className="ag-theme-alpine" style={{ height: 600, width: '100%' }}>
      <AgGridReact
        ref={gridRef}
        rowData={rowData}
        columnDefs={columnDefs}
        animateRows={true}
        rowSelection={'multiple'}
        onGridReady={onGridReady}
        onCellValueChanged={onCellValueChanged}
        defaultColDef={defaultColDef} 
      />
    </div>
  );
});


function SalesForecastData() {
  // --- TODAS LAS DECLARACIONES DE ESTADOS Y HOOKS DEBEN IR AQUÍ AL PRINCIPIO ---
  // Estos deben ser lo primero que se declara dentro del componente funcional, sin excepciones.

  // ESTADOS
  const [historyData, setHistoryData] = useState([]);
  const [forecastVersionedData, setForecastVersionedData] = useState([]); 
  const [forecastStatData, setForecastStatData] = useState([]);
  const [loadingData, setLoadingData] = useState(false); 
  const [errorData, setErrorData] = useState(null);

  const [clients, setClients] = useState([]);
  const [skus, setSkus] = useState([]);
  const [keyFigures, setKeyFigures] = useState([]); 
  const [adjustmentTypes, setAdjustmentTypes] = useState([]); // Nuevo estado para tipos de ajuste

  const [selectedClient, setSelectedClient] = useState('');
  const [selectedSku, setSelectedSku] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedKeyFigures, setSelectedKeyFigures] = useState(null); 
  const [selectedSources, setSelectedSources] = useState(null); 

  const [forecastAlpha, setForecastAlpha] = useState(0.5);
  const [forecastModel, setForecastModel] = useState("ETS");
  const [forecastHorizon, setForecastHorizon] = useState(12);
  const [generatingForecast, setGeneratingForecast] = useState(false); 
  const [forecastGenerationError, setForecastGenerationError] = useState(null);
  const [forecastGenerationMessage, setForecastGenerationMessage] = useState(null);

  // REFS
  const gridRef = useRef(); 

  // Column Definitions para AG Grid (Es un estado, va al principio)
  const [columnDefs] = useState([ 
    { headerName: 'Cliente', field: 'clientName', minWidth: 150, filter: true, sortable: true },
    { headerName: 'SKU', field: 'skuName', minWidth: 150, filter: true, sortable: true },
    { headerName: 'Período', field: 'period', minWidth: 120, filter: 'agDateColumnFilter', sortable: true,
      valueFormatter: params => params.value ? new Date(params.value).toLocaleDateString('es-AR', { year: 'numeric', month: '2-digit', day: '2-digit' }) : ''
    },
    { headerName: 'Figura Clave', field: 'keyFigureName', minWidth: 150, filter: true, sortable: true },
    { headerName: 'Fuente', field: 'source', minWidth: 100, filter: true, sortable: true },
    { 
      headerName: 'Valor', 
      field: 'value', 
      minWidth: 120, 
      type: 'numericColumn',
      editable: true, 
      valueParser: params => Number(params.newValue),
      cellClassRules: {
        'rag-red': params => params.value < 0,
      }
    },
    { headerName: 'Modelo', field: 'modelUsed', minWidth: 100, filter: true, sortable: true },
    { headerName: 'Run ID', field: 'forecastRunId', minWidth: 100, filter: true, sortable: true, valueFormatter: params => params.value ? String(params.value).substring(0, 8) + '...' : '' },
  ]);

  // --- DEFINICIÓN DE CALLBACKS (useCallback) Y MEMOIZACIONES (useMemo) ---
  // Todas estas funciones deben declararse aquí, DESPUÉS de los `useState` y `useRef`.

  // Callbacks para AG Grid: Lógica de edición
  const isCellEditable = useCallback(params => {
    return params.colDef.field === 'value' && params.data.keyFigureName === 'Pronóstico Estadístico';
  }, []);

  const onCellValueChanged = useCallback(async event => { 
    console.log('Cell value changed:', event.data, 'New Value:', event.newValue, 'Old Value:', event.oldValue);
    
    if (event.newValue === event.oldValue) {
        return;
    }

    const { clientId, skuId, clientFinalId, period, keyFigureId, dataType } = event.data;
    const newValue = Number(event.newValue);

    const overrideAdjType = adjustmentTypes.find(type => type.name === 'Override');
    if (!overrideAdjType) {
        console.error("Tipo de ajuste 'Override' no encontrado. No se puede guardar el ajuste.");
        alert("Error: Tipo de ajuste 'Override' no configurado en la base de datos.");
        return;
    }
    const adjustmentTypeId = overrideAdjType.adjustment_type_id;

    try {
        const adjustmentPayload = {
            client_id: clientId,
            sku_id: skuId,
            client_final_id: clientFinalId,
            period: period, 
            key_figure_id: keyFigureId,
            adjustment_type_id: adjustmentTypeId,
            value: newValue,
            comment: `Ajuste manual de ${event.oldValue} a ${event.newValue} para ${event.data.keyFigureName}`,
            user_id: "00000000-0000-0000-0000-000000000001" 
        };
        
        await sendManualAdjustment(adjustmentPayload);
        console.log("Ajuste guardado exitosamente!");
        alert("Ajuste guardado exitosamente!");
    } catch (e) {
        console.error("Error al guardar el ajuste manual:", e);
        alert(`Error al guardar el ajuste: ${e.message}`);
    }
  }, [adjustmentTypes]); 


  const onGridReady = useCallback((params) => {
    // params.api.sizeColumnsToFit();
  }, []);

  const memoizedColumnDefs = useMemo(() => {
    return columnDefs.map(col => {
      if (col.field === 'value') {
        return { ...col, editable: isCellEditable };
      }
      return col;
    });
  }, [columnDefs, isCellEditable]); 


  const rowData = useMemo(() => {
    const combined = [];

    historyData.forEach(item => {
      combined.push({
        id: `${item.client_id}-${item.sku_id}-${item.period}-${item.key_figure_id}-${item.source}`,
        clientName: item.client?.client_name || 'N/A',
        skuName: item.sku?.sku_name || 'N/A',
        period: item.period,
        keyFigureName: item.key_figure?.name || 'N/A',
        source: item.source,
        value: item.value,
        modelUsed: 'Historia',
        forecastRunId: 'N/A',
        clientId: item.client_id,
        skuId: item.sku_id,
        clientFinalId: item.client_final_id,
        keyFigureId: item.key_figure_id,
        dataType: 'history'
      });
    });

    forecastStatData.forEach(item => {
      combined.push({
        id: `${item.client_id}-${item.sku_id}-${item.period}-${item.forecast_run_id}-stat`,
        clientName: item.client?.client_name || 'N/A',
        skuName: item.sku?.sku_name || 'N/A',
        period: item.period,
        keyFigureName: 'Pronóstico Estadístico',
        source: 'Forecast',
        value: item.value,
        modelUsed: item.model_used,
        forecastRunId: item.forecast_run_id,
        clientId: item.client_id,
        skuId: item.sku_id,
        clientFinalId: item.client_final_id,
        keyFigureId: 4, 
        dataType: 'forecast_stat'
      });
    });

    return combined.sort((a, b) => {
      if (a.clientName !== b.clientName) return a.clientName.localeCompare(b.clientName);
      if (a.skuName !== b.skuName) return a.skuName.localeCompare(b.skuName);
      if (a.period !== b.period) return new Date(a.period) - new Date(b.period);
      if (a.dataType === 'history' && b.dataType === 'forecast_stat') return -1;
      if (a.dataType === 'forecast_stat' && b.dataType === 'history') return 1;
      return 0;
    });
  }, [historyData, forecastStatData]);


  // Manejadores de cambios en filtros (useCallback)
  const handleKeyFigureChange = useCallback((event) => {
    const { value, checked } = event.target;
    setSelectedKeyFigures(prev => {
        const currentSelection = prev || []; 
        const newSelection = checked ? [...currentSelection, value] : currentSelection.filter(kfId => kfId !== value);
        return newSelection.length > 0 ? newSelection : null; 
    });
  }, []);

  const handleSourceChange = useCallback((event) => {
    const { value, checked } = event.target;
    setSelectedSources(prev => {
        const currentSelection = prev || [];
        const newSelection = checked ? [...currentSelection, value] : currentSelection.filter(source => source !== value);
        return newSelection.length > 0 ? newSelection : null;
    });
  }, []); 

  // Función para manejar la búsqueda de datos (handleSearch)
  const handleSearch = useCallback(async () => { 
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

      const [historical, versioned, forecastStat] = await Promise.all([ 
        fetchHistoricalData(filterParams), 
        fetchForecastVersionedData(filterParams), 
        fetchForecastStatData({ 
            clientIds: filterParams.clientIds,
            skuIds: filterParams.skuIds,
            startPeriod: filterParams.startPeriod,
            endPeriod: filterParams.endPeriod,
        })
      ]);

      setHistoryData(historical);
      setForecastVersionedData(versioned); 
      setForecastStatData(forecastStat); 

    } catch (e) {
      setErrorData(e.message);
    } finally {
      setLoadingData(false);
    }
  }, [selectedClient, selectedSku, startDate, endDate, selectedKeyFigures, selectedSources]); 


  // Función para disparar la generación de Forecast (handleGenerateForecast)
  const handleGenerateForecast = useCallback(async () => {
    setGeneratingForecast(true);
    setForecastGenerationError(null);
    setForecastGenerationMessage(null);

    if (!selectedClient || !selectedSku || !selectedSources || selectedSources.length === 0) {
        setForecastGenerationError("Por favor, selecciona un Cliente, un SKU y al menos una Fuente para generar el pronóstico.");
        setGeneratingForecast(false);
        return;
    }
    const historySource = selectedSources[0]; 

    try {
        const result = await generateForecast({
            clientId: selectedClient,
            skuId: selectedSku,
            historySource: historySource,
            smoothingAlpha: parseFloat(forecastAlpha), 
            modelName: forecastModel,
            forecastHorizon: parseInt(forecastHorizon, 10), 
        });
        setForecastGenerationMessage(result.message);
        await handleSearch(); 
    }
    // NOTA: Si el backend lanza un RuntimeError, este catch lo captura.
    // Asegúrate de que los errores específicos del backend (ej. "tiny datasets")
    // sean lanzados como RuntimeError y capturados aquí.
    catch (e) {
        setForecastGenerationError(e.message);
    } finally {
        setGeneratingForecast(false);
    }
  }, [selectedClient, selectedSku, selectedSources, forecastAlpha, forecastModel, forecastHorizon, handleSearch]); 

  // --- EFECTOS (useEffect va DESPUÉS de todas las declaraciones de estados y callbacks/memo) ---
  useEffect(() => {
    const loadDimensions = async () => {
      try {
        const [clientsData, skusData, keyFiguresData, adjustmentTypesData] = await Promise.all([ 
          fetchClients(),
          fetchSkus(),
          fetchKeyFigures(),
          fetchAdjustmentTypes(), // Nueva llamada a API para tipos de ajuste
        ]);
        setClients(clientsData);
        setSkus(skusData);
        setKeyFigures(keyFiguresData);
        setAdjustmentTypes(adjustmentTypesData); // Guardar tipos de ajuste
      } catch (e) {
        console.error("Error loading dimensions:", e);
        setErrorData("Error al cargar dimensiones para filtros: " + e.message);
      }
    };
    loadDimensions();
  }, []);

  // --- Renderizado Principal del Componente ---
  // Este bloque `return` SIEMPRE se ejecuta. Las condiciones de carga/error se manejan internamente por DataTableRenderer.
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
          {['sales', 'order', 'shipments'].map(sourceOption => (
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

      {/* Sección de Generación de Forecast */}
      <div style={{ 
          marginBottom: '20px', 
          border: '1px solid #0056b3', 
          padding: '15px', 
          background: '#e6f7ff',
          color: '#333'
      }}>
        <h3>Generar Pronóstico Estadístico</h3>
        <p>Selecciona un Cliente y un SKU y una Fuente para generar el pronóstico.</p>
        <p style={{ fontSize: '0.8em', color: '#666' }}>
            Nota: Los modelos de pronóstico requieren un mínimo de datos históricos (al menos 5-10 puntos de datos por Cliente-SKU).
            Si no hay suficientes datos, la generación fallará.
        </p>
        <div>
            <label style={{ color: '#333' }}>Modelo:</label>
            <select value={forecastModel} onChange={e => setForecastModel(e.target.value)} style={{ color: '#333', background: 'white' }}>
                <option value="ETS">ETS (Exponential Smoothing)</option>
                <option value="ARIMA">ARIMA</option>
            </select>
        </div>
        <div style={{ marginTop: '10px' }}>
            <label style={{ color: '#333' }}>Alpha (0.0-1.0, solo para ETS):</label>
            <input type="number" step="0.1" min="0" max="1" value={forecastAlpha} onChange={e => setForecastAlpha(e.target.value)} style={{ color: '#333', background: 'white' }}/>
        </div>
        <div style={{ marginTop: '10px' }}>
            <label style={{ color: '#333' }}>Horizonte (meses):</label>
            <input type="number" step="1" min="1" value={forecastHorizon} onChange={e => setForecastHorizon(e.target.value)} style={{ color: '#333', background: 'white' }}/>
        </div>
        <button onClick={handleGenerateForecast} disabled={generatingForecast} style={{ marginTop: '20px', padding: '10px 20px', cursor: 'pointer' }}>
          {generatingForecast ? 'Generando...' : 'Generar Pronóstico'}
        </button>
        {forecastGenerationMessage && <p style={{ color: 'green', marginTop: '10px' }}>{forecastGenerationMessage}</p>}
        {forecastGenerationError && <p style={{ color: 'red', marginTop: '10px' }}>{forecastGenerationError}</p>}
      </div>


      {/* Gráfico de Datos */}
      <SalesChart 
        historyData={historyData} 
        forecastStatData={forecastStatData} 
        keyFigures={keyFigures} 
        selectedKeyFigures={selectedKeyFigures}
        selectedSources={selectedSources}
      />


      {/* --- TABLA AG GRID (Ahora renderizada por el componente auxiliar) --- */}
      <h3 style={{ marginTop: '30px' }}>Datos de Detalle (AG Grid)</h3>
      {/* El bloque if/else para loadingData/errorData para la tabla AG Grid */}
      <DataTableRenderer 
        loading={loadingData} 
        error={errorData} 
        rowData={rowData} 
        columnDefs={memoizedColumnDefs} 
        onGridReady={onGridReady} 
        onCellValueChanged={onCellValueChanged} 
        defaultColDef={useMemo(() => ({ // useMemo para defaultColDef
          flex: 1,
          minWidth: 100,
          resizable: true,
        }), [])}
        gridRef={gridRef}
      />

    </section>
  );
}

export default SalesForecastData;