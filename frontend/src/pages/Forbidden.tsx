import React from 'react';
import { Box, Typography, Button, Paper } from '@mui/material';
import { ShieldAlert, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const Forbidden: React.FC = () => {
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '70vh',
        p: 3,
      }}
    >
      <Paper
        elevation={0}
        sx={{
          p: 5,
          maxWidth: 480,
          textAlign: 'center',
          borderRadius: '16px',
          border: '1px solid #E2E8F0',
          backgroundColor: '#FFFFFF',
        }}
      >
        <Box
          sx={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 72,
            height: 72,
            borderRadius: '50%',
            backgroundColor: '#FEE2E2',
            color: '#DC2626',
            mb: 3,
          }}
        >
          <ShieldAlert size={36} />
        </Box>
        <Typography variant="h5" fontWeight={700} color="#1E293B" gutterBottom>
          Access Denied (403)
        </Typography>
        <Typography variant="body2" color="#64748B" sx={{ mb: 4, lineHeight: 1.6 }}>
          You do not have the required permissions to view this module or perform this action.
          Please contact your administrator if you believe this is in error.
        </Typography>
        <Button
          variant="contained"
          startIcon={<ArrowLeft size={18} />}
          onClick={() => navigate('/')}
          sx={{
            textTransform: 'none',
            fontWeight: 600,
            borderRadius: '8px',
            backgroundColor: '#0F172A',
            '&:hover': { backgroundColor: '#1E293B' },
          }}
        >
          Return to Dashboard
        </Button>
      </Paper>
    </Box>
  );
};

export default Forbidden;
