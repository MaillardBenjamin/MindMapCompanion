import { createTheme, alpha } from '@mui/material/styles';

declare module '@mui/material/styles' {
  interface Palette {
    gradient: {
      primary: string;
      secondary: string;
      dark: string;
    };
  }
  interface PaletteOptions {
    gradient?: {
      primary?: string;
      secondary?: string;
      dark?: string;
    };
  }
}

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#00D9FF',
      light: '#5CE1FF',
      dark: '#00A8C7',
      contrastText: '#0A0E17',
    },
    secondary: {
      main: '#FF6B9D',
      light: '#FF9BC1',
      dark: '#CC4D7A',
    },
    background: {
      default: '#0A0E17',
      paper: '#12182B',
    },
    text: {
      primary: '#E8EDF5',
      secondary: '#8B95A8',
    },
    success: {
      main: '#4ADE80',
    },
    warning: {
      main: '#FBBF24',
    },
    error: {
      main: '#FF5757',
    },
    gradient: {
      primary: '#00D9FF',
      secondary: '#FF6B9D',
      dark: '#0A0E17',
    },
  },
  typography: {
    fontFamily: '"Outfit", "Poppins", "Segoe UI", sans-serif',
    h1: {
      fontWeight: 800,
      letterSpacing: '-0.02em',
    },
    h2: {
      fontWeight: 700,
      letterSpacing: '-0.01em',
    },
    h3: {
      fontWeight: 600,
    },
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 500,
    },
    h6: {
      fontWeight: 500,
    },
    button: {
      fontWeight: 600,
      textTransform: 'none',
    },
  },
  shape: {
    borderRadius: 16,
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#0A0E17',
          minHeight: '100vh',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          padding: '12px 28px',
          fontSize: '1rem',
          transition: 'all 0.3s ease',
        },
        contained: {
          backgroundColor: '#00D9FF',
          boxShadow: '0 4px 20px rgba(0, 217, 255, 0.3)',
          '&:hover': {
            backgroundColor: '#5CE1FF',
            boxShadow: '0 8px 30px rgba(0, 217, 255, 0.5)',
            transform: 'translateY(-2px)',
          },
        },
        outlined: {
          borderColor: '#00D9FF',
          borderWidth: 2,
          '&:hover': {
            borderWidth: 2,
            background: alpha('#00D9FF', 0.1),
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: '#12182B',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(0, 217, 255, 0.1)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 12,
            '& fieldset': {
              borderColor: 'rgba(139, 149, 168, 0.3)',
            },
            '&:hover fieldset': {
              borderColor: '#00D9FF',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#00D9FF',
              boxShadow: '0 0 20px rgba(0, 217, 255, 0.2)',
            },
          },
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          background: 'rgba(10, 14, 23, 0.8)',
          backdropFilter: 'blur(20px)',
          borderBottom: '1px solid rgba(0, 217, 255, 0.1)',
        },
      },
    },
  },
});

export default theme;
