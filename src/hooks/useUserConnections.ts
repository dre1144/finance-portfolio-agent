import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import { useAuth } from '../contexts/AuthContext';

export interface UserConnection {
  id: string;
  broker_type: string;
  is_active: boolean;
  created_at: string;
  last_check_at: string | null;
  metadata: {
    created_by: string;
    created_at: string;
    updated_at?: string;
    last_check_status?: string;
    error_message?: string;
  };
}

export const useUserConnections = () => {
  const { user } = useAuth();
  const [connections, setConnections] = useState<UserConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      setConnections([]);
      setLoading(false);
      return;
    }

    const loadConnections = async () => {
      try {
        setLoading(true);
        const { data, error: fetchError } = await supabase
          .from('user_connections')
          .select('*')
          .eq('user_id', user.id)
          .order('created_at', { ascending: false });

        if (fetchError) throw fetchError;

        setConnections(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load connections');
      } finally {
        setLoading(false);
      }
    };

    loadConnections();

    // Подписываемся на изменения
    const channel = supabase
      .channel(`user_connections:${user.id}`)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'user_connections',
          filter: `user_id=eq.${user.id}`,
        },
        (payload) => {
          switch (payload.eventType) {
            case 'INSERT':
              setConnections(prev => [payload.new as UserConnection, ...prev]);
              break;
            case 'UPDATE':
              setConnections(prev =>
                prev.map(conn =>
                  conn.id === payload.new.id
                    ? { ...conn, ...payload.new }
                    : conn
                )
              );
              break;
            case 'DELETE':
              setConnections(prev =>
                prev.filter(conn => conn.id !== payload.old.id)
              );
              break;
          }
        }
      )
      .subscribe();

    return () => {
      channel.unsubscribe();
    };
  }, [user]);

  const createConnection = async (brokerType: string, token: string) => {
    try {
      if (!user) throw new Error('User not authenticated');

      const { data, error: createError } = await supabase
        .rpc('create_user_connection', {
          p_user_id: user.id,
          p_broker_type: brokerType,
          p_token: token
        });

      if (createError) throw createError;

      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create connection');
      throw err;
    }
  };

  const updateConnectionToken = async (connectionId: string, newToken: string) => {
    try {
      const { error: updateError } = await supabase
        .rpc('update_user_connection_token', {
          p_connection_id: connectionId,
          p_new_token: newToken
        });

      if (updateError) throw updateError;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update connection token');
      throw err;
    }
  };

  const toggleConnectionStatus = async (connectionId: string, isActive: boolean) => {
    try {
      const { error: updateError } = await supabase
        .from('user_connections')
        .update({ is_active: isActive })
        .eq('id', connectionId);

      if (updateError) throw updateError;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update connection status');
      throw err;
    }
  };

  const deleteConnection = async (connectionId: string) => {
    try {
      const { error: deleteError } = await supabase
        .from('user_connections')
        .delete()
        .eq('id', connectionId);

      if (deleteError) throw deleteError;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete connection');
      throw err;
    }
  };

  const clearError = () => setError(null);

  return {
    connections,
    loading,
    error,
    createConnection,
    updateConnectionToken,
    toggleConnectionStatus,
    deleteConnection,
    clearError,
  };
}; 