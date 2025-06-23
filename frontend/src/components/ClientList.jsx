// frontend/src/components/ClientList.jsx

import React, { useState, useEffect } from 'react';
import { fetchClients } from '../api'; // Importamos la función desde el archivo api.js

function ClientList() {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const getClients = async () => {
      try {
        const data = await fetchClients(); // Usamos la función centralizada
        setClients(data);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    getClients();
  }, []);

  if (loading) {
    return <p>Cargando clientes...</p>;
  }

  if (error) {
    return <p style={{ color: 'red' }}>Error al cargar clientes: {error}</p>;
  }

  return (
    <section>
      <h2>Clientes</h2>
      {clients.length === 0 ? (
        <p>No se encontraron clientes.</p>
      ) : (
        <ul>
          {clients.map((client) => (
            <li key={client.client_id}>
              {client.client_name} (ID: {client.client_id})
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default ClientList;