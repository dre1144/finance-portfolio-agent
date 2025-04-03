import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Header } from './components/layout/Header';
import { AuthPage } from './pages/auth';
import { SettingsPage } from './pages/settings';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <Routes>
            <Route path="/auth" element={<AuthPage />} />
            
            {/* Защищенные маршруты */}
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <>
                    <Header />
                    <main>
                      <Routes>
                        <Route path="/settings" element={<SettingsPage />} />
                        {/* Другие защищенные маршруты */}
                      </Routes>
                    </main>
                  </>
                </ProtectedRoute>
              }
            />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}; 