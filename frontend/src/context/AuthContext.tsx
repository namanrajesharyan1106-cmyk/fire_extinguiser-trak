import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../api/axios';

export interface User {
  id: number;
  employee_id?: string;
  name: string;
  email: string;
  department?: string;
  role: string;
  status: string;
  phone?: string;
  plant?: string;
  is_first_login?: boolean;
}

export interface AuthContextType {
  token: string | null;
  refreshToken: string | null;
  user: User | null;
  permissions: string[];
  plants: string[];
  selectedPlant: string | null;
  setSelectedPlant: (plant: string | null) => void;
  login: (accessToken: string, refreshToken: string, userData?: any) => Promise<void>;
  logout: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
  refetchUser: () => Promise<void>;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [refreshToken, setRefreshToken] = useState<string | null>(() => localStorage.getItem('refreshToken'));
  const [user, setUser] = useState<User | null>(() => {
    const u = localStorage.getItem('user');
    return u ? JSON.parse(u) : null;
  });
  const [permissions, setPermissions] = useState<string[]>(() => {
    const p = localStorage.getItem('permissions');
    return p ? JSON.parse(p) : [];
  });
  const [plants, setPlants] = useState<string[]>(() => {
    const pl = localStorage.getItem('plants');
    return pl ? JSON.parse(pl) : [];
  });
  const [selectedPlant, setSelectedPlantState] = useState<string | null>(() => {
    return localStorage.getItem('selectedPlant') || null;
  });
  const [loading, setLoading] = useState<boolean>(true);

  const setSelectedPlant = (plant: string | null) => {
    setSelectedPlantState(plant);
    if (plant) {
      localStorage.setItem('selectedPlant', plant);
    } else {
      localStorage.removeItem('selectedPlant');
    }
  };

  const fetchUserData = useCallback(async () => {
    try {
      const res = await api.get('/auth/me');
      const data = res.data?.data || res.data;
      if (data) {
        setUser(data);
        localStorage.setItem('user', JSON.stringify(data));
        const perms = data.permissions || [];
        setPermissions(perms);
        localStorage.setItem('permissions', JSON.stringify(perms));
        const userPlants = data.plants || [];
        setPlants(userPlants);
        localStorage.setItem('plants', JSON.stringify(userPlants));

        // Auto select first plant if user only has 1 assigned plant
        if (userPlants.length === 1 && !selectedPlant) {
          setSelectedPlant(userPlants[0]);
        }
      }
    } catch {
      // If fetching user fails, ignore or wait for retry
    } finally {
      setLoading(false);
    }
  }, [selectedPlant]);

  useEffect(() => {
    if (token) {
      fetchUserData();
    } else {
      setLoading(false);
    }
  }, [token, fetchUserData]);

  const login = async (accessToken: string, newRefreshToken: string, userData?: any) => {
    setToken(accessToken);
    setRefreshToken(newRefreshToken);
    localStorage.setItem('token', accessToken);
    localStorage.setItem('refreshToken', newRefreshToken);
    if (userData) {
      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));
    }
    await fetchUserData();
  };

  const logout = async () => {
    try {
      const curRefreshToken = localStorage.getItem('refreshToken');
      if (curRefreshToken) {
        await api.post('/auth/logout', { refresh_token: curRefreshToken });
      }
    } catch {
      // ignore
    } finally {
      setToken(null);
      setRefreshToken(null);
      setUser(null);
      setPermissions([]);
      setPlants([]);
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('user');
      localStorage.removeItem('permissions');
      localStorage.removeItem('plants');
      localStorage.removeItem('selectedPlant');
    }
  };

  const hasPermission = (permission: string): boolean => {
    if (user?.role === 'ADMIN') return true;
    return permissions.includes(permission);
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        refreshToken,
        user,
        permissions,
        plants,
        selectedPlant,
        setSelectedPlant,
        login,
        logout,
        hasPermission,
        refetchUser: fetchUserData,
        loading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
