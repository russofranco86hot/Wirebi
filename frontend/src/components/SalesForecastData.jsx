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
  // ESTADOS
  const [historyData, setHistoryData] = useState([]);
  const [forecastVersionedData, setForecastVersionedData] = useState([]);
  const [forecastStatData, setForecastStatData] = useState([]);
  const [cleanHistoryData, setCleanHistoryData] = useState([]); // Nuevo estado
  const [finalForecastData, setFinalForecastData] = useState([]); // Nuevo estado
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
  const [selectedSources, setSelectedSources] = useState([]); // Cambiado a [] por defecto

  const [forecastAlpha, setForecastAlpha] = useState(0.5);
  const [forecastModel, setForecastModel] = useState("ETS");
  const [forecastHorizon, setForecastHorizon] = useState(12);
  const [generatingForecast, setGeneratingForecast] = useState(false);
  const [forecastGenerationError, setForecastGenerationError] = useState(null);
  const [forecastGenerationMessage, setForecastGenerationMessage] = useState(null);

  const [isCommentModalOpen, setIsCommentModalOpen] = useState(false); // Estado para el modal de comentarios
  const [selectedCellForComment, setSelectedCellForComment] = useState(null); // Datos de la celda seleccionada
  const [commentsForSelectedCell, setCommentsForSelectedCell] = useState([]); // Comentarios para la celda

  // REFS
  const gridRef = useRef();

  // Column Definitions para AG Grid
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
      editable: params => params.data.keyFigureName === 'Pronóstico Estadístico' || params.data.keyFigureName === 'Pronóstico Final', // Ahora también editable el Pronóstico Final
      valueParser: params => Number(params.newValue),
      cellClassRules: {
        'rag-red': params => params.value < 0,
        // Clase para indicar que hay comentarios
        'has-comments': params => params.data.hasComments,
      },
      // Cell Renderer para mostrar un icono si tiene comentarios
      cellRenderer: (params) => {
        const value = params.value;
        const hasComments = params.data.hasComments;
        return (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: '100%' }}>
            <span>{value !== undefined && value !== null ? value.toLocaleString('es-AR') : ''}</span>
            {hasComments && <span title="Esta celda tiene comentarios" style={{ marginLeft: '5px', cursor: 'pointer' }}>💬</span>}
          </div>
        );
      }
    },
    { headerName: 'Modelo', field: 'modelUsed', minWidth: 100, filter: true, sortable: true },
    { headerName: 'Run ID', field: 'forecastRunId', minWidth: 100, filter: true, sortable: true, valueFormatter: params => params.value ? String(params.value).substring(0, 8) + '...' : '' },
  ]);

  // Callbacks para AG Grid: Lógica de edición
  const isCellEditable = useCallback(params => {
    return params.colDef.field === 'value' && (params.data.keyFigureName === 'Pronóstico Estadístico' || params.data.keyFigureName === 'Pronóstico Final');
  }, []);

  const onCellValueChanged = useCallback(async event => {
    console.log('Cell value changed:', event.data, 'New Value:', event.newValue, 'Old Value:', event.oldValue);

    if (event.newValue === event.oldValue) {
      return;
    }

    const { clientId, skuId, clientFinalId, period, keyFigureId, keyFigureName } = event.data;
    const newValue = Number(event.newValue);

    let adjustmentTypeId;
    // Determinar el tipo de ajuste según la figura clave
    if (keyFigureName === 'Pronóstico Estadístico' || keyFigureName === 'Pronóstico Final') {
      const overrideAdjType = adjustmentTypes.find(type => type.name === 'Override');
      if (!overrideAdjType) {
        console.error("Tipo de ajuste 'Override' no encontrado. No se puede guardar el ajuste.");
        return;
      }
      adjustmentTypeId = overrideAdjType.adjustment_type_id;
    } else {
      console.error("Solo 'Pronóstico Estadístico' y 'Pronóstico Final' son editables para ajustes directos.");
      return;
    }

    try {
      const adjustmentPayload = {
        client_id: clientId,
        sku_id: skuId,
        client_final_id: clientFinalId,
        period: period,
        key_figure_id: keyFigureId,
        adjustment_type_id: adjustmentTypeId,
        value: newValue,
        comment: `Ajuste manual de ${event.oldValue} a ${event.newValue} para ${keyFigureName}`,
        user_id: "00000000-0000-0000-0000-000000000001"
      };

      await sendManualAdjustment(adjustmentPayload);
      console.log("Ajuste guardado exitosamente!");

      // Para actualizar el chart y la tabla, recargamos los datos relevantes
      // Si el ajuste es al 'Pronóstico Estadístico' o 'Pronóstico Final', actualizamos los estados correspondientes
      if (keyFigureName === 'Pronóstico Estadístico') {
        setForecastStatData(prevData => {
          return prevData.map(item => {
            if (item.client_id === clientId && item.sku_id === skuId && item.period === period) {
              return { ...item, value: newValue };
            }
            return item;
          });
        });
      } else if (keyFigureName === 'Pronóstico Final') {
        // Al editar Pronóstico Final, solo se actualiza localmente si se refleja en el gráfico
        // y se pasa al backend. No se necesita actualizar forecastStatData.
        setFinalForecastData(prevData => {
          return prevData.map(item => {
            if (item.client_id === clientId && item.sku_id === skuId && item.period === period) {
              return { ...item, value: newValue };
            }
            return item;
          });
        });
      }

      // Opcionalmente, puedes volver a llamar handleSearch para recargar TODOS los datos
      // y asegurarte de que Historia Limpia y Pronóstico Final se recalculen en el backend
      // y se reflejen en el frontend, pero para una respuesta más rápida del UI
      // se prioriza la actualización local de los estados directos.
      // handleSearch(); // Descomentar si la recarga completa es preferible después de cada ajuste

    } catch (e) {
      console.error("Error al guardar el ajuste manual:", e);
      // Podrías mostrar un mensaje de error más amigable aquí
    }
  }, [adjustmentTypes]);


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
        startPeriod: cellData.period,
        endPeriod: cellData.period,
        keyFigureIds: [cellData.keyFigureId],
      });
      setCommentsForSelectedCell(fetchedComments);
    } catch (error) {
      console.error("Error fetching comments:", error);
      setCommentsForSelectedCell([]); // Clear comments on error
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
      period: cellData.period,
      key_figure_id: cellData.keyFigureId,
      comment: commentText,
      user_id: "00000000-0000-0000-0000-000000000001", // ID de usuario por defecto
    };

    try {
      await sendComment(commentPayload);
      console.log("Comentario guardado exitosamente!");
      // Actualizar los comentarios para la celda seleccionada inmediatamente
      // Esto simula una recarga sin necesidad de cerrar y abrir el modal
      const updatedComments = await fetchComments({
        clientIds: [cellData.clientId],
        skuIds: [cellData.skuId],
        startPeriod: cellData.period,
        endPeriod: cellData.period,
        keyFigureIds: [cellData.keyFigureId],
      });
      setCommentsForSelectedCell(updatedComments);
      // Actualizar el estado de la celda para mostrar el icono de comentario
      if (gridRef.current && gridRef.current.api) {
        const rowNode = gridRef.current.api.getRowNode(cellData.id);
        if (rowNode) {
          rowNode.setData({ ...rowNode.data, hasComments: true });
        }
      }

    } catch (e) {
      console.error("Error al guardar el comentario:", e);
    }
  }, [gridRef]);


  // --- Menú Contextual (Clic Derecho) de AG Grid ---
  const getContextMenuItems = useCallback((params) => {
    const defaultItems = params.defaultItems.filter(item => item !== 'copyWithHeaders' && item !== 'paste'); // Remover opciones por defecto que no queremos
    const cellData = params.node?.data;

    if (!cellData) return defaultItems; // Si no hay datos de celda, solo mostrar elementos por defecto

    return [
      ...defaultItems,
      'separator',
      {
        name: 'Agregar un comentario',
        action: () => {
          openCommentModal(cellData);
        },
        icon: '<span class="ag-icon ag-icon-comments"></span>', // Puedes usar un icono de AG Grid o uno personalizado
      },
      {
        name: 'Ver historial de comentarios anteriores',
        action: () => {
          openCommentModal(cellData);
        },
        icon: '<span class="ag-icon ag-icon-clipboard"></span>', // Icono genérico para historial
      },
    ];
  }, [openCommentModal]);


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

    // Mapeo para rastrear si una combinación Cliente-SKU-Período-FiguraClave tiene comentarios
    const commentsPresence = {};
    commentsForSelectedCell.forEach(comment => {
      const periodString = new Date(comment.period).toISOString().split('T')[0];
      const id = `${comment.client_id}-${comment.sku_id}-${periodString}-${comment.key_figure_id}`;
      commentsPresence[id] = true;
    });

    // Función auxiliar para añadir elementos y marcar si tienen comentarios
    const addDataItem = (item, keyFigureName, source, modelUsed, forecastRunId, dataType, keyFigureId) => {
      const periodString = new Date(item.period).toISOString().split('T')[0]; // Formatear para el ID
      const id = `${item.client_id}-${item.sku_id}-${periodString}-${keyFigureId || item.key_figure_id}`; // Usar KFId pasado o del item
      combined.push({
        id: id,
        clientName: item.clientName || item.client?.client_name || 'N/A',
        skuName: item.skuName || item.sku?.sku_name || 'N/A',
        period: item.period,
        keyFigureName: keyFigureName,
        source: source,
        value: item.value,
        modelUsed: modelUsed,
        forecastRunId: forecastRunId,
        clientId: item.client_id,
        skuId: item.sku_id,
        clientFinalId: item.client_final_id,
        keyFigureId: keyFigureId,
        dataType: dataType,
        hasComments: commentsPresence[id] || false, // Añadir la bandera de comentarios
      });
    };

    historyData.forEach(item => {
      addDataItem(item, item.key_figure?.name || 'N/A', item.source, 'Historia', 'N/A', 'history', item.key_figure_id);
    });

    forecastStatData.forEach(item => {
      addDataItem(item, 'Pronóstico Estadístico', 'Forecast', item.model_used, item.forecast_run_id, 'forecast_stat', 4);
    });

    cleanHistoryData.forEach(item => { // Añadir Historia Limpia
      addDataItem(item, 'Historia Limpia', 'Calculado', 'N/A', 'N/A', 'clean_history', 5);
    });

    finalForecastData.forEach(item => { // Añadir Pronóstico Final
      addDataItem(item, 'Pronóstico Final', 'Calculado', 'N/A', 'N/A', 'final_forecast', 6);
    });


    return combined.sort((a, b) => {
      if (a.clientName !== b.clientName) return a.clientName.localeCompare(b.clientName);
      if (a.skuName !== b.skuName) return a.skuName.localeCompare(b.skuName);
      if (a.period !== b.period) return new Date(a.period) - new Date(b.period);
      // Ordenar para que Historia siempre esté primero, luego Historia Limpia, luego Pronóstico Estadístico, luego Pronóstico Final
      const order = { 'Historia': 1, 'Historia Limpia': 2, 'Pronóstico Estadístico': 3, 'Pronóstico Final': 4 };
      return (order[a.keyFigureName] || 99) - (order[b.keyFigureName] || 99);
    });
  }, [historyData, forecastStatData, cleanHistoryData, finalForecastData, commentsForSelectedCell]);


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
        // CORREGIDO: Devolver siempre un array, vacío si no hay selecciones
        return newSelection; 
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
        // Para la historia limpia y pronóstico final, necesitamos un solo client/sku/client_final
        clientId: selectedClient || null,
        skuId: selectedSku || null,
        // Esto es un placeholder. En un sistema real, clientFinalId debe obtenerse o ser un campo de filtro.
        // Aquí asumimos que si selectedClient está, podemos usarlo como clientFinalId
        clientFinalId: selectedClient || '00000000-0000-0000-0000-000000000001', // Asumimos un default o el mismo client_id
      };

      const [historical, versioned, forecastStat, cleanHistory, finalForecast] = await Promise.all([
        fetchHistoricalData(filterParams),
        fetchForecastVersionedData(filterParams),
        fetchForecastStatData({
            clientIds: filterParams.clientIds,
            skuIds: filterParams.skuIds,
            startPeriod: filterParams.startPeriod,
            endPeriod: filterParams.endPeriod,
        }),
        // Nuevas llamadas para Historia Limpia y Pronóstico Final
        selectedClient && selectedSku && startDate && endDate ? fetchCleanHistoryData(filterParams) : Promise.resolve([]),
        selectedClient && selectedSku && startDate && endDate ? fetchFinalForecastData(filterParams) : Promise.resolve([]),
      ]);

      setHistoryData(historical);
      setForecastVersionedData(versioned);
      setForecastStatData(forecastStat);
      setCleanHistoryData(cleanHistory); // Actualizar estado de Historia Limpia
      setFinalForecastData(finalForecast); // Actualizar estado de Pronóstico Final

      // También cargar todos los comentarios para el rango actual de datos
      const allComments = await fetchComments({
        clientIds: filterParams.clientIds,
        skuIds: filterParams.skuIds,
        startPeriod: filterParams.startPeriod,
        endPeriod: filterParams.endPeriod,
        // No filtramos por KeyFigureId aquí para obtener todos los comentarios
      });
      // Mapear la presencia de comentarios para la visualización en la tabla
      const commentsMap = {};
      allComments.forEach(comment => {
        const periodString = new Date(comment.period).toISOString().split('T')[0];
        const id = `${comment.client_id}-${comment.sku_id}-${periodString}-${comment.key_figure_id}`;
        commentsMap[id] = true;
      });
      // Aplicar 'hasComments' a rowData de forma reactiva a través de un nuevo estado si es necesario,
      // o directamente en la construcción de rowData. Por ahora, se maneja en rowData useMemo.

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

    // --- DEBUGGING LOG - Check raw state values ---
    console.log("DEBUG: selectedClient:", selectedClient);
    console.log("DEBUG: selectedSku:", selectedSku);
    console.log("DEBUG: selectedSources:", selectedSources);
    // --- END DEBUGGING LOG ---

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
        setForecastGenerationError("La fuente del historial seleccionada no es válida. Por favor, elige 'Sales', 'Order' o 'Shipments'.");
        setGeneratingForecast(false);
        return;
    }
    
    // Convertir a float/int de forma segura
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
        await handleSearch(); // Recargar datos para ver el nuevo pronóstico y las figuras calculadas
    }
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
          fetchAdjustmentTypes(),
        ]);
        setClients(clientsData);
        setSkus(skusData);
        setKeyFigures(keyFiguresData);
        setAdjustmentTypes(adjustmentTypesData);
      } catch (e) {
        console.error("Error loading dimensions:", e);
        setErrorData("Error al cargar dimensiones para filtros: " + e.message);
      }
    };
    loadDimensions();
  }, []);

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
        cleanHistoryData={cleanHistoryData} // Pasar nueva data
        finalForecastData={finalForecastData} // Pasar nueva data
        keyFigures={keyFigures}
        selectedKeyFigures={selectedKeyFigures}
        selectedSources={selectedSources}
      />


      {/* --- TABLA AG GRID (Ahora renderizada por el componente auxiliar) --- */}
      <h3 style={{ marginTop: '30px' }}>Datos de Detalle (AG Grid)</h3>
      <DataTableRenderer
        loading={loadingData}
        error={errorData}
        rowData={rowData}
        columnDefs={memoizedColumnDefs}
        onGridReady={onGridReady}
        onCellValueChanged={onCellValueChanged}
        defaultColDef={useMemo(() => ({
          flex: 1,
          minWidth: 100,
          resizable: true,
        }), [])}
        gridRef={gridRef}
        getContextMenuItems={getContextMenuItems} // Pasar la función del menú contextual
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