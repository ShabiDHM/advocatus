// FILE: /home/user/advocatus-frontend/src/context/AuthContext.tsx
// PHOENIX PROTOCOL MODIFICATION 1.1 (TYPO FIX)
// 1. CRITICAL FIX: Corrected a typo in the JSX closing tag from </Auth.Provider>
//    to </AuthContext.Provider>, resolving the compilation errors.

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { User, LoginRequest, RegisterRequest } from '../data/types';
import { apiService } from '../services/api';
import { jwtDecode } from 'jwt-decode';

interface DecodedToken {
    sub: string;
    id: string;
    exp: number;
    role?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);
const LOCAL_STORAGE_TOKEN_KEY = 'jwtToken';

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem(LOCAL_STORAGE_TOKEN_KEY);
    setUser(null);
  }, []);

  // Set the logout handler once when the component mounts
  useEffect(() => {
    apiService.setLogoutHandler(logout);
  }, [logout]);

  const setUserFromToken = useCallback(async (token: string) => {
    try {
      const fullUser = await apiService.fetchUserProfile();
      const decoded = jwtDecode<DecodedToken>(token);
      const normalizedRole = (decoded.role || fullUser.role || 'STANDARD').toUpperCase() as User['role'];
      setUser({ ...fullUser, token, role: normalizedRole });
    } catch (error) {
      console.error("Failed to set user from token.", error);
      logout(); // If fetching profile fails, ensure logout
    }
  }, [logout]);

  // This useEffect now orchestrates the entire session validation on startup.
  useEffect(() => {
    const validateSession = async () => {
      const token = localStorage.getItem(LOCAL_STORAGE_TOKEN_KEY);
      if (!token) {
        try {
            const response = await apiService.refreshAccessToken();
            await setUserFromToken(response.access_token);
        } catch {
            setUser(null);
        }
      } else {
        await setUserFromToken(token);
      }
      setIsLoading(false);
    };

    validateSession();
  }, [setUserFromToken]);

  const handleAuthSuccess = async (token: string) => {
    localStorage.setItem(LOCAL_STORAGE_TOKEN_KEY, token);
    await setUserFromToken(token);
  };

  const login = async (data: LoginRequest) => {
    setIsLoading(true);
    try {
      const response = await apiService.login(data);
      await handleAuthSuccess(response.access_token);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: RegisterRequest) => {
    await apiService.register(data);
  };

  if (isLoading) {
    return <div className="min-h-screen bg-background-dark flex items-center justify-center"></div>;
  }

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, register, logout, isLoading }}>
      {children}
    </AuthContext.Provider> // <-- PHOENIX PROTOCOL FIX: Corrected typo here
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) { throw new Error('useAuth must be used within an AuthProvider'); }
  return context;
};

export default useAuth;