// FILE: src/context/AuthContext.tsx

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

// Extended User type that includes the token, strictly for AuthContext usage
type AuthUser = User & { token?: string };

interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);
const LOCAL_STORAGE_TOKEN_KEY = 'jwtToken';

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem(LOCAL_STORAGE_TOKEN_KEY);
    setUser(null);
  }, []);

  // Set the logout handler once when the component mounts
  useEffect(() => {
    apiService.setLogoutHandler(logout);
  }, [logout]);

  useEffect(() => {
    const initializeApp = async () => {
      try {
        const response = await apiService.refreshAccessToken();
        const { access_token } = response;
        localStorage.setItem(LOCAL_STORAGE_TOKEN_KEY, access_token);

        const fullUser = await apiService.fetchUserProfile();
        const decoded = jwtDecode<DecodedToken>(access_token);
        const normalizedRole = (decoded.role || fullUser.role || 'STANDARD').toUpperCase() as User['role'];
        
        setUser({ ...fullUser, token: access_token, role: normalizedRole });

      } catch (error) {
        console.error("Session validation failed. User is not logged in.", error);
        logout();
      } finally {
        setIsLoading(false);
      }
    };

    initializeApp();
  }, [logout]);

  const login = async (data: LoginRequest) => {
    setIsLoading(true);
    try {
      const response = await apiService.login(data);
      const { access_token } = response;
      localStorage.setItem(LOCAL_STORAGE_TOKEN_KEY, access_token);
      
      const fullUser = await apiService.fetchUserProfile();
      const decoded = jwtDecode<DecodedToken>(access_token);
      const normalizedRole = (decoded.role || fullUser.role || 'STANDARD').toUpperCase() as User['role'];
      
      setUser({ ...fullUser, token: access_token, role: normalizedRole });

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
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) { throw new Error('useAuth must be used within an AuthProvider'); }
  return context;
};

export default useAuth;