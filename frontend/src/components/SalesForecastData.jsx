// frontend/src/components/SalesForecastData.jsx

import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import {
    fetchClients, fetchSkus, fetchKeyFigures,
    salesForecastApi, updateAdjustment, generateStatisticalForecast,
    saveComment, fetchComments, fetchAdjustmentTypes,
    saveForecastVersion, fetchForecastVersions, fetchVersionedForecastData
} from '../api'; 

import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

import SalesChart from './SalesChart';
import dayjs from 'dayjs'; 
import { v4 as uuidv4 } from 'uuid'; 

// Material-UI Imports
import {
    Button, TextField, MenuItem, Select, InputLabel, FormControl,
    CircularProgress, Box, Typography, Dialog, DialogActions,
    DialogContent, DialogContentText, DialogTitle, Alert
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';


// Constantes para IDs de Key Figures (¡AHORA DEFINITIVAS Y CANÓNICAS!)
// Asignadas de 1 a 8, como en la lista maestra.
const KEY_FIGURE_SALES_ID = 1;
const KEY_FIGURE_SMOOTHED_SALES_ID = 2;
const KEY_FIGURE_ORDERS_ID = 3;
const KEY_FIGURE_SMOOTHED_ORDERS_ID = 4;
const KEY_FIGURE_MANUAL_INPUT_ID = 5; // Esta es la editable histórica
const KEY_FIGURE_STAT_FORECAST_SALES_ID = 6;
const KEY_FIGURE_STAT_FORECAST_ORDERS_ID = 7;
const KEY_FIGURE_FINAL_FORECAST_ID = 8; // Esta es la editable de pronóstico

// Constantes para Adjustment Types (debe coincidir con los IDs de tu base de datos)
const ADJUSTMENT_TYPE_QTY_ID = 1; 
const ADJUSTMENT_TYPE_PCT_ID = 2; 
const ADJUSTMENT_TYPE_OVERRIDE_ID = 3; 

// Mapeo de nombres de Key Figures a sus IDs (usado en frontend)
const keyFigureMap = {
    'Sales': KEY_FIGURE_SALES_ID,
    'Smoothed Sales': KEY_FIGURE_SMOOTHED_SALES_ID,
    'Orders': KEY_FIGURE_ORDERS_ID,
    'Smoothed Orders': KEY_FIGURE_SMOOTHED_ORDERS_ID,
    'Manual input': KEY_FIGURE_MANUAL_INPUT_ID,
    'Statistical forecast Sales': KEY_FIGURE_STAT_FORECAST_SALES_ID, 
    'Statistical forecast Orders': KEY_FIGURE_STAT_FORECAST_ORDERS_ID,
    'Final Forecast': KEY_FIGURE_FINAL_FORECAST_ID, 
};



function SalesForecastData({ clientFinalId: propClientFinalId }) { 
    // --- TODAS LAS DECLARACIONES DE ESTADOS Y HOOKS DEBEN IR AQUÍ AL PRINCIPIO ---
    const gridRef = useRef(null);

    // ESTADOS DE SELECCIÓN DE CLIENTE/SKU Y FILTROS
    const [selectedClientId, setSelectedClientId] = useState(''); 
    const [selectedSkuId, setSelectedSkuId] = useState('');     
    const clientFinalId = selectedClientId; 


    // ESTADOS DE DATOS Y CARGA
    const [rowData, setRowData] = useState([]);
    const [columnDefs, setColumnDefs] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [chartData, setChartData] = useState([]);

    // ESTADOS DE DIMENSIONES (Cargados una vez)
    const [clients, setClients] = useState([]);
    const [skus, setSkus] = useState([]);
    const [keyFigures, setKeyFigures] = useState([]);
    const [adjustmentTypes, setAdjustmentTypes] = useState([]);

    // ESTADOS DE RANGO DE FECHAS
    const [startDate, setStartDate] = useState(dayjs('2023-01-01'));
    const [endDate, setEndDate] = useState(dayjs('2024-12-31'));

    // ESTADOS DE FILTROS DE DATOS (para la tabla, no para generar pronóstico)
    const [selectedKeyFigures, setSelectedKeyFigures] = useState([]); 
    const [selectedSources, setSelectedSources] = useState(['sales']); 

    // ESTADOS DE GENERACIÓN DE PRONÓSTICO
    const [historySource, setHistorySource] = useState('sales'); 
    const [smoothingAlpha, setSmoothingAlpha] = useState(0.5);
    const [modelName, setModelName] = useState('ETS');
    const [forecastHorizon, setForecastHorizon] = useState(12); 

    // ESTADOS DE COMENTARIOS
    const [openCommentModal, setOpenCommentModal] = useState(false);
    const [activeRow, setActiveRow] = useState(null);
    const [activeCol, setActiveCol] = useState(null);
    const [commentText, setNewCommentText] = useState(''); 
    const [commentsForSelectedCell, setCommentsForSelectedCell] = useState([]); 

    // ESTADOS DE GESTIÓN DE VERSIONES (SNAPSHOTS)
    const [openSaveVersionModal, setOpenSaveVersionModal] = useState(false);
    const [versionName, setVersionName] = useState('');
    const [versionNotes, setVersionNotes] = useState('');
    const [isSavingVersion, setIsSavingVersion] = useState(false);
    const [saveVersionError, setSaveVersionError] = useState(null);
    const [saveVersionSuccess, setSaveVersionSuccess] = useState(false);
    const [versionsList, setVersionsList] = useState([]); 
    const [selectedVersionId, setSelectedVersionId] = useState(''); 


    // ID de usuario placeholder (reemplazar con autenticación real)
    const currentUserId = '00000000-0000-0000-0000-000000000001';

    // --- Funciones para manejar datos y lógica ---

    const fetchSalesData = useCallback(async () => {
        if (!selectedClientId || !selectedSkuId || !clientFinalId) {
            console.warn("fetchSalesData: Client, SKU, or Client Final ID not selected. Skipping data fetch.");
            setRowData([]);
            setColumnDefs([]);
            setChartData([]);
            return;
        }

        setLoading(true);
        setError(null);
        try {
            const data = await salesForecastApi( // LLAMADA A LA API REAL
                selectedClientId,
                selectedSkuId,
                clientFinalId, 
                startDate.format('YYYY-MM-DD'),
                endDate.format('YYYY-MM-DD')
            );
            
            if (data && data.rows && data.columns) {
                setRowData(data.rows);
                console.log("DEBUG: Datos (data.rows) recibidos del backend:", data.rows); // Log de rows

                // --- INICIO: Lógica de procesamiento de Columnas del Backend ---
                console.log("DEBUG: data.columns recibidos del backend (original):", data.columns); // Log de columns originales

                const processColumnsForFrontend = (cols) => {
                    if (!cols || !Array.isArray(cols)) return [];
                    return cols.map(colDef => {
                        if (colDef.children) {
                            return {
                                ...colDef,
                                children: processColumnsForFrontend(colDef.children)
                            };
                        } else {
                            const isMonthColumn = colDef.field && colDef.field.startsWith('date_');
                            return {
                                ...colDef,
                               // editable: isMonthColumn, // Solo los meses son editables
                                valueFormatter: (params) => { 
                                    if (typeof params.value === 'number') {
                                        return params.value.toLocaleString(undefined, { maximumFractionDigits: 2 });
                                    }
                                    return params.value;
                                },
                                valueParser: (params) => Number(params.newValue),
                                cellRenderer: (params) => {
                                    const cellValue = params.value !== undefined && params.value !== null ? params.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '';
                                    const hasComments = params.data && params.colDef && params.data[`${params.colDef.colId}_hasComment`]; 
                                    return (
                                        <div
                                            onContextMenu={(e) => handleCellContextMenu(e, params)}
                                            style={{
                                                height: '100%',
                                                width: '100%',
                                                display: 'flex',
                                                alignItems: 'center',
                                                paddingLeft: '5px',
                                                cursor: 'context-menu'
                                            }}
                                        >
                                            <span>{cellValue}</span>
                                            {hasComments && <span title="Esta celda tiene comentarios" style={{ marginLeft: '5px', cursor: 'pointer' }}>💬</span>}
                                        </div>
                                    );
                                },
                                cellClassRules: {
                                    ...(colDef.cellClassRules || {}), 
                                    'has-comments-icon': (params) => params.data && params.colDef && params.data[`${colDef.colId}_hasComment`],
                                    'rag-red': params => typeof params.value === 'number' && params.value < 0, 
                                }
                            };
                        }
                    });
                };

                const processedDynamicColumns = processColumnsForFrontend(data.columns);
                console.log("DEBUG: processedDynamicColumns (después de processColumnsForFrontend):", processedDynamicColumns); // Log de columnas procesadas

                setColumnDefs(processedDynamicColumns);

                // Aquí, el estado `columnDefs` en el próximo render será el correcto.
                // Para el log inmediato, usamos la variable `finalColumnDefs`.
                console.log("DEBUG: columnDefs FINALES para AG-Grid (lista completa):", processedDynamicColumns); 

                updateChartData(data.rows, processedDynamicColumns);

            } else {
                setRowData([]);
                setColumnDefs([]);
                setChartData([]);
                setError('No se encontraron datos para los filtros seleccionados.');
            }
        } catch (err) {
            setError(err.message);
            setRowData([]);
            setColumnDefs([]);
            setChartData([]);
        } finally {
            setLoading(false);
        }
    }, [selectedClientId, selectedSkuId, clientFinalId, startDate, endDate, salesForecastApi]); 


    useEffect(() => {
        if (selectedClientId && selectedSkuId) {
            fetchSalesData();
        }
    }, [selectedClientId, selectedSkuId, fetchSalesData]); 


    const updateChartData = (rows, columns) => {
        // ACTUALIZADO: Usar los nuevos nombres de Key Figure
        const salesRow = rows.find(row => row.keyFigureName === 'Sales');
        const smoothedSalesRow = rows.find(row => row.keyFigureName === 'Smoothed Sales');
        const ordersRow = rows.find(row => row.keyFigureName === 'Orders');
        const smoothedOrdersRow = rows.find(row => row.keyFigureName === 'Smoothed Orders');
        const manualInputRow = rows.find(row => row.keyFigureName === 'Manual input');
        const statForecastSalesRow = rows.find(row => row.keyFigureName === 'Statistical forecast Sales');
        const statForecastOrdersRow = rows.find(row => row.keyFigureName === 'Statistical forecast Orders');
        const finalForecastRow = rows.find(row => row.keyFigureName === 'Final Forecast');

        console.log("DEBUG: Fila de 'Final Forecast' para el gráfico:", finalForecastRow);


        const allPeriods = columns
        .filter(col => col.field && col.field.startsWith('date_'))
        .map(col => col.field.replace('date_', ''))
        .sort();

        const allDatesInOrder = allPeriods.map(p => dayjs(p).toDate());

        const getTraceData = (keyFigureRow) => {
            if (!keyFigureRow) return { x: allDatesInOrder, y: allDatesInOrder.map(() => null) }; 
            
            const yValues = allDatesInOrder.map(date => {
                const dateIso = dayjs(date).format('YYYY-MM-DD');
                const fieldName = `date_${dateIso}`;
                const value = typeof keyFigureRow[fieldName] === 'number' ? keyFigureRow[fieldName] : null;
                return value;
            });
            return { x: allDatesInOrder, y: yValues };
        };

        // ACTUALIZADO: Trazas del gráfico con los nuevos nombres
        setChartData([
            { x: getTraceData(salesRow).x, y: getTraceData(salesRow).y, name: 'Sales', type: 'scatter', mode: 'lines+markers', marker: { color: 'green' } },
            { x: getTraceData(smoothedSalesRow).x, y: getTraceData(smoothedSalesRow).y, name: 'Smoothed Sales', type: 'scatter', mode: 'lines+markers', marker: { color: 'lightgreen' } },
            { x: getTraceData(ordersRow).x, y: getTraceData(ordersRow).y, name: 'Orders', type: 'scatter', mode: 'lines+markers', marker: { color: 'blue' } },
            { x: getTraceData(smoothedOrdersRow).x, y: getTraceData(smoothedOrdersRow).y, name: 'Smoothed Orders', type: 'scatter', mode: 'lines+markers', marker: { color: 'lightblue' } },
            { x: getTraceData(manualInputRow).x, y: getTraceData(manualInputRow).y, name: 'Manual input', type: 'scatter', mode: 'lines+markers', marker: { color: 'purple' } },
            { x: getTraceData(statForecastSalesRow).x, y: getTraceData(statForecastSalesRow).y, name: 'Statistical forecast Sales', type: 'scatter', mode: 'lines+markers', marker: { color: 'orange' } },
            { x: getTraceData(statForecastOrdersRow).x, y: getTraceData(statForecastOrdersRow).y, name: 'Statistical forecast Orders', type: 'scatter', mode: 'lines+markers', marker: { color: 'darkorange' } },
            { x: getTraceData(finalForecastRow).x, y: getTraceData(finalForecastRow).y, name: 'Final Forecast', type: 'scatter', mode: 'lines+markers', marker: { color: 'red' } }
        ]);
    };

    const handleCellValueChanged = useCallback(async (event) => {
        const { data, colDef, newValue, oldValue } = event;
        const keyFigureName = data.keyFigureName; 
        
        const colIdParts = colDef.colId ? colDef.colId.split('_') : [];
        const periodString = colIdParts.length > 1 ? colIdParts[1] : null;

        const period = dayjs(periodString).toDate(); 
        if (!periodString) {
             console.warn("handleCellValueChanged: Period string not found in colId.");
             event.node.setDataValue(colDef.field, oldValue); 
             return;
        }
        
        if (newValue === oldValue) return;

        console.log("DEBUG: handleCellValueChanged: keyFigureName siendo procesado (desde data.keyFigureName):", keyFigureName);
        console.log("DEBUG: handleCellValueChanged: Contenido actual de keyFigureMap:", keyFigureMap);


        const keyFigureId = keyFigureMap[keyFigureName];
        if (!keyFigureId) {
            console.warn(`Figura clave '${keyFigureName}' no encontrada en el mapeo. No se puede guardar el ajuste.`);
            console.warn("DEBUG: data.keyFigureName original de la fila (si diferente):", data.keyFigureName);
            event.node.setDataValue(colDef.field, oldValue); 
            return;
        }

        let adjustmentTypeId;
        // ACTUALIZADO: Lógica de tipos de ajuste con los nuevos IDs
        if (keyFigureId === KEY_FIGURE_MANUAL_INPUT_ID) { // 'Manual input' es editable
            adjustmentTypeId = ADJUSTMENT_TYPE_OVERRIDE_ID; // Se asume que editar 'Manual input' es un override directo
        } else if (keyFigureId === KEY_FIGURE_FINAL_FORECAST_ID) { // 'Final Forecast' es editable
            adjustmentTypeId = ADJUSTMENT_TYPE_OVERRIDE_ID; // Editar 'Final Forecast' es un override
        } else if (keyFigureId === KEY_FIGURE_STAT_FORECAST_SALES_ID || keyFigureId === KEY_FIGURE_STAT_FORECAST_ORDERS_ID) {
            adjustmentTypeId = ADJUSTMENT_TYPE_OVERRIDE_ID; // Editar stat forecast también es un override
        } else {
            console.warn(`Edición no permitida para la figura clave: ${keyFigureName}`);
            event.node.setDataValue(colDef.field, oldValue); 
            return;
        }

        const adjustmentData = {
            client_id: selectedClientId,
            sku_id: selectedSkuId,
            client_final_id: clientFinalId, 
            period: dayjs(period).format('YYYY-MM-DD'),
            key_figure_id: keyFigureId,
            adjustment_type_id: adjustmentTypeId,
            value: parseFloat(newValue),
            user_id: currentUserId
        };

        try {
            await updateAdjustment(adjustmentData);
            console.log("Ajuste guardado exitosamente!");
            fetchSalesData(); 
        } catch (err) {
            setError(err.message);
            event.node.setDataValue(colDef.field, oldValue);
        }
    }, [selectedClientId, selectedSkuId, clientFinalId, fetchSalesData, keyFigureMap]);


    const handleGenerateForecast = useCallback(async () => {
        if (!selectedClientId || !selectedSkuId) {
            setError('Por favor, selecciona un Cliente y un SKU antes de generar el pronóstico.');
            return;
        }
        setLoading(true);
        setError(null);
        try {
            // ACTUALIZADO: historySource de la UI ahora mapea a la KF_ID correcta
            let forecastHistoryKfId = null;
            if (historySource === 'sales') {
                forecastHistoryKfId = KEY_FIGURE_SALES_ID;
            } else if (historySource === 'order' || historySource === 'shipments') {
                forecastHistoryKfId = KEY_FIGURE_ORDERS_ID;
            }

            if (!forecastHistoryKfId) {
                setError('Fuente de historia no válida para generar pronóstico.');
                setLoading(false);
                return;
            }


            const result = await generateStatisticalForecast(
                selectedClientId,
                selectedSkuId,
                historySource, // Pasar la fuente original para que el backend determine el KF_ID
                smoothingAlpha,
                modelName,
                forecastHorizon
            );
            console.log("Pronóstico generado:", result);

            const latestHistoricalPeriod = dayjs(startDate).add(forecastHorizon, 'month'); 
            setEndDate(latestHistoricalPeriod); 

            fetchSalesData(); 
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [selectedClientId, selectedSkuId, historySource, smoothingAlpha, modelName, forecastHorizon, startDate, fetchSalesData]);


    const handleCellContextMenu = useCallback((event, params) => {
        event.preventDefault(); 
        setActiveRow(params.data);
        setActiveCol(params.colDef);
        
        const keyFigureName = params.data.keyFigureName; 
        const colIdParts = params.colDef.colId ? params.colDef.colId.split('_') : [];
        const periodString = colIdParts.length > 1 ? colIdParts[1] : null;
        
        const period = dayjs(periodString).toDate();
        const keyFigureId = keyFigureMap[keyFigureName];

        if (!period || !keyFigureId) {
            console.warn("handleCellContextMenu: No se pudo determinar período o ID de figura clave.");
            return;
        }

        const cellDataForComment = {
            clientId: params.data.client_id,
            skuId: params.data.sku_id,
            clientFinalId: params.data.client_final_id,
            period: period,
            keyFigureName: keyFigureName,
            keyFigureId: keyFigureId,
        };
        
        fetchComments(
            cellDataForComment.clientId,
            cellDataForComment.skuId,
            cellDataForComment.clientFinalId, 
            dayjs(cellDataForComment.period).format('YYYY-MM-DD'),
            cellDataForComment.keyFigureId
        )
        .then(comments => {
            setCommentsForSelectedCell(comments); // Actualizado para usar el nuevo nombre de estado
            setNewCommentText(''); 
            setOpenCommentModal(true);
        })
        .catch(err => {
            console.error('Error fetching comments:', err);
            setCommentsForSelectedCell([]); // Actualizado
            setOpenCommentModal(true); 
        });
    }, [selectedClientId, selectedSkuId, clientFinalId, keyFigureMap]); 


    const handleCloseCommentModal = useCallback(() => {
        setOpenCommentModal(false);
        setNewCommentText('');
        setCommentsForSelectedCell([]);
        setActiveRow(null);
        setActiveCol(null);
    }, []);

    const handleSaveComment = useCallback(async () => {
        if (!commentText.trim() || !activeRow || !activeCol) {
            alert('El comentario no puede estar vacío.');
            return;
        }

        const keyFigureName = activeRow.keyFigureName; 
        const colIdParts = activeCol.colId ? activeCol.colId.split('_') : [];
        const periodString = colIdParts.length > 1 ? colIdParts[1] : null;

        const period = dayjs(periodString).format('YYYY-MM-DD');
        const keyFigureId = keyFigureMap[keyFigureName];

        if (!periodString || !keyFigureId) {
            console.warn("handleSaveComment: No se pudo determinar período o ID de figura clave.");
            return;
        }

        const commentData = {
            client_id: activeRow.client_id,
            sku_id: activeRow.sku_id,
            client_final_id: activeRow.client_final_id, 
            period: period,
            key_figure_id: keyFigureId,
            comment: newCommentText, // Usar newCommentText
            user_id: currentUserId
        };

        try {
            await saveComment(commentData);
            alert('Comentario guardado exitosamente.');
            fetchSalesData(); 
            handleCloseCommentModal(); 
        } catch (error) {
            alert(`Error al guardar el comentario: ${error.message}`);
        }
    }, [activeCol, activeRow, commentText, selectedClientId, selectedSkuId, clientFinalId, fetchSalesData, keyFigureMap]); 
    
    // --- MANEJADORES PARA EL MODAL DE GESTIÓN DE VERSIONES ---
    const handleOpenSaveVersionModal = useCallback(() => {
        setOpenSaveVersionModal(true);
        setVersionName(''); 
        setVersionNotes('');
        setSaveVersionError(null);
        setSaveVersionSuccess(false);
    }, []);

    const handleCloseSaveVersionModal = useCallback(() => {
        setOpenSaveVersionModal(false);
        setVersionName('');
        setVersionNotes('');
    }, []);

    const handleSaveVersion = useCallback(async () => {
        if (!versionName.trim()) {
            setSaveVersionError('El nombre de la versión no puede estar vacío.');
            return;
        }
        if (!selectedClientId) {
            setSaveVersionError('Debe seleccionar un cliente para guardar la versión.');
            return;
        }

        setIsSavingVersion(true);
        setSaveVersionError(null);
        setSaveVersionSuccess(false);

        const versionData = {
            client_id: selectedClientId,
            user_id: currentUserId, 
            version_name: versionName,
            history_source_used: historySource, 
            smoothing_parameter_used: smoothingAlpha, 
            statistical_model_applied: modelName, 
            notes: versionNotes
        };

        try {
            await saveForecastVersion(versionData);
            setSaveVersionSuccess(true);
            await fetchForecastVersions(selectedClientId).then(setVersionsList); 
            setTimeout(() => handleCloseSaveVersionModal(), 2000); 
        } catch (error) {
            setSaveVersionError(error.message || 'Error desconocido al guardar la versión.');
        } finally {
            setIsSavingVersion(false);
        }
    }, [selectedClientId, versionName, historySource, smoothingAlpha, modelName, versionNotes]);

    const handleLoadVersion = useCallback(async () => {
        if (!selectedVersionId || !selectedClientId || !selectedSkuId || !clientFinalId) { 
            setError("Por favor, selecciona una versión, cliente y SKU para cargar.");
            return;
        }
        setLoading(true);
        setError(null);
        try {
            const versionedData = await fetchVersionedForecastData(
                selectedVersionId,
                selectedClientId,
                selectedSkuId,
                clientFinalId, 
                startDate.format('YYYY-MM-DD'),
                endDate.format('YYYY-MM-DD')
            );
            
            console.log("Datos de la versión cargados:", versionedData);
            alert(`Versión ${selectedVersionId} cargada. Consulta la consola para los datos.`);

            
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [selectedVersionId, selectedClientId, selectedSkuId, clientFinalId, startDate, endDate]);

    // UseEffect para cargar las versiones al seleccionar un cliente
    useEffect(() => {
        const loadVersions = async () => {
            if (selectedClientId) {
                try {
                    const versions = await fetchForecastVersions(selectedClientId);
                    setVersionsList(versions);
                } catch (error) {
                    console.error("Error fetching versions:", error);
                    setVersionsList([]);
                }
            } else {
                setVersionsList([]);
            }
        };
        loadVersions();
    }, [selectedClientId]);


    // Definición de las columnas por defecto para Ag-Grid
    const defaultColDef = useMemo(() => ({
        flex: 1,
        minWidth: 100,
        resizable: true,
        sortable: true,
        filter: true,
        editable: (params) => {
            const keyFigureId = keyFigureMap[params.data.keyFigureName];
            return [
                KEY_FIGURE_MANUAL_INPUT_ID, // Manual input es editable
                KEY_FIGURE_FINAL_FORECAST_ID, // Final Forecast es editable
                KEY_FIGURE_STAT_FORECAST_SALES_ID, // Stat Forecast Sales es editable
                KEY_FIGURE_STAT_FORECAST_ORDERS_ID, // Stat Forecast Orders es editable
            ].includes(keyFigureId);
        },
    }), [keyFigureMap]); 


    // --- LÓGICA: Preparación de rowData pivotada y ColumnDefs dinámicas ---
    const { processedRowData, dynamicColumnDefs } = useMemo(() => {
        const finalProcessedRowData = rowData;
        const finalDynamicColumnDefs = columnDefs; 

        return { processedRowData: finalProcessedRowData, dynamicColumnDefs: finalDynamicColumnDefs };
    }, [rowData, columnDefs, commentsForSelectedCell]);


    // Efectos para cargar datos iniciales
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
                setError("Error al cargar dimensiones para filtros: " + e.message);
            }
        };
        loadDimensions();
    }, []);

    // Efecto para cargar SKUs cuando cambia el cliente seleccionado
    useEffect(() => {
        const loadSkus = async () => {
            try {
                if (selectedClientId) {
                    const skusData = await fetchSkus(selectedClientId);
                    setSkus(skusData);
                } else {
                    setSkus([]); 
                }
            } catch (e) {
                console.error("Error al cargar SKUs:", e);
                setError("Error al cargar SKUs: " + e.message);
            }
        };
        loadSkus();
    }, [selectedClientId]);

    // Renderizado Principal del Componente
    return (
        <LocalizationProvider dateAdapter={AdapterDayjs}>
            <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
                <Typography variant="h4" gutterBottom>
                    Datos de Demanda y Pronóstico
                </Typography>

                {/* Controles de Filtro */}
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 0, border: '1px solid #ccc', p: 2, borderRadius: '4px', bgcolor: 'background.paper' }}>
                    <Typography variant="h6" sx={{ width: '100%', mb: 1 }}>Filtros</Typography>
                    <FormControl sx={{ minWidth: 200 }}>
                        <InputLabel id="client-select-label">Cliente</InputLabel>
                        <Select
                            labelId="client-select-label"
                            value={selectedClientId}
                            label="Cliente"
                            onChange={e => setSelectedClientId(e.target.value)}
                        >
                            <MenuItem value=""><em>Seleccione Cliente</em></MenuItem>
                            {clients.map(client => (
                                <MenuItem key={client.client_id} value={client.client_id}>
                                    {client.client_name}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    <FormControl sx={{ minWidth: 200 }}>
                        <InputLabel id="sku-select-label">SKU</InputLabel>
                        <Select
                            labelId="sku-select-label"
                            value={selectedSkuId}
                            label="SKU"
                            onChange={e => setSelectedSkuId(e.target.value)}
                            disabled={!selectedClientId || skus.length === 0}
                        >
                            <MenuItem value=""><em>Seleccione SKU</em></MenuItem>
                            {skus.map(sku => (
                                <MenuItem key={sku.sku_id} value={sku.sku_id}>
                                    {sku.sku_name}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    <DatePicker
                        label="Fecha Inicio"
                        value={startDate}
                        onChange={(newValue) => setStartDate(newValue)}
                        format="YYYY-MM-DD"
                        slotProps={{ textField: { variant: 'outlined' } }}
                    />
                    <DatePicker
                        label="Fecha Fin"
                        value={endDate}
                        onChange={(newValue) => setEndDate(newValue)}
                        format="YYYY-MM-DD"
                        slotProps={{ textField: { variant: 'outlined' } }}
                    />
                    
                    <FormControl sx={{ minWidth: 150 }}>
                        <InputLabel id="source-select-label">Fuente (Histórico)</InputLabel>
                        <Select
                            labelId="source-select-label"
                            multiple
                            value={selectedSources}
                            onChange={e => setSelectedSources(e.target.value)}
                            renderValue={(selected) => selected.join(', ')}
                            label="Fuente (Histórico)"
                        >
                            <MenuItem value="sales">Ventas</MenuItem>
                            <MenuItem value="order">Órdenes</MenuItem>
                            <MenuItem value="shipments">Envíos</MenuItem>
                        </Select>
                    </FormControl>

                    <Button
                        variant="contained"
                        onClick={fetchSalesData}
                        disabled={loading || !selectedClientId || !selectedSkuId}
                        sx={{ height: '56px' }}
                    >
                        Cargar Datos
                    </Button>
                </Box>

                {/* Sección de Generación de Forecast */}
                <Box sx={{ mb: 0, border: '1px solid #0056b3', p: 2, background: '#e6f7ff', borderRadius: '4px' }}>
                    <Typography variant="h6" gutterBottom>Generar Pronóstico Estadístico</Typography>
                    <Typography variant="body2" sx={{ mb: 2, color: '#666' }}>
                        Nota: Los modelos de pronóstico requieren un mínimo de datos históricos (al menos 5-10 puntos de datos por Cliente-SKU).
                        Si no hay suficientes datos, la generación fallará.
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
                        <FormControl sx={{ minWidth: 150 }}>
                            <InputLabel id="model-name-label">Modelo</InputLabel>
                            <Select
                                labelId="model-name-label"
                                value={modelName}
                                label="Modelo"
                                onChange={(e) => setModelName(e.target.value)}
                            >
                                <MenuItem value="ETS">ETS (Exponential Smoothing)</MenuItem>
                                <MenuItem value="ARIMA">ARIMA</MenuItem>
                            </Select>
                        </FormControl>

                        <TextField
                            label="Alpha (0.0-1.0)"
                            type="number"
                            value={smoothingAlpha}
                            onChange={(e) => setSmoothingAlpha(parseFloat(e.target.value))}
                            inputProps={{ step: 0.1, min: 0, max: 1 }}
                            sx={{ width: 150 }}
                        />

                        <TextField
                            label="Horizonte (meses)"
                            type="number"
                            value={forecastHorizon}
                            onChange={(e) => setForecastHorizon(parseInt(e.target.value, 10))} 
                            inputProps={{ step: 1, min: 1 }}
                            sx={{ width: 150 }}
                        />

                        <Button
                            variant="contained"
                            color="secondary"
                            onClick={handleGenerateForecast}
                            disabled={loading || !selectedClientId || !selectedSkuId || selectedSources.length === 0}
                            sx={{ height: '56px' }}
                        >
                            {loading ? <CircularProgress size={24} /> : 'Generar Pronóstico'}
                        </Button>
                    </Box>
                    {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
                </Box>

                {/* Sección de Gestión de Versiones */}
                <Box sx={{ mb: 0, border: '1px solid #2e7d32', p: 2, background: '#e8f5e9', borderRadius: '4px' }}>
                    <Typography variant="h6" gutterBottom>Gestión de Versiones (Snapshots)</Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
                        <Button
                            variant="contained"
                            color="primary"
                            onClick={handleOpenSaveVersionModal}
                            disabled={loading || !selectedClientId}
                            sx={{ height: '56px' }}
                        >
                            Guardar Versión Actual
                        </Button>

                        <FormControl sx={{ minWidth: 200 }}>
                            <InputLabel id="version-select-label">Cargar Versión</InputLabel>
                            <Select
                                labelId="version-select-label"
                                value={selectedVersionId}
                                label="Cargar Versión"
                                onChange={e => setSelectedVersionId(e.target.value)}
                                disabled={!selectedClientId || versionsList.length === 0}
                            >
                                <MenuItem value=""><em>Seleccione Versión</em></MenuItem>
                                {versionsList.map(version => (
                                    <MenuItem key={version.version_id} value={version.version_id}>
                                        {version.version_name} ({dayjs(version.creation_date).format('DD/MM/YYYY HH:mm')})
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        <Button
                            variant="contained"
                            onClick={handleLoadVersion}
                            disabled={loading || !selectedVersionId || !selectedClientId || !selectedSkuId}
                            sx={{ height: '56px' }}
                        >
                            Cargar Versión Seleccionada
                        </Button>
                    </Box>
                </Box>

                {/* Gráfico de Datos */}
                <Box sx={{ width: '100%', minHeight: 600, mb: 2 }}>
                    <SalesChart chartData={chartData} />
                </Box>

                {/* --- TABLA AG GRID --- */}
                <Box sx={{ width: '100%', minHeight: 400, mb: 2 }}>
                    <Typography variant="h5" gutterBottom>Datos de Detalle</Typography>
                    <div className="ag-theme-alpine" style={{ height: '400px', width: '100%', position: 'relative' }}>
                        {loading && (
                            <Box sx={{
                                position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
                                display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'rgba(255,255,255,0.7)', zIndex: 2
                            }}>
                                <CircularProgress />
                            </Box>
                        )}
                        {error && (
                            <Box sx={{
                                position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
                                display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'rgba(255,255,255,0.7)', zIndex: 2
                            }}>
                                <Alert severity="error">{error}</Alert>
                            </Box>
                        )}
                        {!loading && !error && processedRowData.length > 0 && dynamicColumnDefs.length > 0 ? (
                            <AgGridReact
                                ref={gridRef}
                                rowData={processedRowData}
                                columnDefs={dynamicColumnDefs}
                                defaultColDef={defaultColDef}
                                onCellValueChanged={handleCellValueChanged}
                                getContextMenuItems={(params) => {
                                    const defaultItems = params.defaultItems.filter(item => item.name !== 'copyWithHeaders' && item.name !== 'paste');
                                    const colId = params.column?.colId;
                                    const rowData = params.node?.data;

                                    if (!rowData || !colId || !colId.startsWith('date_')) {
                                        return defaultItems;
                                    }
                                    
                                    const colIdParts = colId.replace('date_', '').split('_');
                                    const periodString = colIdParts[0];
                                    const keyFigureName = colIdParts.slice(1).join('_'); 

                                    const period = dayjs(periodString).toDate();
                                    const keyFigureId = keyFigureMap[keyFigureName];

                                    if (!period || !keyFigureId) {
                                        return defaultItems;
                                    }

                                    const cellDataForComment = {
                                        clientId: rowData.client_id,
                                        skuId: rowData.sku_id,
                                        clientFinalId: rowData.client_final_id,
                                        period: period,
                                        keyFigureName: keyFigureName,
                                        keyFigureId: keyFigureId,
                                    };

                                    return [
                                        ...defaultItems,
                                        'separator',
                                        {
                                            name: 'Agregar/Ver Comentarios',
                                            action: () => {
                                                handleCellContextMenu(params.event, params);
                                            },
                                            icon: '<span class="ag-icon ag-icon-comments"></span>',
                                        },
                                    ];
                                }}
                            />
                       
                   
                    ) : (
                        !loading && !error && (
                           <Box sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <Typography>Selecciona Cliente, SKU y rango de fechas para ver los datos.</Typography>
                            </Box>
                        )
                    )}
                    </div>
                </Box>

                {/* Modal para Comentarios (Material-UI Dialog) */}
                <Dialog open={openCommentModal} onClose={handleCloseCommentModal}>
                    <DialogTitle>Comentarios para {activeRow?.clientName} - {activeRow?.skuName} - {activeCol?.headerName}</DialogTitle>
                    <DialogContent>
                        <DialogContentText>
                            Añadir un nuevo comentario para esta celda:
                        </DialogContentText>
                        <TextField
                            autoFocus
                            margin="dense"
                            id="comment"
                            label="Nuevo Comentario"
                            type="text"
                            fullWidth
                            variant="outlined"
                            value={commentText}
                            onChange={(e) => setNewCommentText(e.target.value)}
                            multiline
                            rows={3}
                            sx={{ mb: 2 }}
                        />
                        {commentsForSelectedCell.length > 0 && (
                            <Box sx={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid #eee', p: 1, borderRadius: '4px' }}>
                                <Typography variant="subtitle1" gutterBottom>Historial de Comentarios:</Typography>
                                {existingComments.map((comment, index) => (
                                    <Box key={index} sx={{ mb: 1, pb: 1, borderBottom: '1px dashed #eee' }}>
                                        <Typography variant="body2">
                                            <strong>{new Date(comment.created_at).toLocaleString()}:</strong> {comment.comment}
                                        </Typography>
                                    </Box>
                                ))}
                            </Box>
                        )}
                        {commentsForSelectedCell.length === 0 && <Typography variant="body2">No hay comentarios anteriores para esta celda.</Typography>}
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={handleCloseCommentModal} color="secondary">
                            Cancelar
                        </Button>
                        <Button onClick={handleSaveComment} color="primary" disabled={!commentText.trim()}>
                            Guardar Comentario
                        </Button>
                    </DialogActions>
                </Dialog>

                {/* Modal para Guardar Versión (Material-UI Dialog) */}
                <Dialog open={openSaveVersionModal} onClose={handleCloseSaveVersionModal}>
                    <DialogTitle>Guardar Versión del Pronóstico</DialogTitle>
                    <DialogContent>
                        <DialogContentText>
                            Introduce un nombre y notas para la versión actual del pronóstico del cliente seleccionado.
                        </DialogContentText>
                        <TextField
                            autoFocus
                            margin="dense"
                            id="version-name"
                            label="Nombre de la Versión"
                            type="text"
                            fullWidth
                            variant="outlined"
                            value={versionName}
                            onChange={(e) => setVersionName(e.target.value)}
                            error={!!saveVersionError && !saveVersionSuccess}
                            helperText={saveVersionError}
                            sx={{ mt: 2 }}
                        />
                        <TextField
                            margin="dense"
                            id="version-notes"
                            label="Notas Adicionales (Opcional)"
                            type="text"
                            fullWidth
                            multiline
                            rows={3}
                            variant="outlined"
                            value={versionNotes}
                            onChange={(e) => setVersionNotes(e.target.value)}
                            sx={{ mt: 2 }}
                        />
                        {isSavingVersion && <CircularProgress size={24} sx={{ mt: 2 }} />}
                        {saveVersionSuccess && (
                            <Alert severity="success" sx={{ mt: 2 }}>
                                Versión guardada exitosamente.
                            </Alert>
                        )}
                        {saveVersionError && !saveVersionSuccess && (
                            <Alert severity="error" sx={{ mt: 2 }}>
                                {saveVersionError}
                            </Alert>
                        )}
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={handleCloseSaveVersionModal} color="secondary" disabled={isSavingVersion}>
                            Cancelar
                        </Button>
                        <Button onClick={handleSaveVersion} color="primary" disabled={isSavingVersion || !versionName.trim()}>
                            Guardar
                        </Button>
                    </DialogActions>
                </Dialog>
            </Box>
        </LocalizationProvider>
    );
}

export default SalesForecastData;