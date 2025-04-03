import React from 'react';
import { Navigate } from 'react-router-dom';
import { AuthForm } from '../components/auth/AuthForm';
import { useAuth } from '../contexts/AuthContext';

export const AuthPage: React.FC = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-gray-500">Loading...</div>
        </div>
      </div>
    );
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  return <AuthForm />;
}; 