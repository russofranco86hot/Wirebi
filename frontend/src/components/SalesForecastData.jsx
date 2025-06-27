// frontend/src/components/SalesForecastData.jsx

import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import {
  fetchClients, fetchSkus, fetchKeyFigures,
  fetchHistoricalData, fetchForecastVersionedData, fetchForecastStatData,
  generateForecast, sendManualAdjustment, fetchAdjustmentTypes,
  fetchCleanHistoryData, fetchFinalForecastData, sendComment, fetchComments
} from '../api';

import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

import SalesChart from './SalesChart';

// Constantes para IDs de Key Figures
const KF_SALES_ID = 1;
const KF_ORDER_ID = 2;
const KF_SHIPMENTS_ID = 3;
const KF_STATISTICAL_FORECAST_ID = 4;
const KF_CLEAN_HISTORY_ID = 5;
const KF_FINAL_FORECAST_ID = 6;


// Componente auxiliar para manejar la carga/error y renderizar la tabla AG Grid
const DataTableRenderer = React.memo(({ loading, error, rowData, columnDefs, onGridReady, onCellValueChanged, defaultColDef, gridRef, getContextMenuItems }) => {
  if (loading) {
    return <p>Cargando datos...</p>;
  }

  if (error) {
    return <p style={{ color: 'red' }}>Error al cargar datos: {error}</p>;
  }

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
        getContextMenuItems={getContextMenuItems} // Añadido para el menú contextual
      />
    </div>
  );
});


// Nuevo componente Modal para Comentarios
const CommentModal = ({ isOpen, onClose, cellData, comments, onSaveComment }) => {
  const [newComment, setNewComment] = useState('');

  useEffect(() => {
    // Limpiar el campo de texto cuando se abre o cambia la celda seleccionada
    if (isOpen) {
      setNewComment('');
    }
  }, [isOpen, cellData]);

  if (!isOpen) return null;

  const handleSave = () => {
    if (newComment.trim()) {
      onSaveComment(cellData, newComment);
      setNewComment('');
    }
  };

  return (
    <div style={{
      position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
      backgroundColor: 'white', padding: '20px', border: '1px solid #ccc',
      zIndex: 1000, boxShadow: '0 4px 8px rgba(0,0,0,0.1)', minWidth: '400px', maxWidth: '600px'
    }}>
      <h3>Comentarios para {cellData?.clientName} - {cellData?.skuName} - {new Date(cellData?.period).toLocaleDateString()} ({cellData?.keyFigureName})</h3>
      
      <h4>Agregar nuevo comentario:</h4>
      <textarea
        value={newComment}
        onChange={(e) => setNewComment(e.target.value)}
        placeholder="Escribe tu comentario aquí..."
        rows="4"
        style={{ width: '100%', marginBottom: '10px' }}
      />
      <button onClick={handleSave} style={{ marginRight: '10px' }}>Guardar Comentario</button>
      <button onClick={onClose}>Cerrar</button>

      {comments && comments.length > 0 && (
        <>
          <h4>Historial de Comentarios:</h4>
          <div style={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid #eee', padding: '10px' }}>
            {comments.map((comment, index) => (
              <div key={index} style={{ marginBottom: '10px', paddingBottom: '5px', borderBottom: '1px dashed #eee' }}>
                <p><strong>{comment.timestamp ? new Date(comment.timestamp).toLocaleString() : 'Fecha Desconocida'}</strong></p>
                <p>{comment.comment}</p>
              </div>
            ))}
          </div>
        </>
      )}
      {comments && comments.length === 0 && <p>No hay comentarios anteriores para esta celda.</p>}
    </div>
  );
};


function SalesForecastData() {
  // --- TODAS LAS DECLARACIONES DE ESTADOS Y HOOKS DEBEN IR AQUÍ AL PRINCIPIO ---
  // Estos deben ser lo primero que se declara dentro del componente funcional, sin excepciones.

  // ESTADOS
  const [historyData, setHistoryData] = useState([]);
  const [forecastVersionedData, setForecastVersionedData] = useState([]);
  const [forecastStatData, setForecastStatData] = useState([]);
  const [cleanHistoryData, setCleanHistoryData] = useState([]);
  const [finalForecastData, setFinalForecastData] = useState([]);
  const [loadingData, setLoadingData] = useState(false);
  const [errorData, setErrorData] = useState(null);

  const [clients, setClients] = useState([]);
  const [skus, setSkus] = useState([]);
  const [keyFigures, setKeyFigures] = useState([]);
  const [adjustmentTypes, setAdjustmentTypes] = useState([]);

  const [selectedClient, setSelectedClient] = useState('');
  const [selectedSku, setSelectedSku] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const [selectedKeyFigures, setSelectedKeyFigures] = useState(null);
  const [selectedSources, setSelectedSources] = useState([]);

  const [forecastAlpha, setForecastAlpha] = useState(0.5);
  const [forecastModel, setForecastModel] = useState("ETS");
  const [forecastHorizon, setForecastHorizon] = useState(12);
  const [generatingForecast, setGeneratingForecast] = useState(false);
  const [forecastGenerationError, setForecastGenerationError] = useState(null);
  const [forecastGenerationMessage, setForecastGenerationMessage] = useState(null);

  const [isCommentModalOpen, setIsCommentModalOpen] = useState(false);
  const [selectedCellForComment, setSelectedCellForComment] = useState(null);
  const [commentsForSelectedCell, setCommentsForSelectedCell] = useState([]);

  const [forecastStartDate, setForecastStartDate] = useState(null);

  // REFS
  const gridRef = useRef();

  // --- DEFINICIÓN DE CALLBACKS (useCallback) Y MEMOIZACIONES (useMemo) ---
  // Todas estas funciones deben declararse aquí, DESPUÉS de los `useState` y `useRef`.
  // Es crucial que las funciones que son dependencias de otras se declaren primero.

  // Función para manejar la búsqueda de datos (handleSearch) - DECLARADA TEMPRANO YA QUE OTRAS LA USAN
  const handleSearch = useCallback(async () => {
    setLoadingData(true);
    setErrorData(null);
    try {
      const filterParams = {
        clientIds: selectedClient ? [selectedClient] : null,
        skuIds: selectedSku ? [selectedSku] : null,
        startPeriod: startDate || null,
        endPeriod: endDate || null, // Se usará el endDate actualizado por handleGenerateForecast o el del filtro
        keyFigureIds: selectedKeyFigures,
        sources: selectedSources,
        clientId: selectedClient || null,
        skuId: selectedSku || null,
        clientFinalId: selectedClient || '00000000-0000-0000-0000-000000000001',
      };

      const [historical, versioned, forecastStat, cleanHistory, finalForecast, allComments] = await Promise.all([
        fetchHistoricalData(filterParams),
        fetchForecastVersionedData(filterParams),
        fetchForecastStatData({
            clientIds: filterParams.clientIds,
            skuIds: filterParams.skuIds,
            startPeriod: filterParams.startPeriod,
            endPeriod: filterParams.endPeriod,
        }),
        selectedClient && selectedSku && startDate && endDate ? fetchCleanHistoryData(filterParams) : Promise.resolve([]),
        selectedClient && selectedSku && startDate && endDate ? fetchFinalForecastData(filterParams) : Promise.resolve([]),
        fetchComments({
            clientIds: filterParams.clientIds,
            skuIds: filterParams.skuIds,
            startPeriod: filterParams.startPeriod,
            endPeriod: filterParams.endPeriod,
        }),
      ]);

      setHistoryData(historical);
      setForecastVersionedData(versioned);
      setForecastStatData(forecastStat);
      setCleanHistoryData(cleanHistory);
      setFinalForecastData(finalForecast);
      setCommentsForSelectedCell(allComments);

      // Calcular y establecer forecastStartDate
      if (forecastStat.length > 0) {
        const minForecastPeriod = forecastStat.reduce((min, p) => 
          new Date(p.period) < new Date(min.period) ? p : min, forecastStat[0]
        ).period;
        setForecastStartDate(new Date(minForecastPeriod));
      } else {
        setForecastStartDate(null); // Si no hay pronóstico, no hay fecha de inicio de pronóstico
      }

      console.log("DEBUG: handleSearch - Fetched Historical Data Count:", historical.length); // Log de depuración
      console.log("DEBUG: handleSearch - Fetched Forecast Stat Data Count:", forecastStat.length); // Log de depuración
      if (forecastStat.length > 0) {
        console.log("DEBUG: handleSearch - First Forecast Stat Period:", forecastStat[0].period); // Log de depuración
        console.log("DEBUG: handleSearch - Last Forecast Stat Period:", forecastStat[forecastStat.length - 1].period); // Log de depuración
      }
      console.log("DEBUG: handleSearch - Forecast Start Date Set To:", forecastStartDate ? forecastStartDate.toISOString().split('T')[0] : 'null'); // Log de depuración


    } catch (e) {
      setErrorData(e.message);
    } finally {
      setLoadingData(false);
    }
  }, [selectedClient, selectedSku, startDate, endDate, selectedKeyFigures, selectedSources]);


  // Función para disparar la generación de Forecast (handleGenerateForecast) - También usa handleSearch
  const handleGenerateForecast = useCallback(async () => {
    setGeneratingForecast(true);
    setForecastGenerationError(null);
    setForecastGenerationMessage(null);

    // Validaciones más robustas
    if (!selectedClient || selectedClient === '') {
        setForecastGenerationError("Por favor, selecciona un Cliente válido.");
        setGeneratingForecast(false);
        return;
    }
    if (!selectedSku || selectedSku === '') {
        setForecastGenerationError("Por favor, selecciona un SKU válido.");
        setGeneratingForecast(false);
        return;
    }
    if (!selectedSources || selectedSources.length === 0 || !selectedSources[0]) {
        setForecastGenerationError("Por favor, selecciona al menos una Fuente de historial válida (Sales, Order o Shipments).");
        setGeneratingForecast(false);
        return;
    }
    const historySource = selectedSources[0];
    const validSources = ['sales', 'order', 'shipments'];
    if (!validSources.includes(historySource)) {
        setForecastGenerationError("La fuente del historial seleccionada no es válida. Por favor, elige 'Sales', 'Order' o 'Service'.");
        setGeneratingForecast(false);
        return;
    }
    
    const smoothingAlpha = parseFloat(forecastAlpha);
    const forecastHorizonInt = parseInt(forecastHorizon, 10);

    if (isNaN(smoothingAlpha) || smoothingAlpha < 0 || smoothingAlpha > 1) {
      setForecastGenerationError("El valor de Alpha (0.0-1.0) no es válido.");
      setGeneratingForecast(false);
      return;
    }
    if (isNaN(forecastHorizonInt) || forecastHorizonInt < 1) {
      setForecastGenerationError("El Horizonte de pronóstico (meses) debe ser un número entero mayor o igual a 1.");
      setGeneratingForecast(false);
      return;
    }


    try {
        const result = await generateForecast({
            clientId: selectedClient,
            skuId: selectedSku,
            historySource: historySource,
            smoothingAlpha: smoothingAlpha,
            modelName: forecastModel,
            forecastHorizon: forecastHorizonInt,
        });
        setForecastGenerationMessage(result.message);

        // --- INICIO: Lógica para extender el endDate del filtro ---
        // Obtener la fecha del último dato histórico cargado.
        let latestHistoricalPeriod = new Date(startDate); // Valor por defecto si no hay datos históricos
        if (historyData && historyData.length > 0) {
            latestHistoricalPeriod = historyData.reduce((latest, p) =>
                new Date(p.period) > new Date(latest.period) ? p : latest, historyData[0]
            ).period;
            latestHistoricalPeriod = new Date(latestHistoricalPeriod);
        }
        
        // Calcular la fecha final de la visualización (último mes del pronóstico)
        // Partimos del último mes histórico + el horizonte de pronóstico
        const lastForecastMonthDate = new Date(latestHistoricalPeriod);
        lastForecastMonthDate.setMonth(latestHistoricalPeriod.getMonth() + forecastHorizonInt);
        // Para asegurar que sea el último día del mes, vamos al siguiente mes y restamos 1 día.
        const finalFetchEndDate = new Date(lastForecastMonthDate.getFullYear(), lastForecastMonthDate.getMonth() + 1, 0);

        console.log("DEBUG: handleGenerateForecast - Calculated finalFetchEndDate:", finalFetchEndDate.toISOString().split('T')[0]); // Log de depuración
        // Actualizar el estado endDate del filtro. Esto provocará que handleSearch use este nuevo rango.
        setEndDate(finalFetchEndDate.toISOString().split('T')[0]);
        // --- FIN: Lógica para extender el endDate del filtro ---

        await handleSearch(); // Recargar datos para ver el nuevo pronóstico y las figuras calculadas
    }
    catch (e) {
        setForecastGenerationError(e.message);
    } finally {
        setGeneratingForecast(false);
    }
  }, [selectedClient, selectedSku, selectedSources, forecastAlpha, forecastModel, forecastHorizon, handleSearch, startDate, historyData, setEndDate]); // Añadido setEndDate a las dependencias


  // Callbacks para AG Grid: Lógica de edición
  const isCellEditable = useCallback(params => {
    // Permitir edición solo si la columna es editable Y es Pronóstico Estadístico o Pronóstico Final
    // params.colDef.editable viene del dynamicColumnDefs
    // params.colDef.colId viene del dynamicColumnDefs y es algo como "YYYY-MM-DD_KeyFigureName"
    if (!params.colDef.editable || !params.colDef.colId || !params.colDef.colId.includes('_')) {
        return false; // No editable si no es una columna de valor dinámica o no está marcada como editable
    }
    const keyFigureNameInColumn = params.colDef.colId.split('_').pop();
    return (keyFigureNameInColumn === 'Pronóstico Estadístico' || keyFigureNameInColumn === 'Pronóstico Final');
  }, []);


  const onCellValueChanged = useCallback(async event => {
    console.log('Cell value changed:', event.data, 'New Value:', event.newValue, 'Old Value:', event.oldValue);
    console.log('Column ID (event.colDef.colId):', event.colDef.colId);
    console.log('event.colDef object:', event.colDef);
    console.log('Full event object:', event);


    if (event.newValue === event.oldValue) {
      return;
    }

    // Verificar si la columna es una de las dinámicas de período/figura clave
    // Esta validación ya debería ser cubierta por isCellEditable, pero se mantiene como doble chequeo.
    if (!event.colDef.colId || !event.colDef.colId.includes('_')) {
        console.warn("Edición ignorada: Columna no reconocida para edición de datos de pronóstico/historial.");
        return;
    }

    const [periodString, keyFigureName] = event.colDef.colId.split('_');
    const period = new Date(periodString);
    const newValue = Number(event.newValue);

    const { clientId, skuId, clientFinalId } = event.data;

    const keyFigure = keyFigures.find(kf => kf.name === keyFigureName);
    if (!keyFigure) {
        console.error(`Key Figure '${keyFigureName}' no encontrada. No se puede guardar el ajuste.`);
        return;
    }
    const keyFigureId = keyFigure.key_figure_id;

    let adjustmentTypeId;
    // La lógica de isCellEditable ya garantiza que solo se edita Pronóstico Estadístico o Final
    const overrideAdjType = adjustmentTypes.find(type => type.name === 'Override');
    if (!overrideAdjType) {
        console.error("Tipo de ajuste 'Override' no encontrado. No se puede guardar el ajuste.");
        return;
    }
    adjustmentTypeId = overrideAdjType.adjustment_type_id;

    try {
      const adjustmentPayload = {
        client_id: clientId,
        sku_id: skuId,
        client_final_id: clientFinalId,
        period: period.toISOString().split('T')[0],
        key_figure_id: keyFigureId,
        adjustment_type_id: adjustmentTypeId,
        value: newValue,
        comment: `Ajuste manual de ${event.oldValue} a ${event.newValue} para ${keyFigureName} en ${period.toLocaleDateString()}`,
        user_id: "00000000-0000-0000-0000-000000000001"
      };

      await sendManualAdjustment(adjustmentPayload);
      console.log("Ajuste guardado exitosamente!");

      // --- INICIO: Actualización de estado local para feedback inmediato ---
      const updateSpecificState = (prevData) => {
          return prevData.map(item => {
              const itemPeriodIso = new Date(item.period).toISOString().split('T')[0];
              const targetPeriodIso = period.toISOString().split('T')[0];

              if (item.client_id === clientId && item.sku_id === skuId && itemPeriodIso === targetPeriodIso) {
                  console.log(`DEBUG: Found item for update! Changing value for ${item.client_id}-${item.sku_id}-${itemPeriodIso} from ${item.value} to ${newValue}`);
                  return { ...item, value: newValue };
              }
              return item;
          });
      };

      if (keyFigureName === 'Pronóstico Estadístico') {
        setForecastStatData(prevData => updateSpecificState(prevData));
      } else if (keyFigureName === 'Pronóstico Final') {
        setFinalForecastData(prevData => updateSpecificState(prevData));
      }
      // --- FIN: Actualización de estado local para feedback inmediato ---
      
      // La recarga completa asegura la consistencia de los datos desde el backend,
      // incluyendo cualquier cálculo que dependa de los ajustes.
      // Se ejecuta DESPUÉS de la actualización local.
      // handleSearch(); // Comentado para depurar la persistencia visual. No descomentar.
      
    } catch (e) {
      console.error("Error al guardar el ajuste manual:", e);
    }
  }, [adjustmentTypes, keyFigures, forecastStatData, finalForecastData]);


  const onGridReady = useCallback((params) => {
    // params.api.sizeColumnsToFit();
  }, []);


  // --- Funciones para el Modal de Comentarios ---
  const openCommentModal = useCallback(async (cellData) => {
    setSelectedCellForComment(cellData);
    setIsCommentModalOpen(true);
    // Fetch comments for the selected cell
    try {
      const fetchedComments = await fetchComments({
        clientIds: [cellData.clientId],
        skuIds: [cellData.skuId],
        startPeriod: cellData.period.toISOString().split('T')[0],
        endPeriod: cellData.period.toISOString().split('T')[0],
        keyFigureIds: [cellData.keyFigureId],
      });
      setCommentsForSelectedCell(fetchedComments);
    } catch (error) {
      console.error("Error fetching comments:", error);
      setCommentsForSelectedCell([]);
    }
  }, []);

  const closeCommentModal = useCallback(() => {
    setIsCommentModalOpen(false);
    setSelectedCellForComment(null);
    setCommentsForSelectedCell([]);
  }, []);

  const handleSaveComment = useCallback(async (cellData, commentText) => {
    const commentPayload = {
      client_id: cellData.clientId,
      sku_id: cellData.skuId,
      client_final_id: cellData.clientFinalId,
      period: cellData.period.toISOString().split('T')[0],
      key_figure_id: cellData.keyFigureId,
      comment: commentText,
      user_id: "00000000-0000-0000-0000-000000000001",
    };

    try {
      await sendComment(commentPayload);
      console.log("Comentario guardado exitosamente!");
      
      handleSearch(); // Recargar todos los datos para asegurar la consistencia de los iconos
      
    } catch (e) {
      console.error("Error al guardar el comentario:", e);
    }
  }, [handleSearch]);

  // --- Menú Contextual (Clic Derecho) de AG Grid ---
  const getContextMenuItems = useCallback((params) => {
    const defaultItems = params.defaultItems.filter(item => item !== 'copyWithHeaders' && item !== 'paste');
    const cellData = params.node?.data;

    if (!cellData || !params.column) return defaultItems;

    let period = null;
    let keyFigureName = null;
    let keyFigureId = null;

    if (params.column.colId && params.column.colId.includes('_')) {
        const [periodStr, kfName] = params.column.colId.split('_');
        period = new Date(periodStr);
        keyFigureName = kfName;
        const kf = keyFigures.find(k => k.name === keyFigureName);
        keyFigureId = kf ? kf.key_figure_id : null;
    } else {
        return defaultItems;
    }

    if (!period || !keyFigureId) {
        return defaultItems;
    }

    const dataForComment = {
        ...cellData,
        period: period,
        keyFigureName: keyFigureName,
        keyFigureId: keyFigureId,
        id: `${cellData.clientId}-${cellData.skuId}-${period.toISOString().split('T')[0]}-${keyFigureId}`,
    };

    return [
      ...defaultItems,
      'separator',
      {
        name: 'Agregar un comentario',
        action: () => {
          openCommentModal(dataForComment);
        },
        icon: '<span class="ag-icon ag-icon-comments"></span>',
      },
      {
        name: 'Ver historial de comentarios anteriores',
        action: () => {
          openCommentModal(dataForComment);
        },
        icon: '<span class="ag-icon ag-icon-clipboard"></span>',
      },
    ];
  }, [openCommentModal, keyFigures]);


  // --- NUEVA LÓGICA: Preparación de rowData pivotada y ColumnDefs dinámicas ---
  const { processedRowData, dynamicColumnDefs } = useMemo(() => {
    // console.log("DEBUG: useMemo dependencies:", { historyData, forecastStatData, cleanHistoryData, finalForecastData, keyFigures, commentsForSelectedCell, forecastStartDate });

    const allData = [
      ...historyData.map(item => ({ ...item, type: 'history', kf_id: item.key_figure_id, kf_name: item.key_figure?.name || 'N/A' })),
      ...forecastStatData.map(item => ({ ...item, type: 'forecast_stat', kf_id: KF_STATISTICAL_FORECAST_ID, kf_name: 'Pronóstico Estadístico' })),
      ...cleanHistoryData.map(item => ({ ...item, type: 'clean_history', kf_id: KF_CLEAN_HISTORY_ID, kf_name: 'Historia Limpia' })),
      ...finalForecastData.map(item => ({ ...item, type: 'final_forecast', kf_id: KF_FINAL_FORECAST_ID, kf_name: 'Pronóstico Final' })),
    ];

    const uniquePeriods = new Set();
    const uniqueKeyFigureNames = new Set();
    
    const commentsMap = {};
    commentsForSelectedCell.forEach(comment => {
        const periodString = new Date(comment.period).toISOString().split('T')[0];
        const id = `${comment.client_id}-${comment.sku_id}-${periodString}-${comment.key_figure_id}`;
        commentsMap[id] = true;
    });


    // Agrupar datos por Cliente y SKU y consolidar por período y figura clave
    const groupedData = allData.reduce((acc, item) => {
        const clientKey = item.client_id;
        const skuKey = item.sku_id;
        const clientFinalKey = item.client_final_id;
        const groupKey = `${clientKey}-${skuKey}-${clientFinalKey}`;

        if (!acc[groupKey]) {
            acc[groupKey] = {
                id: groupKey, // ID único para la fila
                clientId: clientKey,
                skuId: skuKey,
                clientFinalId: clientFinalKey,
                clientName: item.clientName || item.client?.client_name || 'N/A',
                skuName: item.skuName || item.sku?.sku_name || 'N/A',
            };
        }

        const periodDate = new Date(item.period);
        const periodIso = periodDate.toISOString().split('T')[0]; //YYYY-MM-DD
        uniquePeriods.add(periodIso);
        uniqueKeyFigureNames.add(item.kf_name);

        // Lógica de visualización condicional: Mostrar solo las cifras clave apropiadas para el período
        const isHistoricalPeriod = forecastStartDate ? periodDate < forecastStartDate : true;
        const isForecastPeriod = forecastStartDate ? periodDate >= forecastStartDate : false;

        let valueToDisplay = undefined;

        switch (item.kf_id) {
            case KF_SALES_ID:
            case KF_ORDER_ID:
            case KF_SHIPMENTS_ID:
                if (isHistoricalPeriod) {
                    valueToDisplay = item.value;
                }
                break;
            case KF_CLEAN_HISTORY_ID:
                if (isHistoricalPeriod) {
                    valueToDisplay = item.value;
                }
                break;
            case KF_STATISTICAL_FORECAST_ID:
            case KF_FINAL_FORECAST_ID:
                if (isForecastPeriod) {
                    valueToDisplay = item.value;
                }
                break;
            default:
                valueToDisplay = item.value; // Por si acaso hay otros kf_id
                break;
        }


        const colIdPrefix = `${periodIso}_`;
        const colId = `${colIdPrefix}${item.kf_name}`;

        acc[groupKey][colId] = valueToDisplay;

        const commentCellId = `${clientKey}-${skuKey}-${periodIso}-${item.kf_id}`;
        const commentIconColId = `${colId}_hasComment`;
        if (commentsMap[commentCellId]) {
            acc[groupKey][commentIconColId] = true;
        }

        return acc;
    }, {});

    const processedRowData = Object.values(groupedData).sort((a, b) => {
        if (a.clientName !== b.clientName) return a.clientName.localeCompare(b.clientName);
        if (a.skuName !== b.skuName) return a.skuName.localeCompare(b.skuName);
        return 0;
    });

    // Generar Column Definitions dinámicas
    const initialColumnDefs = [
      { 
          headerName: 'Cliente', 
          field: 'clientName', 
          minWidth: 150, 
          filter: true, 
          sortable: true, 
          pinned: 'left',
          suppressMovable: true, 
          editable: false 
      },
      { 
          headerName: 'SKU', 
          field: 'skuName', 
          minWidth: 150, 
          filter: true, 
          sortable: true, 
          pinned: 'left',
          suppressMovable: true, 
          editable: false 
      },
    ];

    const sortedPeriods = Array.from(uniquePeriods).sort();
    const sortedKeyFigureNames = Array.from(uniqueKeyFigureNames).sort((a, b) => {
        const order = { 'Sales': 1, 'Order': 2, 'Shipments': 3, 'Historia Limpia': 4, 'Pronóstico Estadístico': 5, 'Pronóstico Final': 6 };
        return (order[a] || 99) - (order[b] || 99);
    });

    const dynamicPeriodColumns = sortedPeriods.map(periodIso => {
        const periodDate = new Date(periodIso);
        const headerPeriodName = periodDate.toLocaleDateString('es-AR', { month: 'short', year: 'numeric' });

        // Filtrar KeyFigures a mostrar para este período
        const children = sortedKeyFigureNames
            .filter(kfName => {
                const isHistoricalKf = [keyFigures.find(k => k.key_figure_id === KF_SALES_ID)?.name, 
                                        keyFigures.find(k => k.key_figure_id === KF_ORDER_ID)?.name,
                                        keyFigures.find(k => k.key_figure_id === KF_SHIPMENTS_ID)?.name,
                                        keyFigures.find(k => k.key_figure_id === KF_CLEAN_HISTORY_ID)?.name].includes(kfName);
                const isForecastKf = [keyFigures.find(k => k.key_figure_id === KF_STATISTICAL_FORECAST_ID)?.name, 
                                      keyFigures.find(k => k.key_figure_id === KF_FINAL_FORECAST_ID)?.name].includes(kfName);

                const isHistoricalPeriod = forecastStartDate ? periodDate < forecastStartDate : true;
                const isForecastPeriod = forecastStartDate ? periodDate >= forecastStartDate : false;

                // Si no hay forecastStartDate, todo es histórico
                if (!forecastStartDate) {
                    return isHistoricalKf; // Solo mostrar las históricas
                }
                
                // Mostrar solo la figura clave si su tipo de período coincide con el período actual
                return (isHistoricalPeriod && isHistoricalKf) || (isForecastPeriod && isForecastKf);
            })
            .map(kfName => {
                const colId = `${periodIso}_${kfName}`;
                const keyFigure = keyFigures.find(k => k.name === kfName);
                const isEditable = keyFigure ? keyFigure.editable : false;
                
                return {
                    headerName: kfName,
                    field: colId,
                    colId: colId, // Asegúrate de que colId se asigna explícitamente
                    minWidth: 100,
                    editable: isEditable && (kfName === 'Pronóstico Estadístico' || kfName === 'Pronóstico Final'), 
                    type: 'numericColumn',
                    valueParser: params => Number(params.newValue),
                    cellClassRules: {
                        'rag-red': params => params.value < 0,
                        'has-comments': params => params.data[`${colId}_hasComment`], 
                    },
                    cellRenderer: (params) => {
                        const value = params.value;
                        const hasComments = params.data[`${colId}_hasComment`];
                        return (
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: '100%' }}>
                                <span>{value !== undefined && value !== null ? value.toLocaleString('es-AR') : ''}</span>
                                {hasComments && <span title="Esta celda tiene comentarios" style={{ marginLeft: '5px', cursor: 'pointer' }}>💬</span>}
                            </div>
                        );
                    },
                    cellRendererParams: {
                        keyFigureId: keyFigure ? keyFigure.key_figure_id : null,
                        keyFigureName: kfName,
                        period: periodDate,
                    }
                };
            });

        // Solo crear el grupo de columnas si tiene hijos (es decir, alguna figura clave se mostrará para ese mes)
        if (children.length > 0) {
            return {
                headerName: headerPeriodName,
                groupId: periodIso,
                children: children,
                marryChildren: true,
            };
        }
        return null; // No devolver el grupo si no tiene hijos
    }).filter(group => group !== null); // Filtrar grupos nulos


    const finalColumnDefs = [...initialColumnDefs, ...dynamicPeriodColumns];

    return { processedRowData, dynamicColumnDefs: finalColumnDefs };

  }, [historyData, forecastStatData, cleanHistoryData, finalForecastData, keyFigures, commentsForSelectedCell, forecastStartDate]);


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
        return newSelection; 
    });
  }, []);

  // --- EFECTOS (useEffect va DESPUÉS de todas las declaraciones de estados y callbacks/memo) ---
  // useEffect para cargar dimensiones iniciales (clientes, keyFigures, adjustmentTypes)
  useEffect(() => {
    const loadDimensions = async () => {
      try {
        const [clientsData, keyFiguresData, adjustmentTypesData] = await Promise.all([
          fetchClients(),
          fetchKeyFigures(),
          fetchAdjustmentTypes(),
        ]);
        setClients(clientsData);
        setKeyFigures(keyFiguresData);
        setAdjustmentTypes(adjustmentTypesData);
      } catch (e) {
        console.error("Error loading dimensions:", e);
        setErrorData("Error al cargar dimensiones para filtros: " + e.message);
      }
    };
    loadDimensions();
  }, []);

  // useEffect para filtrar SKUs CUANDO CAMBIA EL CLIENTE
  useEffect(() => {
    const loadSkus = async () => {
      try {
        let skusData;
        if (selectedClient) {
          skusData = await fetchSkus(selectedClient);
        } else {
          skusData = await fetchSkus();
        }
        setSkus(skusData);
      } catch (e) {
        console.error("Error al cargar SKUs:", e);
        setErrorData("Error al cargar SKUs: " + e.message);
      }
    };
    loadSkus();
  }, [selectedClient]);

  // --- Renderizado Principal del Componente ---
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
        cleanHistoryData={cleanHistoryData}
        finalForecastData={finalForecastData}
        keyFigures={keyFigures}
        selectedKeyFigures={selectedKeyFigures}
        selectedSources={selectedSources}
        forecastStartDate={forecastStartDate}
      />


      {/* --- TABLA AG GRID (Ahora renderizada por el componente auxiliar) --- */}
      <h3 style={{ marginTop: '30px' }}>Datos de Detalle (AG Grid)</h3>
      <DataTableRenderer
        loading={loadingData}
        error={errorData}
        rowData={processedRowData}
        columnDefs={dynamicColumnDefs}
        onGridReady={onGridReady}
        onCellValueChanged={onCellValueChanged}
        defaultColDef={useMemo(() => ({
          flex: 1,
          minWidth: 100,
          resizable: true,
          filter: true,
          sortable: true,
        }), [])}
        gridRef={gridRef}
        getContextMenuItems={getContextMenuItems}
      />

      {/* Modal de Comentarios */}
      <CommentModal
        isOpen={isCommentModalOpen}
        onClose={closeCommentModal}
        cellData={selectedCellForComment}
        comments={commentsForSelectedCell}
        onSaveComment={handleSaveComment}
      />

    </section>
  );
}

export default SalesForecastData;