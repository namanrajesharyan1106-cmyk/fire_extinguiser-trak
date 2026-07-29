import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#0052cc', // Industrial Blue
    },
    secondary: {
      main: '#42526E',
    },
    success: {
      main: '#36B37E', // Green
    },
    warning: {
      main: '#FFAB00', // Orange
    },
    error: {
      main: '#FF5630', // Red
    },
    background: {
      default: '#F4F5F7',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#172B4D',
      secondary: '#5E6C84',
    }
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: { fontSize: '2rem', fontWeight: 600 },
    h2: { fontSize: '1.75rem', fontWeight: 600 },
    h3: { fontSize: '1.5rem', fontWeight: 600 },
    h4: { fontSize: '1.25rem', fontWeight: 600 },
    h5: { fontSize: '1.1rem', fontWeight: 600 },
    h6: { fontSize: '1rem', fontWeight: 600 },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 4,
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        variant: 'outlined',
        fullWidth: true,
        InputLabelProps: {
          shrink: true, // IMPORTANT: Fixes overlapping label bug
        }
      },
      styleOverrides: {
        root: {
          marginBottom: 16,
        }
      }
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
        }
      }
    }
  },
});

export default theme;
