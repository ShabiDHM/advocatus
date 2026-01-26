// FILE: src/context/AuthContext.tsx
// PHOENIX PROTOCOL - AUTH CONTEXT V2.3 (TYPE CONFLICT RESOLUTION)
// 1. FIXED: Used 'Omit' to resolve type conflicts between base 'User' and 'AuthUser'.
// 2. FIXED: Added explicit casting 'as AuthUser' to ensure state updates are accepted.
// 3. STATUS: Resolves the 'type never' and 'not assignable' errors in VS Code.

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { User, LoginRequest, RegisterRequest } from '../data/types';
import { apiService } from '../services/api';
import { Loader2 } from 'lucide-react';

// PHOENIX FIX: We Omit conflicting fields from the base User type before overriding them.
// This prevents the 'intersection reduced to never' error.
type AuthUser = Omit<User, 'subscription_tier' | 'account_type' | 'product_plan'> & {
    subscription_tier?: 'BASIC' | 'PRO';
    account_type?: 'SOLO' | 'ORGANIZATION';
    product_plan?: string;
};

interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    apiService.logout(); 
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      // Cast the response to AuthUser to satisfy the specific string literals
      const fullUser = await apiService.fetchUserProfile() as AuthUser;
      setUser(fullUser);
    } catch (error) {
      console.error("Failed to refresh user, logging out.", error);
      logout();
    }
  }, [logout]);

  useEffect(() => {
    apiService.setLogoutHandler(logout);
  }, [logout]);

  useEffect(() => {
    let isMounted = true;

    const initializeApp = async () => {
      // Mobile Upload Path Check
      if (window.location.pathname.startsWith('/mobile-upload/')) {
        if (isMounted) setIsLoading(false);
        return;
      }

      try {
        const refreshed = await apiService.refreshToken();
        
        if (refreshed) {
            // Cast to AuthUser
            const fullUser = await apiService.fetchUserProfile() as AuthUser;
            if (isMounted) setUser(fullUser);
        } else {
            if (isMounted) setUser(null);
        }
      } catch (error) {
        console.error("Session initialization failed:", error);
        if (isMounted) setUser(null);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    initializeApp();
    return () => { isMounted = false; };
  }, []); 

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const loginPayload: LoginRequest = { 
          username: email, 
          password: password 
      };

      await apiService.login(loginPayload);
      // Cast to AuthUser
      const fullUser = await apiService.fetchUserProfile() as AuthUser;
      setUser(fullUser);

    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: RegisterRequest) => {
    await apiService.register(data);
  };

  if (isLoading) {
    return (
        <div className="min-h-screen bg-gray-900 flex items-center justify-center">
            <div className="text-center">
                <Loader2 className="h-12 w-12 text-blue-500 animate-spin mx-auto mb-4" />
                <h2 className="text-xl font-bold text-white">Juristi AI</h2>
                <p className="text-sm text-gray-400 mt-2">Duke u ngarkuar...</p>
            </div>
        </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, register, logout, isLoading, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) { throw new Error('useAuth must be used within an AuthProvider'); }
  return context;
};

export default AuthContext;