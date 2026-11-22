import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Box, CircularProgress } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import theme from './theme/theme';
import MainLayout from './layouts/MainLayout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Locations from './pages/Locations';
import Assets from './pages/Assets';
import QRCodes from './pages/QRCodes';
import Inspections from './pages/Inspections';
import Maintenance from './pages/Maintenance';
import Reports from './pages/Reports';
import Users from './pages/Users';
import MasterData from './pages/MasterData';
import Settings from './pages/Settings';
import ChangePassword from './pages/ChangePassword';
import Forbidden from './pages/Forbidden';
import { AuthProvider, useAuth } from './context/AuthContext';
import RequirePermission from './components/RequirePermission';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 300_000, // 5 minutes
      gcTime: 900_000, // 15 minutes
      refetchOnWindowFocus: false,
    },
  },
});

// ─── Protected Route ──────────────────────────────────────────────────────────
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { token, user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress size={40} />
      </Box>
    );
  }

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (user?.is_first_login && location.pathname !== '/change-password') {
    return <Navigate to="/change-password" replace />;
  }

  return <>{children}</>;
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AuthProvider>
          <Router>
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/forbidden" element={<Forbidden />} />

              {/* Protected layout routes */}
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <MainLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<RequirePermission permission="view_dashboard"><Dashboard /></RequirePermission>} />
                <Route path="locations" element={<RequirePermission permission="view_locations"><Locations /></RequirePermission>} />
                <Route path="assets" element={<RequirePermission permission="view_assets"><Assets /></RequirePermission>} />
                <Route path="qrcodes" element={<RequirePermission permission="view_locations"><QRCodes /></RequirePermission>} />
                <Route path="inspections" element={<RequirePermission permission="view_inspections"><Inspections /></RequirePermission>} />
                <Route path="maintenance" element={<RequirePermission permission="view_maintenance"><Maintenance /></RequirePermission>} />
                <Route path="reports" element={<RequirePermission permission="view_reports"><Reports /></RequirePermission>} />
                <Route path="users" element={<RequirePermission permission="view_users"><Users /></RequirePermission>} />
                <Route path="master-data" element={<RequirePermission permission="manage_system_config"><MasterData /></RequirePermission>} />
                <Route path="settings" element={<RequirePermission permission="manage_system_config"><Settings /></RequirePermission>} />
                <Route path="change-password" element={<ChangePassword />} />
                {/* Catch-all → redirect to dashboard */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </Router>
          <ToastContainer position="bottom-right" autoClose={4000} />
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
