// frontend/src/components/SalesChart.jsx

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';

function SalesChart({ historyData, forecastStatData, cleanHistoryData, finalForecastData, keyFigures, selectedKeyFigures, selectedSources }) {
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

    // 1. Historia Cruda (Sales, Order, Shipments)
    if (historyData && historyData.length > 0) {
      const groupedHistory = historyData.reduce((acc, item) => {
        const key = `${item.client_id}-${item.sku_id}-${item.key_figure_id}-${item.source}`;
        if (!acc[key]) {
          acc[key] = {
            x: [],
            y: [],
            type: 'scatter',
            mode: 'lines+markers',
            name: `${item.client?.client_name || 'N/A'} - ${item.sku?.sku_name || 'N/A'} - ${keyFigureNameMap[item.key_figure_id] || item.key_figure?.name || 'Historia'} (${item.source})`,
            visible: (selectedKeyFigures === null || selectedKeyFigures.includes(String(item.key_figure_id))) &&
                     (selectedSources === null || selectedSources.includes(item.source)) ? true : 'legendonly'
          };
        }
        acc[key].x.push(item.period);
        acc[key].y.push(item.value);
        allDates.add(new Date(item.period));
        return acc;
      }, {});
      data.push(...Object.values(groupedHistory));
    }

    // 2. Pronóstico Estadístico
    if (forecastStatData && forecastStatData.length > 0) {
        const groupedForecastStat = forecastStatData.reduce((acc, item) => {
            const key = `${item.client_id}-${item.sku_id}-stat-forecast`;
            if (!acc[key]) {
                acc[key] = {
                    x: [],
                    y: [],
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: `${item.client?.client_name || 'N/A'} - ${item.sku?.sku_name || 'N/A'} - Pronóstico Estadístico (${item.model_used})`,
                    line: { dash: 'dot', color: 'blue' }, // Línea punteada para pronóstico
                    marker: { symbol: 'circle-open' },
                    visible: (selectedKeyFigures === null || selectedKeyFigures.includes(String(4))) ? true : 'legendonly' // 4 es el ID de Pronóstico Estadístico
                };
            }
            acc[key].x.push(item.period);
            acc[key].y.push(item.value);
            allDates.add(new Date(item.period));
            return acc;
        }, {});
        data.push(...Object.values(groupedForecastStat));
    }

    // 3. Historia Limpia (Nueva)
    if (cleanHistoryData && cleanHistoryData.length > 0) {
        const groupedCleanHistory = cleanHistoryData.reduce((acc, item) => {
            const key = `${item.client_id}-${item.sku_id}-clean-history`;
            if (!acc[key]) {
                acc[key] = {
                    x: [],
                    y: [],
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: `${item.clientName || 'N/A'} - ${item.skuName || 'N/A'} - Historia Limpia`,
                    line: { color: 'green' }, // Color distintivo para historia limpia
                    visible: (selectedKeyFigures === null || selectedKeyFigures.includes(String(5))) ? true : 'legendonly' // 5 es el ID de Historia Limpia
                };
            }
            acc[key].x.push(item.period);
            acc[key].y.push(item.value);
            allDates.add(new Date(item.period));
            return acc;
        }, {});
        data.push(...Object.values(groupedCleanHistory));
    }

    // 4. Pronóstico Final (Nueva)
    if (finalForecastData && finalForecastData.length > 0) {
        const groupedFinalForecast = finalForecastData.reduce((acc, item) => {
            const key = `${item.client_id}-${item.sku_id}-final-forecast`;
            if (!acc[key]) {
                acc[key] = {
                    x: [],
                    y: [],
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: `${item.clientName || 'N/A'} - ${item.skuName || 'N/A'} - Pronóstico Final`,
                    line: { dash: 'dashdot', color: 'red' }, // Línea dash-dot para pronóstico final
                    marker: { symbol: 'star' },
                    visible: (selectedKeyFigures === null || selectedKeyFigures.includes(String(6))) ? true : 'legendonly' // 6 es el ID de Pronóstico Final
                };
            }
            acc[key].x.push(item.period);
            acc[key].y.push(item.value);
            allDates.add(new Date(item.period));
            return acc;
        }, {});
        data.push(...Object.values(groupedFinalForecast));
    }

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
      },
      yaxis: {
        title: 'Valor',
      },
      hovermode: 'x unified', // Muestra tooltips para todas las series en la misma fecha
      height: 500,
      responsive: true,
      margin: {
        l: 50,
        r: 50,
        b: 100,
        t: 100,
        pad: 4
      },
    };

    return { data, layout };

  }, [historyData, forecastStatData, cleanHistoryData, finalForecastData, keyFigureNameMap, selectedKeyFigures, selectedSources]);


  return (
    <div style={{ marginTop: '30px', border: '1px solid #ccc', padding: '15px' }}>
      <h3>Visualización de Datos</h3>
      {chartData.data.length > 0 ? (
        <Plot
          data={chartData.data}
          layout={chartData.layout}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler={true} // Hace que el gráfico se adapte al tamaño del contenedor
        />
      ) : (
        <p>No hay datos seleccionados para mostrar en el gráfico. Por favor, realiza una búsqueda.</p>
      )}
    </div>
  );
}

export default SalesChart;