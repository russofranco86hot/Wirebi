// frontend/src/main.jsx - Versión corregida (Cierre de React.StrictMode)

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';

// --- ÚNICAS IMPORTACIONES Y REGISTRO PARA AG GRID COMMUNITY (GRATUITA Y MINIMALISTA) ---
import { ModuleRegistry, ClientSideRowModelModule } from 'ag-grid-community'; 

ModuleRegistry.registerModules([
  ClientSideRowModelModule,
]);
// --- FIN DE LAS IMPORTACIONES Y REGISTRO ÚNICOS ---

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>, {/* CORREGIDO: Añadido el '>' de cierre aquí */}
);