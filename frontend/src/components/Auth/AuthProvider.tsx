import { useEffect, useState } from 'react';
import { CircularProgress, Box } from '@mui/material';
import { useAuthStore } from '../../stores/authStore';

interface AuthProviderProps {
  children: React.ReactNode;
}

/**
 * Composant qui charge l'utilisateur au démarrage si un token existe
 */
const AuthProvider = ({ children }: AuthProviderProps) => {
  const [isInitializing, setIsInitializing] = useState(true);
  const { loadUser, isAuthenticated } = useAuthStore();

  useEffect(() => {
    const initializeAuth = async () => {
      const accessToken = localStorage.getItem('access_token');
      
      if (accessToken) {
        // Si un token existe, charger l'utilisateur
        try {
          await loadUser();
        } catch (error) {
          console.error('Erreur lors du chargement de l\'utilisateur:', error);
        }
      }
      
      setIsInitializing(false);
    };

    initializeAuth();
  }, [loadUser]);

  // Afficher un loader pendant l'initialisation
  if (isInitializing) {
    return (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          backgroundColor: '#0A0E17',
        }}
      >
        <Box sx={{ textAlign: 'center' }}>
          <CircularProgress size={60} sx={{ color: '#00D9FF', mb: 2 }} />
        </Box>
      </Box>
    );
  }

  return <>{children}</>;
};

export default AuthProvider;
