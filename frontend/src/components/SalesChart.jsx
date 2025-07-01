// frontend/src/components/SalesChart.jsx

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { Box, Typography } from '@mui/material'; // Asegúrate de importar Box y Typography

// Ya no necesitamos las constantes KF_ porque SalesForecastData ya procesa esto.

// El componente SalesChart ahora solo espera el 'chartData' ya pre-procesado
// de SalesForecastData, el cual contiene las trazas de Plotly.
function SalesChart({ chartData }) { // Solo recibe chartData
    const dataForPlotly = useMemo(() => {
        // Asegurarse de que chartData sea un array válido y no vacío
        if (!chartData || !Array.isArray(chartData) || chartData.length === 0) {
            return [];
        }
        // Filtrar trazas que puedan no tener datos x o y (defensa)
        return chartData.filter(trace => 
            trace && Array.isArray(trace.x) && trace.x.length > 0 && 
            Array.isArray(trace.y) && trace.y.length > 0
        );
    }, [chartData]);


    const layout = useMemo(() => ({
        title: 'Historial y Pronóstico de Ventas',
        xaxis: {
            title: 'Período',
            type: 'date',
            tickformat: '%Y-%m',
        },
        yaxis: {
            title: 'Valor',
            rangemode: 'tozero', // Asegura que el eje Y comience en 0
        },
        hovermode: 'x unified',
        height: 450, // Altura estándar para el gráfico
        margin: {
            l: 50,
            r: 50,
            b: 80,
            t: 50,
        },
        legend: {
            orientation: "h",
            yanchor: "bottom",
            y: 1.02,
            xanchor: "right",
            x: 1
        }
    }), []);

    // Si no hay datos válidos para Plotly, muestra un mensaje
    if (dataForPlotly.length === 0) {
        return (
            <Box sx={{ p: 2, border: '1px dashed #ccc', textAlign: 'center', minHeight: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Typography variant="body1" color="text.secondary">
                    No hay datos disponibles para mostrar el gráfico. Por favor, cargue datos.
                </Typography>
            </Box>
        );
    }

    return (
        <div style={{ marginTop: '30px', border: '1px solid #ccc', padding: '15px' }}>
            <h3>Visualización de Datos</h3>
            <Plot
                data={dataForPlotly}
                layout={layout}
                style={{ width: '100%', height: '100%' }}
                useResizeHandler={true} // Para que el gráfico se adapte al tamaño del contenedor
                config={{ responsive: true }}
            />
        </div>
    );
}

export default SalesChart;