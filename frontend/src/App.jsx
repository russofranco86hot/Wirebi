// frontend/src/App.jsx - Versión actualizada y completa

import React from 'react';
import './App.css';

// Importamos los componentes
import ClientList from './components/ClientList';
import SkuList from './components/SkuList';
import KeyFigureList from './components/KeyFigureList';
import SalesForecastData from './components/SalesForecastData'; // Nuevo componente

function App() {
  return (
    <div className="App">
      <h1>Dashboard de Wirebi</h1>

      {/* Renderizamos los componentes de lista */}
      <ClientList />
      <SkuList />
      <KeyFigureList />

      {/* Renderizamos el componente principal para datos y filtros */}
      <SalesForecastData />

    </div>
  );
}

export default App;