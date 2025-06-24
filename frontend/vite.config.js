// frontend/vite.config.js - Versión corregida

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc' // CAMBIO: Usar @vitejs/plugin-react-swc

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
})