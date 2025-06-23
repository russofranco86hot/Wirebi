// frontend/src/components/KeyFigureList.jsx

import React, { useState, useEffect } from 'react';
import { fetchKeyFigures } from '../api'; // Importamos la función desde el archivo api.js

function KeyFigureList() {
  const [keyFigures, setKeyFigures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const getKeyFigures = async () => {
      try {
        const data = await fetchKeyFigures(); // Usamos la función centralizada
        setKeyFigures(data);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    getKeyFigures();
  }, []);

  if (loading) {
    return <p>Cargando Figuras Clave...</p>;
  }

  if (error) {
    return <p style={{ color: 'red' }}>Error al cargar Figuras Clave: {error}</p>;
  }

  return (
    <section>
      <h2>Figuras Clave</h2>
      {keyFigures.length === 0 ? (
        <p>No se encontraron Figuras Clave.</p>
      ) : (
        <ul>
          {keyFigures.map((kf) => (
            <li key={kf.key_figure_id}>
              {kf.name} (ID: {kf.key_figure_id}) - Aplica a: {kf.applies_to}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default KeyFigureList;