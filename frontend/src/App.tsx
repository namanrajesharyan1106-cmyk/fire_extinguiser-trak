import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
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
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />

            {/* Protected layout routes */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <MainLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="locations" element={<Locations />} />
              <Route path="assets" element={<Assets />} />
              <Route path="qrcodes" element={<QRCodes />} />
              <Route path="inspections" element={<Inspections />} />
              <Route path="maintenance" element={<Maintenance />} />
              <Route path="reports" element={<Reports />} />
              <Route path="users" element={<Users />} />
              {/* Catch-all → redirect to dashboard */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </Router>
        <ToastContainer position="bottom-right" autoClose={4000} />
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
