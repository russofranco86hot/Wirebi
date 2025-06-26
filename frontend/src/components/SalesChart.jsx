// frontend/src/components/SalesChart.jsx

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';

// Constantes para IDs de Key Figures (para la lógica de filtrado)
const KF_SALES_ID = 1;
const KF_ORDER_ID = 2;
const KF_SHIPMENTS_ID = 3;
const KF_STATISTICAL_FORECAST_ID = 4;
const KF_CLEAN_HISTORY_ID = 5;
const KF_FINAL_FORECAST_ID = 6;


function SalesChart({ historyData, forecastStatData, cleanHistoryData, finalForecastData, keyFigures, selectedKeyFigures, selectedSources, forecastStartDate }) {
  // Mapeo de keyFigures por ID para fácil acceso al nombre
  const keyFigureNameMap = useMemo(() => {
    return keyFigures.reduce((map, kf) => {
      map[kf.key_figure_id] = kf.name;
      return map;
    }, {});
  }, [keyFigures]);

  const chartData = useMemo(() => {
    const data = [];
    let allDates = new Set(); // Para encontrar el rango de fechas dinámicamente

    // Helper para añadir y filtrar datos
    const addAndFilterData = (sourceData, kfId, kfName, seriesNameSuffix, lineColor, lineDash, markerSymbol, isHistoricalSeries, isForecastSeries) => {
        if (sourceData && sourceData.length > 0) {
            const filteredAndGrouped = sourceData.reduce((acc, item) => {
                const itemPeriodDate = new Date(item.period);
                const shouldInclude = forecastStartDate 
                    ? (isHistoricalSeries && itemPeriodDate < forecastStartDate) || (isForecastSeries && itemPeriodDate >= forecastStartDate)
                    : (isHistoricalSeries ? true : false); // Si no hay forecastStartDate, las series históricas incluyen todo

                if (shouldInclude) {
                    const key = `${item.client_id}-${item.sku_id}-${kfId}-${item.source || 'N/A'}`;
                    if (!acc[key]) {
                        acc[key] = {
                            x: [],
                            y: [],
                            type: 'scatter',
                            mode: 'lines+markers',
                            name: `${item.client?.client_name || item.clientName || 'N/A'} - ${item.sku?.sku_name || item.skuName || 'N/A'} - ${kfName}${seriesNameSuffix ? ` (${seriesNameSuffix})` : ''}`,
                            line: lineColor ? { color: lineColor, dash: lineDash } : undefined,
                            marker: markerSymbol ? { symbol: markerSymbol } : undefined,
                            visible: (selectedKeyFigures === null || selectedKeyFigures.includes(String(kfId))) ? true : 'legendonly'
                        };
                    }
                    acc[key].x.push(item.period);
                    acc[key].y.push(item.value);
                    allDates.add(itemPeriodDate);
                }
                return acc;
            }, {});
            data.push(...Object.values(filteredAndGrouped));
        }
    };

    // 1. Historia Cruda (Sales, Order, Shipments)
    if (historyData && historyData.length > 0) {
        historyData.forEach(item => {
            const itemPeriodDate = new Date(item.period);
            const shouldInclude = forecastStartDate ? itemPeriodDate < forecastStartDate : true;
            if (shouldInclude && (selectedKeyFigures === null || selectedKeyFigures.includes(String(item.key_figure_id)))) {
                const key = `${item.client_id}-${item.sku_id}-${item.key_figure_id}-${item.source || 'N/A'}`;
                let existingTrace = data.find(trace => trace.name.includes(`${item.client?.client_name || item.clientName || 'N/A'} - ${item.sku?.sku_name || item.skuName || 'N/A'} - ${keyFigureNameMap[item.key_figure_id] || item.key_figure?.name || 'Historia'} (${item.source})`));
                if (!existingTrace) {
                    existingTrace = {
                        x: [],
                        y: [],
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: `${item.client?.client_name || item.clientName || 'N/A'} - ${item.sku?.sku_name || item.skuName || 'N/A'} - ${keyFigureNameMap[item.key_figure_id] || item.key_figure?.name || 'Historia'} (${item.source})`,
                        visible: (selectedSources === null || selectedSources.includes(item.source)) ? true : 'legendonly'
                    };
                    data.push(existingTrace);
                }
                existingTrace.x.push(item.period);
                existingTrace.y.push(item.value);
                allDates.add(itemPeriodDate);
            }
        });
    }


    // 2. Historia Limpia (KF_CLEAN_HISTORY_ID = 5) - Solo en período histórico
    addAndFilterData(cleanHistoryData, KF_CLEAN_HISTORY_ID, 'Historia Limpia', null, 'green', null, null, true, false);

    // 3. Pronóstico Estadístico (KF_STATISTICAL_FORECAST_ID = 4) - Solo en período de pronóstico
    addAndFilterData(forecastStatData, KF_STATISTICAL_FORECAST_ID, 'Pronóstico Estadístico', 'Estadístico', 'blue', 'dot', 'circle-open', false, true);

    // 4. Pronóstico Final (KF_FINAL_FORECAST_ID = 6) - Solo en período de pronóstico
    addAndFilterData(finalForecastData, KF_FINAL_FORECAST_ID, 'Pronóstico Final', 'Final', 'red', 'dashdot', 'star', false, true);


    // Determinar el rango de fechas para el layout
    let minDate = allDates.size > 0 ? new Date(Math.min(...Array.from(allDates))) : null;
    let maxDate = allDates.size > 0 ? new Date(Math.max(...Array.from(allDates))) : null;

    // Ajustar el rango del eje X para que sea un poco más amplio
    if (minDate && maxDate) {
      minDate.setMonth(minDate.getMonth() - 1); // Un mes antes
      maxDate.setMonth(maxDate.getMonth() + 1); // Un mes después
    }


    const layout = {
      title: 'Demanda y Pronóstico',
      xaxis: {
        title: 'Período',
        type: 'date',
        range: minDate && maxDate ? [minDate.toISOString().split('T')[0], maxDate.toISOString().split('T')[0]] : [],
        tickformat: "%b %Y",
        automargin: true,
      },
      yaxis: {
        title: 'Valor',
        automargin: true,
      },
      hovermode: 'x unified',
      height: 650, // Aumentado para dar más espacio al gráfico
      responsive: true,
      margin: {
        l: 50,
        r: 50,
        b: 100,
        t: 80, // Ajustado para dar espacio a la leyenda si está arriba
        pad: 4
      },
      legend: { // Configuración de la leyenda
        x: 0,
        xanchor: 'left', // Anclado a la izquierda
        y: -0.2, // Colocado por debajo del gráfico
        yanchor: 'top', // Anclado a la parte superior de la leyenda
        orientation: 'h', // Horizontal
        bgcolor: 'rgba(255, 255, 255, 0.8)', // Fondo semi-transparente
        bordercolor: '#ccc',
        borderwidth: 1,
        font: { size: 10 },
      },
    };

    return { data, layout };

  }, [historyData, forecastStatData, cleanHistoryData, finalForecastData, keyFigureNameMap, selectedKeyFigures, selectedSources, forecastStartDate]);


  return (
    <div style={{ marginTop: '30px', border: '1px solid #ccc', padding: '15px' }}>
      <h3>Visualización de Datos</h3>
      {chartData.data.length > 0 ? (
        <Plot
          data={chartData.data}
          layout={chartData.layout}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler={true}
        />
      ) : (
        <p>No hay datos seleccionados para mostrar en el gráfico. Por favor, realiza una búsqueda.</p>
      )}
    </div>
  );
}

export default SalesChart;