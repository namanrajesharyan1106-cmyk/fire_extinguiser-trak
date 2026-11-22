import React from 'react';
import { useAuth } from '../context/AuthContext';
import Forbidden from '../pages/Forbidden';
import { Box, CircularProgress } from '@mui/material';

interface RequirePermissionProps {
  permission: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const RequirePermission: React.FC<RequirePermissionProps> = ({
  permission,
  children,
  fallback,
}) => {
  const { hasPermission, loading } = useAuth();

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress size={36} />
      </Box>
    );
  }

  if (!hasPermission(permission)) {
    return <>{fallback !== undefined ? fallback : <Forbidden />}</>;
  }

  return <>{children}</>;
};

export default RequirePermission;
