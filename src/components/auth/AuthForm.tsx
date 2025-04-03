import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';

type AuthMode = 'signin' | 'signup' | 'reset';

export const AuthForm: React.FC = () => {
  const { signIn, signUp, resetPassword, error } = useAuth();
  const [mode, setMode] = useState<AuthMode>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      switch (mode) {
        case 'signin':
          await signIn(email, password);
          break;
        case 'signup':
          await signUp(email, password);
          break;
        case 'reset':
          await resetPassword(email);
          alert('Check your email for password reset instructions');
          setMode('signin');
          break;
      }
    } catch (err) {
      // Ошибка уже обработана в контексте
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            {mode === 'signin' && 'Sign in to your account'}
            {mode === 'signup' && 'Create new account'}
            {mode === 'reset' && 'Reset your password'}
          </h2>
        </div>

        {error && (
          <div className="rounded-md bg-red-50 p-4">
            <div className="text-sm text-red-700">{error}</div>
          </div>
        )}

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="email-address" className="sr-only">
                Email address
              </label>
              <input
                id="email-address"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Email address"
              />
            </div>
            {mode !== 'reset' && (
              <div>
                <label htmlFor="password" className="sr-only">
                  Password
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                  placeholder="Password"
                />
              </div>
            )}
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className={`group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
                loading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {loading ? (
                <span className="absolute left-0 inset-y-0 flex items-center pl-3">
                  {/* Можно добавить спиннер */}
                </span>
              ) : null}
              {mode === 'signin' && 'Sign in'}
              {mode === 'signup' && 'Sign up'}
              {mode === 'reset' && 'Reset password'}
            </button>
          </div>

          <div className="flex items-center justify-between">
            {mode === 'signin' ? (
              <>
                <button
                  type="button"
                  onClick={() => setMode('signup')}
                  className="text-sm text-blue-600 hover:text-blue-500"
                >
                  Create new account
                </button>
                <button
                  type="button"
                  onClick={() => setMode('reset')}
                  className="text-sm text-blue-600 hover:text-blue-500"
                >
                  Forgot your password?
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => setMode('signin')}
                className="text-sm text-blue-600 hover:text-blue-500"
              >
                Back to sign in
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}; 