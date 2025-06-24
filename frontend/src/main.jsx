// frontend/src/main.jsx - Versión corregida (Registro de AG Grid Community, FINAL)

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';

// --- ÚNICAS IMPORTACIONES Y REGISTRO PARA AG GRID COMMUNITY (GRATUITA) ---
// Importar los módulos esenciales y disponibles directamente desde el paquete principal 'ag-grid-community'
import { ModuleRegistry, ClientSideRowModelModule, ColumnsToolPanelModule, FiltersToolPanelModule, RowGroupingModule, RangeSelectionModule, StatusBarModule, CsvExportModule } from 'ag-grid-community'; 

// Registrar todos los módulos necesarios de la versión Community
ModuleRegistry.registerModules([
  ClientSideRowModelModule,
  ColumnsToolPanelModule,
  FiltersToolPanelModule,
  RowGroupingModule,
  RangeSelectionModule,
  StatusBarModule,
  CsvExportModule
]);
// --- FIN DE LAS IMPORTACIONES Y REGISTRO ÚNICOS ---

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);