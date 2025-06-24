// frontend/src/components/SalesChart.jsx - Versión FINAL con Historia Suavizada y Forecast Stat

import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

function SalesChart({ historyData, forecastStatData, keyFigures, selectedKeyFigures, selectedSources }) {
  // Aseguramos que data sea un array y no null/undefined
  if (!historyData && !forecastStatData || (historyData.length === 0 && forecastStatData.length === 0)) {
    return <p>No hay datos disponibles para el gráfico con los filtros seleccionados.</p>;
  }

  // --- Procesamiento de Datos para el Gráfico ---
  const combinedDataMap = new Map();

  // Procesar datos históricos (crudos y suavizados)
  if (historyData && historyData.length > 0) {
    historyData.forEach(item => {
      const period = item.period; 
      const keyFigureName = item.key_figure?.name; // "Sales", "Order", "Historia Suavizada"
      const sourceName = item.source; // "sales", "order", "shipments"
      const value = item.value;

      if (!period || value === undefined || value === null) return;

      if (!combinedDataMap.has(period)) {
        combinedDataMap.set(period, { period: period });
      }
      const currentPeriodData = combinedDataMap.get(period);

      // Crear una clave única para la línea basada en KeyFigure y Source para Historia
      // Ej. "Sales_sales", "Order_order", "Historia Suavizada_sales"
      const dataKey = `${keyFigureName}_${sourceName}`; 
      currentPeriodData[dataKey] = value;
    });
  }

  // Procesar datos de pronóstico estadístico
  if (forecastStatData && forecastStatData.length > 0) {
    forecastStatData.forEach(item => {
      const period = item.period;
      const modelUsed = item.model_used; 
      const value = item.value;

      if (!period || value === undefined || value === null) return;

      if (!combinedDataMap.has(period)) {
        combinedDataMap.set(period, { period: period });
      }
      const currentPeriodData = combinedDataMap.get(period);

      // Clave única para la línea de pronóstico estadístico
      const dataKey = "Pronóstico Estadístico"; // Nombre constante para la línea
      currentPeriodData[dataKey] = value;
    });
  }

  const chartData = Array.from(combinedDataMap.values()).sort((a, b) => new Date(a.period) - new Date(b.period));

  if (!chartData || chartData.length === 0) {
    return <p>No hay datos disponibles para el gráfico con los filtros seleccionados.</p>;
  }

  // --- Definición de las Líneas del Gráfico ---
  const linesToRender = [];
  const colors = [
    '#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#0088fe', '#00c49f', '#ffbb28',
    '#a4de6c', '#d0ed57', '#83a6ed', '#8dd1e1', '#c09893', '#b3d9d4'
  ]; 
  let colorIndex = 0;

  const activeKeyFiguresIds = selectedKeyFigures || [];

  // 1. Líneas para Historia Cruda y Historia Suavizada
  keyFigures.forEach(kf => {
      // Filtrar por las KeyFigures seleccionadas en la UI
      if (activeKeyFiguresIds.length > 0 && !activeKeyFiguresIds.includes(String(kf.key_figure_id))) {
          return; 
      }

      const appliesTo = kf.applies_to;
      
      if (appliesTo === 'history') {
          const activeSources = selectedSources || ['sales', 'order', 'shipments']; // Default a todas si no hay filtro

          activeSources.forEach(source => {
              const dataKey = `${kf.name}_${source}`; 
              const displayName = `${kf.name} (${source.charAt(0).toUpperCase() + source.slice(1)})`;
              
              if (chartData.some(d => d[dataKey] !== undefined && d[dataKey] !== null)) {
                linesToRender.push(
                    <Line 
                        key={dataKey} 
                        type="monotone" 
                        dataKey={dataKey} 
                        stroke={colors[colorIndex % colors.length]} 
                        activeDot={{ r: 8 }} 
                        name={displayName} 
                        strokeWidth={2}
                    />
                );
                colorIndex++;
              }
          });
      }
  });

  // 2. Línea para "Pronóstico Estadístico"
  if (chartData.some(d => d["Pronóstico Estadístico"] !== undefined && d["Pronóstico Estadístico"] !== null)) {
      linesToRender.push(
          <Line 
              key="Statistical Forecast" 
              type="monotone" 
              dataKey="Pronóstico Estadístico" 
              stroke={colors[colorIndex % colors.length]} 
              activeDot={{ r: 8 }} 
              name="Pronóstico Estadístico" 
              strokeWidth={3} 
              strokeDasharray="5 5" 
          />
      );
      colorIndex++;
  }


  return (
    <section style={{ marginTop: '30px' }}>
      <h3>Gráfico de Datos</h3>
      <ResponsiveContainer width="100%" height={400}>
        <LineChart
          data={chartData}
          margin={{
            top: 5, right: 30, left: 20, bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="period" />
          <YAxis />
          <Tooltip />
          <Legend />
          {linesToRender}
        </LineChart>
      </ResponsiveContainer>
    </section>
  );
}

export default SalesChart;