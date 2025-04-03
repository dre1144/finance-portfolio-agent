import React, { useState } from 'react';
import { useUserConnections } from '../../hooks/useUserConnections';
import { Power, Trash2, RefreshCw } from 'lucide-react';

export const ConnectionManager: React.FC = () => {
  const {
    connections,
    loading,
    error,
    createConnection,
    updateConnectionToken,
    toggleConnectionStatus,
    deleteConnection,
    clearError
  } = useUserConnections();

  const [newBrokerType, setNewBrokerType] = useState('');
  const [newToken, setNewToken] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createConnection(newBrokerType, newToken);
      setNewBrokerType('');
      setNewToken('');
      setIsAdding(false);
    } catch (err) {
      // Ошибка уже обработана в хуке
    }
  };

  const handleUpdateToken = async (connectionId: string, newToken: string) => {
    try {
      await updateConnectionToken(connectionId, newToken);
    } catch (err) {
      // Ошибка уже обработана в хуке
    }
  };

  const handleToggleStatus = async (connectionId: string, currentStatus: boolean) => {
    try {
      await toggleConnectionStatus(connectionId, !currentStatus);
    } catch (err) {
      // Ошибка уже обработана в хуке
    }
  };

  const handleDelete = async (connectionId: string) => {
    if (window.confirm('Are you sure you want to delete this connection?')) {
      try {
        await deleteConnection(connectionId);
      } catch (err) {
        // Ошибка уже обработана в хуке
      }
    }
  };

  if (error) {
    return (
      <div className="text-red-500 p-4" onClick={clearError}>
        Error: {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-semibold">Broker Connections</h2>
        <button
          onClick={() => setIsAdding(!isAdding)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          {isAdding ? 'Cancel' : 'Add Connection'}
        </button>
      </div>

      {/* Форма добавления нового подключения */}
      {isAdding && (
        <form onSubmit={handleSubmit} className="space-y-4 p-4 bg-gray-50 rounded-lg">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Broker Type
            </label>
            <input
              type="text"
              value={newBrokerType}
              onChange={(e) => setNewBrokerType(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Access Token
            </label>
            <input
              type="password"
              value={newToken}
              onChange={(e) => setNewToken(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              required
            />
          </div>
          <button
            type="submit"
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Add Connection
          </button>
        </form>
      )}

      {/* Список подключений */}
      <div className="space-y-4">
        {loading ? (
          <div className="text-center text-gray-500">Loading...</div>
        ) : connections.length === 0 ? (
          <div className="text-center text-gray-500">No connections found</div>
        ) : (
          connections.map(connection => (
            <div
              key={connection.id}
              className="p-4 bg-white rounded-lg shadow border border-gray-200"
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-medium text-gray-900">
                    {connection.broker_type}
                  </h3>
                  <p className="text-sm text-gray-500">
                    Created: {new Date(connection.created_at).toLocaleString()}
                  </p>
                  {connection.last_check_at && (
                    <p className="text-sm text-gray-500">
                      Last check: {new Date(connection.last_check_at).toLocaleString()}
                      {connection.metadata.last_check_status && (
                        <span className={`ml-2 ${
                          connection.metadata.last_check_status === 'success'
                            ? 'text-green-600'
                            : 'text-red-600'
                        }`}>
                          ({connection.metadata.last_check_status})
                        </span>
                      )}
                    </p>
                  )}
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => handleToggleStatus(connection.id, connection.is_active)}
                    className={`p-2 rounded-full ${
                      connection.is_active
                        ? 'text-green-600 hover:bg-green-100'
                        : 'text-gray-400 hover:bg-gray-100'
                    }`}
                    title={connection.is_active ? 'Deactivate' : 'Activate'}
                  >
                    <Power className="h-5 w-5" />
                  </button>
                  <button
                    onClick={() => {
                      const newToken = window.prompt('Enter new access token:');
                      if (newToken) {
                        handleUpdateToken(connection.id, newToken);
                      }
                    }}
                    className="p-2 rounded-full text-blue-600 hover:bg-blue-100"
                    title="Update Token"
                  >
                    <RefreshCw className="h-5 w-5" />
                  </button>
                  <button
                    onClick={() => handleDelete(connection.id)}
                    className="p-2 rounded-full text-red-600 hover:bg-red-100"
                    title="Delete"
                  >
                    <Trash2 className="h-5 w-5" />
                  </button>
                </div>
              </div>
              {connection.metadata.error_message && (
                <div className="mt-2 text-sm text-red-600">
                  Error: {connection.metadata.error_message}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}; 