// FILE: /home/user/advocatus-frontend/src/pages/AuthPage.tsx
// DEFINITIVE VERSION 9.6 - REPAIR: Reverted degradation caused by V9.5 (comment string rendering) and retained all functional fixes.

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../context/AuthContext'; // <-- CRITICAL FIX (V9.5): Changed from named import { useAuth } to default import useAuth
import { LoginRequest, RegisterRequest } from '../data/types';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Scale } from 'lucide-react';

const AuthPage: React.FC = () => {
  const { t } = useTranslation();
  const { login, register } = useAuth();
  const navigate = useNavigate();
  
  const [isLoginMode, setIsLoginMode] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const validateInputs = (): boolean => {
    setError(null);
    if (!username || !password) {
      setError(t('auth.required'));
      return false;
    }
    
    if (!isLoginMode) {
      if (password !== confirmPassword) {
        setError(t('auth.passwordMismatch'));
        return false;
      }
      if (password.length < 8) {
        setError(t('auth.passwordTooShort'));
        return false;
      }
      if (!email || !email.includes('@')) {
        setError(t('auth.invalidEmail'));
        return false;
      }
    }
    return true;
  };

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateInputs()) return;

    setIsLoading(true);
    setError(null);

    try {
      if (isLoginMode) {
        // FIX (V9.3): Ensure login data conforms to the expected structure.
        const data: LoginRequest = { username, password }; 
        await login(data);
        // CRITICAL FIX (V9.4): Only redirect to /dashboard after a successful LOGIN.
        navigate('/dashboard'); 
      } else {
        const data: RegisterRequest = { username, password, email };
        await register(data);
        
        // CRITICAL FIX (V9.4): After successful registration, redirect to login page.
        setIsLoginMode(true);
        setUsername(''); // Clear inputs for fresh login attempt
        setPassword('');
        setEmail('');
        setConfirmPassword('');
        navigate('/login'); 
      }
    } catch (err: any) {
      const status = err.response?.status;
      if (status === 401) {
        console.error("Login attempt failed. Check backend logs for user validation failure.", err); 
        setError(t('auth.loginFailed'));
      } else if (status === 400 && !isLoginMode) {
         setError(t('auth.registerFailed'));
      } else {
        setError(t('auth.networkError'));
      }
    } finally {
      setIsLoading(false); 
    }
  };

  const toggleMode = () => {
    setIsLoginMode(!isLoginMode);
    setError(null);
  };
  
  const isFormValid = isLoginMode 
    ? (username && password) 
    : (username && password && email && password === confirmPassword && password.length >= 8);
  
  return (
    <div className="flex items-center justify-center min-h-screen 
                    bg-background-dark bg-gradient-to-br from-background-dark via-background-light to-background-dark 
                    bg-[length:200%_200%] animate-gradient-shift">
      
      <motion.div 
        className="w-full max-w-md p-8 space-y-6 bg-background-light/50 backdrop-blur-md border border-glass-edge rounded-2xl shadow-2xl glow-primary/20"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", stiffness: 100 }}
      >
        <div className="text-center mb-6">
          <div className="flex items-center justify-center">
            <Scale className="h-8 w-8 text-text-primary mr-3" />
            <h1 className="text-3xl font-extrabold text-text-primary">Advocatus AI</h1>
          </div>
          <p className="text-text-secondary mt-2">{t('auth.subtitle')}</p>
        </div>
        
        <form onSubmit={handleAuth} className="space-y-4">
          
          {error && (
            <div className="p-3 text-sm text-red-100 bg-red-700 rounded-xl">{error}</div>
          )}

          <div>
            <label className="block text-sm font-medium text-text-secondary">{t('auth.username')}</label>
            <input 
              type="text" 
              value={username} 
              onChange={(e) => setUsername(e.target.value)} 
              className="block w-full h-10 mt-1 px-4 py-2 bg-background-dark/50 rounded-xl text-text-primary focus:ring-primary-start focus:border-primary-start border border-glass-edge" 
              disabled={isLoading}
            />
          </div>

          {!isLoginMode && (
            <div>
              <label className="block text-sm font-medium text-text-secondary">{t('auth.email')}</label>
              <input 
                type="email" 
                value={email} 
                onChange={(e) => setEmail(e.target.value)} 
                className="block w-full h-10 mt-1 px-4 py-2 bg-background-dark/50 rounded-xl text-text-primary focus:ring-primary-start focus:border-primary-start border border-glass-edge" 
                disabled={isLoading}
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-text-secondary">{t('auth.password')}</label>
            <input 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              className="block w-full h-10 mt-1 px-4 py-2 bg-background-dark/50 rounded-xl text-text-primary focus:ring-primary-start focus:border-primary-start border border-glass-edge" 
              disabled={isLoading}
            />
          </div>

          {!isLoginMode && (
            <div>
              <label className="block text-sm font-medium text-text-secondary">{t('auth.passwordConfirm')}</label>
              <input 
                type="password" 
                value={confirmPassword} 
                onChange={(e) => setConfirmPassword(e.target.value)} 
                className="block w-full h-10 mt-1 px-4 py-2 bg-background-dark/50 rounded-xl text-text-primary focus:ring-primary-start focus:border-primary-start border border-glass-edge" 
                disabled={isLoading}
              />
            </div>
          )}

          <motion.button 
            type="submit" 
            className={`w-full text-white font-semibold py-3 rounded-xl transition-all duration-300 shadow-lg glow-primary
                       bg-gradient-to-r from-primary-start to-primary-end ${!isFormValid || isLoading ? 'opacity-50 cursor-not-allowed' : ''}`} 
            disabled={!isFormValid || isLoading}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {isLoading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin h-5 w-5 mr-3" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {isLoginMode ? t('general.login') : t('auth.registerButton')}
              </span>
            ) : isLoginMode ? t('auth.loginButton') : t('auth.registerButton')}
          </motion.button>
        </form>

        <p className="text-center text-sm text-text-secondary">
          <button onClick={toggleMode} className="text-secondary-start hover:text-secondary-end transition-colors">
            {isLoginMode ? t('auth.switchToRegister') : t('auth.switchToLogin')}
          </button>
        </p>
      </motion.div>
    </div>
  );
};

export default AuthPage;