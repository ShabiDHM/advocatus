// FILE: src/context/AuthContext.tsx
import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { User, LoginRequest, RegisterRequest } from '../data/types';
import { apiService } from '../services/api';
import { jwtDecode } from 'jwt-decode';
import { Loader2 } from 'lucide-react';

interface DecodedToken {
    sub: string;
    id: string;
    exp: number;
    role?: string;
}

type AuthUser = User & { token?: string };

interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
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
        
        // PHOENIX FIX: Prioritize the API response as the source of truth for the user's role.
        const normalizedRole = (fullUser.role || decoded.role || 'STANDARD').toUpperCase() as User['role'];
        
        setUser({ ...fullUser, token: access_token, role: normalizedRole });

      } catch (error) {
        // Silent fail: user is simply not logged in
        logout();
      } finally {
        setIsLoading(false);
      }
    };

    initializeApp();
  }, [logout]);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const loginPayload: LoginRequest = { 
          username: email, 
          password: password 
      };

      const response = await apiService.login(loginPayload);
      const { access_token } = response;
      localStorage.setItem(LOCAL_STORAGE_TOKEN_KEY, access_token);
      
      const fullUser = await apiService.fetchUserProfile();
      const decoded = jwtDecode<DecodedToken>(access_token);

      // PHOENIX FIX: Prioritize the API response as the source of truth for the user's role.
      const normalizedRole = (fullUser.role || decoded.role || 'STANDARD').toUpperCase() as User['role'];
      
      setUser({ ...fullUser, token: access_token, role: normalizedRole });

    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: RegisterRequest) => {
    await apiService.register(data);
  };

  if (isLoading) {
    return (
        <div className="min-h-screen bg-background-dark flex items-center justify-center">
            <div className="text-center">
                <Loader2 className="h-12 w-12 text-primary-start animate-spin mx-auto mb-4" />
                <h2 className="text-xl font-bold text-text-primary">Juristi AI</h2>
                <p className="text-sm text-text-secondary mt-2">Duke u ngarkuar...</p>
            </div>
        </div>
    );
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

export default AuthContext;