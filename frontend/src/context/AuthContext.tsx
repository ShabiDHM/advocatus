// FILE: src/context/AuthContext.tsx
// PHOENIX PROTOCOL - AUTH CONTEXT V2.1 (PATH AWARENESS)
// 1. FIX: The 'initializeApp' function now checks the window location.
// 2. LOGIC: If the path is '/mobile-upload/...', it skips the authentication check.
// 3. STATUS: This prevents the failed token refresh on the mobile page from redirecting the user.

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { User, LoginRequest, RegisterRequest } from '../data/types';
import { apiService } from '../services/api';
import { Loader2 } from 'lucide-react';

type AuthUser = User;

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
      const fullUser = await apiService.fetchUserProfile();
      setUser(fullUser);
    } catch (error) {
      console.error("Failed to refresh user, logging out.", error);
      logout(); // Logout if refresh fails
    }
  }, [logout]);

  useEffect(() => {
    apiService.setLogoutHandler(logout);
  }, [logout]);

  // Proactive Initialization
  useEffect(() => {
    let isMounted = true;

    const initializeApp = async () => {
      // PHOENIX FIX: If we are on the mobile upload page, do not attempt to authenticate.
      if (window.location.pathname.startsWith('/mobile-upload/')) {
        if (isMounted) setIsLoading(false);
        return;
      }

      try {
        const refreshed = await apiService.refreshToken();
        
        if (refreshed) {
            const fullUser = await apiService.fetchUserProfile();
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
      const fullUser = await apiService.fetchUserProfile();
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