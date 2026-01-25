import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authApi, usersApi, setTokens, removeTokens, getRefreshToken, ApiErrorResponse } from '../services/api';
import type { UserResponse } from '../services/api';

interface User {
  id: number;
  email: string;
  name: string;
  isActive: boolean;
  createdAt: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  register: (email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  setUser: (user: User) => void;
  clearError: () => void;
  loadUser: () => Promise<void>;
}

// Fonction helper pour convertir UserResponse en User
const convertUserResponse = (userResponse: UserResponse): User => {
  return {
    id: userResponse.id,
    email: userResponse.email,
    name: userResponse.email.split('@')[0].charAt(0).toUpperCase() + userResponse.email.split('@')[0].slice(1),
    isActive: userResponse.is_active,
    createdAt: userResponse.created_at,
  };
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });
        
        try {
          // Appel à l'API de connexion
          const tokens = await authApi.login({ email, password });
          
          // Stocker les tokens
          setTokens(tokens.access_token, tokens.refresh_token);
          
          // Récupérer les informations de l'utilisateur
          const userResponse = await usersApi.getMe();
          const user = convertUserResponse(userResponse);

          set({ 
            user, 
            isAuthenticated: true, 
            isLoading: false,
            error: null,
          });
          
          return true;
        } catch (error) {
          const errorMessage = error instanceof ApiErrorResponse 
            ? error.detail 
            : 'Erreur lors de la connexion';
          
          set({ 
            isLoading: false, 
            error: errorMessage,
            isAuthenticated: false,
            user: null,
          });
          
          return false;
        }
      },

      register: async (email: string, password: string) => {
        set({ isLoading: true, error: null });
        
        try {
          // Appel à l'API d'inscription
          const tokens = await authApi.register({ email, password });
          
          // Stocker les tokens
          setTokens(tokens.access_token, tokens.refresh_token);
          
          // Récupérer les informations de l'utilisateur
          const userResponse = await usersApi.getMe();
          const user = convertUserResponse(userResponse);

          set({ 
            user, 
            isAuthenticated: true, 
            isLoading: false,
            error: null,
          });
          
          return true;
        } catch (error) {
          const errorMessage = error instanceof ApiErrorResponse 
            ? error.detail 
            : 'Erreur lors de l\'inscription';
          
          set({ 
            isLoading: false, 
            error: errorMessage,
            isAuthenticated: false,
            user: null,
          });
          
          return false;
        }
      },

      logout: async () => {
        set({ isLoading: true });
        
        try {
          const refreshToken = getRefreshToken();
          if (refreshToken) {
            // Appel à l'API de déconnexion pour invalider le refresh token
            await authApi.logout(refreshToken);
          }
        } catch (error) {
          console.warn('Erreur lors de la déconnexion côté serveur:', error);
        } finally {
          // Supprimer les tokens et réinitialiser l'état
          removeTokens();
          set({ 
            user: null, 
            isAuthenticated: false, 
            isLoading: false,
            error: null,
          });
        }
      },

      setUser: (user: User) => {
        set({ user, isAuthenticated: true });
      },

      clearError: () => {
        set({ error: null });
      },

      loadUser: async () => {
        const accessToken = localStorage.getItem('access_token');
        
        if (!accessToken) {
          set({ isAuthenticated: false, user: null });
          return;
        }

        set({ isLoading: true });
        
        try {
          // Récupérer les informations de l'utilisateur
          const userResponse = await usersApi.getMe();
          const user = convertUserResponse(userResponse);

          set({ 
            user, 
            isAuthenticated: true, 
            isLoading: false,
            error: null,
          });
        } catch (error) {
          // Si l'utilisateur ne peut pas être chargé, supprimer les tokens
          removeTokens();
          set({ 
            user: null, 
            isAuthenticated: false, 
            isLoading: false,
            error: null,
          });
        }
      },
    }),
    {
      name: 'auth-storage',
      // Ne persister que les informations utilisateur, pas les tokens (stockés séparément)
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
