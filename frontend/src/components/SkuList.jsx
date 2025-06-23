// frontend/src/components/SkuList.jsx

import React, { useState, useEffect } from 'react';
import { fetchSkus } from '../api'; // Importamos la función desde el archivo api.js

function SkuList() {
  const [skus, setSkus] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const getSkus = async () => {
      try {
        const data = await fetchSkus(); // Usamos la función centralizada
        setSkus(data);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    getSkus();
  }, []);

  if (loading) {
    return <p>Cargando SKUs...</p>;
  }

  if (error) {
    return <p style={{ color: 'red' }}>Error al cargar SKUs: {error}</p>;
  }

  return (
    <section>
      <h2>SKUs</h2>
      {skus.length === 0 ? (
        <p>No se encontraron SKUs.</p>
      ) : (
        <ul>
          {skus.map((sku) => (
            <li key={sku.sku_id}>
              {sku.sku_name} (ID: {sku.sku_id})
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default SkuList;