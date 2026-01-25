import { useState } from 'react';
import {
  Box,
  Container,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  InputAdornment,
  IconButton,
  Link,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Email as EmailIcon,
  Lock as LockIcon,
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { useNotification } from '../../hooks/useNotification';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState('');

  const navigate = useNavigate();
  const { login, isLoading, error: storeError, clearError } = useAuthStore();
  const { showSuccess, showError } = useNotification();

  // Combiner les erreurs locales et du store
  const error = localError || storeError || '';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError('');
    clearError();

    if (!email || !password) {
      setLocalError('Veuillez remplir tous les champs');
      return;
    }

    // Validation basique de l'email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setLocalError('Veuillez entrer un email valide');
      return;
    }

    try {
      const success = await login(email, password);
      
      if (success) {
        showSuccess('Connexion réussie');
        navigate('/dashboard');
      } else {
        showError(storeError || 'Erreur lors de la connexion');
      }
    } catch (err) {
      // L'erreur est déjà gérée par le store
      console.error('Erreur lors de la connexion:', err);
      showError(storeError || 'Erreur lors de la connexion');
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        position: 'relative',
        py: 4,
      }}
    >
      {/* Background Effects */}
      <Box
        sx={{
          position: 'absolute',
          top: '20%',
          left: '10%',
          width: 400,
          height: 400,
          borderRadius: '50%',
          backgroundColor: 'rgba(0, 217, 255, 0.05)',
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }}
      />
      <Box
        sx={{
          position: 'absolute',
          bottom: '20%',
          right: '10%',
          width: 350,
          height: 350,
          borderRadius: '50%',
          backgroundColor: 'rgba(255, 107, 157, 0.03)',
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }}
      />

      <Container maxWidth="sm">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <Card
            sx={{
              p: { xs: 3, sm: 5 },
              backgroundColor: '#12182B',
            }}
          >
            <CardContent sx={{ p: 0 }}>
              {/* Logo */}
              <Box sx={{ textAlign: 'center', mb: 4 }}>
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                >
                  <Box
                    component="img"
                    src="/logo-avatar.png"
                    alt="MindMapCompanion Logo"
                    sx={{
                      width: 70,
                      height: 70,
                      borderRadius: '18px',
                      objectFit: 'cover',
                      mx: 'auto',
                      mb: 2,
                      boxShadow: '0 8px 32px rgba(0, 217, 255, 0.4)',
                    }}
                  />
                  <Typography
                    variant="h5"
                    sx={{
                      fontWeight: 800,
                      color: '#00D9FF',
                      letterSpacing: '-0.02em',
                      mb: 3,
                    }}
                  >
                    MindMapCompanion
                  </Typography>
                </motion.div>
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
                  Bienvenue
                </Typography>
                <Typography variant="body1" color="text.secondary">
                  Connectez-vous pour accéder à votre espace
                </Typography>
              </Box>

              {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                  {error}
                </Alert>
              )}

              {/* Form */}
              <Box component="form" onSubmit={handleSubmit}>
                <TextField
                  fullWidth
                  label="Email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  sx={{ mb: 3 }}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <EmailIcon sx={{ color: 'text.secondary' }} />
                      </InputAdornment>
                    ),
                  }}
                />

                <TextField
                  fullWidth
                  label="Mot de passe"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  sx={{ mb: 2 }}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <LockIcon sx={{ color: 'text.secondary' }} />
                      </InputAdornment>
                    ),
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => setShowPassword(!showPassword)}
                          edge="end"
                          sx={{ color: 'text.secondary' }}
                        >
                          {showPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />

                <Box sx={{ textAlign: 'right', mb: 3 }}>
                  <Link
                    href="#"
                    underline="hover"
                    sx={{ color: 'primary.main', fontSize: '0.875rem' }}
                  >
                    Mot de passe oublié ?
                  </Link>
                </Box>

                <Button
                  fullWidth
                  variant="contained"
                  type="submit"
                  size="large"
                  disabled={isLoading}
                  sx={{ py: 1.5 }}
                >
                  {isLoading ? (
                    <CircularProgress size={24} color="inherit" />
                  ) : (
                    'Se connecter'
                  )}
                </Button>
              </Box>
            </CardContent>
          </Card>
        </motion.div>
      </Container>
    </Box>
  );
};

export default Login;
