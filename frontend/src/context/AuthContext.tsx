// FILE: src/context/AuthContext.tsx
// PHOENIX PROTOCOL - REVISED AUTHENTICATION CONTEXT
// 1. ARCHITECTURE: Aligns with the automatic, cookie-based token refresh mechanism in api.ts.
// 2. STATELESS CLIENT: Removes all manual token management and localStorage usage for the JWT.
// 3. ROBUSTNESS: Initializes the app by fetching the user profile, letting the apiService interceptor handle session restoration.

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { User, LoginRequest, RegisterRequest } from '../data/types';
import { apiService } from '../services/api';
import { Loader2 } from 'lucide-react';

// The access token is no longer stored here; it's managed in-memory by api.ts
type AuthUser = User;

interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // PHOENIX FIX: The logout function is now simpler. It tells the apiService to clear
  // its in-memory token and then clears the local user state.
  const logout = useCallback(() => {
    apiService.logout(); // Clears the in-memory access token
    setUser(null);
  }, []);

  // The logout handler is set up to allow the apiService to trigger a logout
  // if a token refresh fails permanently.
  useEffect(() => {
    apiService.setLogoutHandler(logout);
  }, [logout]);

  // PHOENIX FIX: Revised initialization logic.
  // We no longer manually refresh the token. We simply ask for the user's profile.
  // The apiService interceptor will automatically handle refreshing the access token
  // using the secure cookie if a session is active.
  useEffect(() => {
    const initializeApp = async () => {
      setIsLoading(true);
      try {
        // This call will succeed if the user has a valid refresh token cookie.
        // The interceptor in api.ts will handle the entire refresh flow automatically.
        const fullUser = await apiService.fetchUserProfile();
        setUser(fullUser);
      } catch (error) {
        // If this fails, it means there's no valid session.
        // The user is not logged in. No further action needed.
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initializeApp();
  }, []); // Run only once on app startup

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const loginPayload: LoginRequest = { 
          username: email, 
          password: password 
      };

      // apiService.login handles setting the in-memory access token
      await apiService.login(loginPayload);
      
      // After a successful login, fetch the full user profile
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