// FILE: /home/user/advocatus-frontend/src/pages/AuthPage.tsx
// PHOENIX PROTOCOL - MOBILE OPTIMIZATION
// 1. RESPONSIVE PADDING: Adjusted container to 'p-6 sm:p-8' for better mobile fit.
// 2. TYPOGRAPHY SCALING: 'text-2xl sm:text-3xl' for the main title.
// 3. INPUT SPACING: Ensured sufficient vertical spacing for touch keyboards.

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../context/AuthContext';
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
        const data: LoginRequest = { username, password }; 
        await login(data);
        navigate('/dashboard'); 
      } else {
        const data: RegisterRequest = { username, password, email };
        await register(data);
        
        // On successful registration, switch to login mode with a success message
        setIsLoginMode(true);
        setError(t('auth.registerSuccess')); // Provide positive feedback
        setPassword('');
        setConfirmPassword('');
      }
    } catch (err: any) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;

      if (status === 422) {
        setError(t('auth.validationError'));
      } else if (status === 409) {
        setError(detail || t('auth.userExists'));
      } else if (status === 401) {
        setError(t('auth.loginFailed'));
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
    <div className="flex items-center justify-center min-h-screen px-4
                    bg-background-dark bg-gradient-to-br from-background-dark via-background-light to-background-dark 
                    bg-[length:200%_200%] animate-gradient-shift">
      
      <motion.div 
        className="w-full max-w-md p-6 sm:p-8 space-y-6 bg-background-light/50 backdrop-blur-md border border-glass-edge rounded-2xl shadow-2xl glow-primary/20"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", stiffness: 100 }}
      >
        <div className="text-center mb-6">
          <div className="flex items-center justify-center">
            <Scale className="h-7 w-7 sm:h-8 sm:w-8 text-text-primary mr-3" />
            <h1 className="text-2xl sm:text-3xl font-extrabold text-text-primary">Advocatus AI</h1>
          </div>
          <p className="text-text-secondary mt-2 text-sm sm:text-base">{t('auth.subtitle')}</p>
        </div>
        
        <form onSubmit={handleAuth} className="space-y-4">
          
          {error && (
            <div className={`p-3 text-sm rounded-xl ${error === t('auth.registerSuccess') ? 'text-green-100 bg-green-700' : 'text-red-100 bg-red-700'}`}>
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-text-secondary">{t('auth.username')}</label>
            <input 
              type="text" 
              value={username} 
              onChange={(e) => setUsername(e.target.value)} 
              className="block w-full h-10 mt-1 px-4 py-2 bg-background-dark/50 rounded-xl text-text-primary focus:ring-primary-start focus:border-primary-start border border-glass-edge transition-all" 
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
                className="block w-full h-10 mt-1 px-4 py-2 bg-background-dark/50 rounded-xl text-text-primary focus:ring-primary-start focus:border-primary-start border border-glass-edge transition-all" 
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
              className="block w-full h-10 mt-1 px-4 py-2 bg-background-dark/50 rounded-xl text-text-primary focus:ring-primary-start focus:border-primary-start border border-glass-edge transition-all" 
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
                className="block w-full h-10 mt-1 px-4 py-2 bg-background-dark/50 rounded-xl text-text-primary focus:ring-primary-start focus:border-primary-start border border-glass-edge transition-all" 
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

        <p className="text-center text-sm text-text-secondary mt-6">
          <button onClick={toggleMode} className="text-secondary-start hover:text-secondary-end transition-colors p-2 rounded-lg hover:bg-white/5">
            {isLoginMode ? t('auth.switchToRegister') : t('auth.switchToLogin')}
          </button>
        </p>
      </motion.div>
    </div>
  );
};

export default AuthPage;