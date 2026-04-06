import { useState } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuthStore } from '../../stores/authStore';

const Header = () => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, logout } = useAuthStore();

  type PublicNavTarget = 'home' | 'features' | 'about';

  const publicNavItems: { label: string; target: PublicNavTarget }[] = [
    { label: 'Accueil', target: 'home' },
    { label: 'Fonctionnalités', target: 'features' },
    { label: 'À propos', target: 'about' },
  ];

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const scrollTop = (behavior: ScrollBehavior = 'smooth') => {
    document.getElementById('scroll-container')?.scrollTo({ top: 0, behavior });
  };

  const handleNavigation = (target: PublicNavTarget) => {
    if (target === 'home') {
      if (location.pathname === '/') {
        scrollTop();
        navigate('/', { replace: true });
      } else {
        navigate('/');
      }
      setMobileOpen(false);
      return;
    }
    if (target === 'features') {
      if (location.pathname !== '/') {
        navigate({ pathname: '/', hash: '#features' });
      } else {
        if (location.hash !== '#features') {
          navigate({ pathname: '/', hash: '#features' });
        }
        window.setTimeout(() => {
          document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' });
        }, 80);
      }
      setMobileOpen(false);
      return;
    }
    navigate('/about');
    setMobileOpen(false);
  };

  const navButtonActive = (target: PublicNavTarget) => {
    if (target === 'about') return location.pathname === '/about';
    if (target === 'home') {
      return location.pathname === '/' && location.hash !== '#features';
    }
    return location.pathname === '/' && location.hash === '#features';
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <AppBar position="fixed" elevation={0}>
      <Toolbar sx={{ justifyContent: 'space-between', py: 1 }}>
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              cursor: 'pointer',
              gap: 1.5,
            }}
            onClick={() => {
              if (location.pathname === '/') {
                scrollTop();
                navigate('/', { replace: true });
              } else {
                navigate('/');
              }
            }}
          >
            <Box
              component="img"
              src="/logo-avatar.png"
              alt="MindMapCompanion Logo"
              sx={{
                width: 44,
                height: 44,
                borderRadius: '12px',
                objectFit: 'cover',
              }}
            />
            <Typography
              variant="h5"
              sx={{
                fontWeight: 800,
                color: '#00D9FF',
                letterSpacing: '-0.02em',
              }}
            >
              MindMapCompanion
            </Typography>
          </Box>
        </motion.div>

        {!isMobile && !isAuthenticated && (
          <Box sx={{ display: 'flex', gap: 1 }}>
            {publicNavItems.map((item, index) => (
              <motion.div
                key={item.label}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
              >
                <Button
                  onClick={() => handleNavigation(item.target)}
                  sx={{
                    color: navButtonActive(item.target) ? 'primary.main' : 'text.secondary',
                    '&:hover': { color: 'primary.light', background: 'transparent' },
                  }}
                >
                  {item.label}
                </Button>
              </motion.div>
            ))}
          </Box>
        )}

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
        >
          {isAuthenticated ? (
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                variant="outlined"
                onClick={() => navigate('/dashboard')}
                sx={{ display: { xs: 'none', sm: 'flex' } }}
              >
                Dashboard
              </Button>
              <Button variant="contained" onClick={handleLogout}>
                Déconnexion
              </Button>
            </Box>
          ) : (
            <Box sx={{ display: 'flex', gap: 2 }}>
              {isMobile ? (
                <IconButton
                  color="inherit"
                  aria-label="menu"
                  onClick={handleDrawerToggle}
                  sx={{ color: 'primary.main' }}
                >
                  <MenuIcon />
                </IconButton>
              ) : (
                <Button
                  variant="outlined"
                  onClick={() => navigate('/login')}
                >
                  Connexion
                </Button>
              )}
            </Box>
          )}
        </motion.div>
      </Toolbar>

      <Drawer
        anchor="right"
        open={mobileOpen}
        onClose={handleDrawerToggle}
        PaperProps={{
          sx: {
            width: 280,
            backgroundColor: '#0A0E17',
            borderLeft: '1px solid rgba(0, 217, 255, 0.2)',
          },
        }}
      >
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'flex-end' }}>
          <IconButton onClick={handleDrawerToggle} sx={{ color: 'primary.main' }}>
            <CloseIcon />
          </IconButton>
        </Box>
        <List>
          {publicNavItems.map((item) => (
            <ListItem key={item.label} disablePadding>
              <ListItemButton onClick={() => handleNavigation(item.target)}>
                <ListItemText
                  primary={item.label}
                  sx={{ color: 'text.primary' }}
                />
              </ListItemButton>
            </ListItem>
          ))}
          <ListItem disablePadding>
            <ListItemButton
              onClick={() => {
                navigate('/login');
                setMobileOpen(false);
              }}
            >
              <ListItemText primary="Connexion" sx={{ color: 'primary.main' }} />
            </ListItemButton>
          </ListItem>
        </List>
      </Drawer>
    </AppBar>
  );
};

export default Header;
