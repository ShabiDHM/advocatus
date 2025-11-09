// FILE: /home/user/advocatus-frontend/src/context/AuthContext.tsx
// PHOENIX PROTOCOL MODIFICATION 28.0 (DEFINITIVE AUTHENTICATION CURE):
// 1. DISEASE IDENTIFIED: The original startup logic had a fatal flaw. When a token was expired,
//    it would correctly refresh it via an interceptor, but then a poorly placed try/catch
//    block would interpret the initial failure as a fatal error, triggering a logout() call
//    that immediately deleted the newly acquired token, causing a race condition where
//    the WebSocket would always fail to connect.
// 2. THE CURE - LINEAR STARTUP LOGIC: The entire session validation useEffect has been rewritten.
//    It now follows a single, authoritative path: it ALWAYS attempts to refresh the token on load.
//    This is the most reliable way to establish a session.
// 3. ATOMIC STATE UPDATES: If the refresh succeeds, it sets the token, fetches the user profile,
//    and sets the user state. If any part fails, it logs the user out.
// 4. GUARANTEED "READY" SIGNAL: The 'setIsLoading(false)' call is now in a 'finally' block,
//    guaranteeing that it is the VERY LAST thing to happen, after the authentication state
//    is definitively resolved. This completely eliminates the race condition.

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

  // This is the core startup logic, rewritten for robustness.
  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Step 1: ALWAYS try to refresh the token. This is the single source of truth for a session.
        const response = await apiService.refreshAccessToken();
        const { access_token } = response;
        localStorage.setItem(LOCAL_STORAGE_TOKEN_KEY, access_token);

        // Step 2: With a guaranteed valid token, fetch the user's profile.
        const fullUser = await apiService.fetchUserProfile();
        const decoded = jwtDecode<DecodedToken>(access_token);
        const normalizedRole = (decoded.role || fullUser.role || 'STANDARD').toUpperCase() as User['role'];
        
        // Step 3: Set the user state. The session is now valid.
        setUser({ ...fullUser, token: access_token, role: normalizedRole });

      } catch (error) {
        // If ANY of the above fails, the session is invalid.
        console.error("Session validation failed. User is not logged in.", error);
        logout(); // Ensure we are fully logged out.
      } finally {
        // Step 4: GUARANTEE that we signal the app is ready only after auth is resolved.
        setIsLoading(false);
      }
    };

    initializeApp();
  }, [logout]); // Depends only on logout, runs once on mount.

  const login = async (data: LoginRequest) => {
    setIsLoading(true);
    try {
      const response = await apiService.login(data);
      const { access_token } = response;
      localStorage.setItem(LOCAL_STORAGE_TOKEN_KEY, access_token);
      
      // After login, fetch profile to populate user state
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