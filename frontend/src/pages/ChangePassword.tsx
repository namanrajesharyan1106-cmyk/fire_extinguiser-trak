import React, { useState } from 'react';
import {
  Box,
  Card,
  Typography,
  TextField,
  Button,
  Alert,
  IconButton,
  InputAdornment,
  CircularProgress,
} from '@mui/material';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Lock } from 'lucide-react';
import { toast } from 'react-toastify';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';

const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, 'Current password is required'),
    new_password: z
      .string()
      .min(8, 'Password must be at least 8 characters long')
      .regex(/[A-Z]/, 'Must contain at least one uppercase letter')
      .regex(/[a-z]/, 'Must contain at least one lowercase letter')
      .regex(/[0-9]/, 'Must contain at least one digit')
      .regex(/[^A-Za-z0-9]/, 'Must contain at least one special character'),
    confirm_password: z.string().min(1, 'Please confirm your new password'),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
  });

type ChangePasswordForm = z.infer<typeof changePasswordSchema>;

export const ChangePassword: React.FC = () => {
  const navigate = useNavigate();
  const { user, refetchUser } = useAuth();
  const [error, setError] = useState<string>('');
  const [showCurrent, setShowCurrent] = useState<boolean>(false);
  const [showNew, setShowNew] = useState<boolean>(false);
  const [showConfirm, setShowConfirm] = useState<boolean>(false);

  const isFirstLogin = Boolean(user?.is_first_login);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordForm>({
    resolver: zodResolver(changePasswordSchema),
  });

  const onSubmit = async (data: ChangePasswordForm) => {
    try {
      setError('');
      await api.post('/auth/change-password', {
        current_password: data.current_password,
        new_password: data.new_password,
      });

      toast.success('Password changed successfully! Welcome to FireSafety Pro.');
      await refetchUser();
      navigate('/');
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail?.message ||
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        'Failed to change password. Please check your current password.';
      setError(msg);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#F8FAFC',
        p: 2,
      }}
    >
      <Card
        sx={{
          maxWidth: 460,
          width: '100%',
          p: { xs: 3, sm: 4.5 },
          borderRadius: '16px',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.06)',
          border: '1px solid #E2E8F0',
        }}
      >
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <Box
            sx={{
              display: 'inline-flex',
              p: 1.5,
              borderRadius: '12px',
              backgroundColor: '#EFF6FF',
              color: '#2563EB',
              mb: 2,
            }}
          >
            <Lock size={32} />
          </Box>
          <Typography variant="h5" fontWeight={700} color="#0F172A">
            {isFirstLogin ? 'Set New Password' : 'Change Password'}
          </Typography>
          <Typography variant="body2" color="#64748B" sx={{ mt: 0.5 }}>
            {isFirstLogin
              ? 'Your account requires setting a personal password before continuing.'
              : 'Update your account password following security policies.'}
          </Typography>
        </Box>

        {isFirstLogin && (
          <Alert severity="warning" sx={{ mb: 3, borderRadius: '8px' }}>
            First-time login: Please update your temporary password to secure your account.
          </Alert>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 3, borderRadius: '8px' }}>
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit(onSubmit)}>
          <TextField
            label="Current Password"
            type={showCurrent ? 'text' : 'password'}
            fullWidth
            margin="normal"
            {...register('current_password')}
            error={!!errors.current_password}
            helperText={errors.current_password?.message}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowCurrent(!showCurrent)} edge="end" size="small">
                    {showCurrent ? <EyeOff size={18} /> : <Eye size={18} />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          <TextField
            label="New Password"
            type={showNew ? 'text' : 'password'}
            fullWidth
            margin="normal"
            {...register('new_password')}
            error={!!errors.new_password}
            helperText={errors.new_password?.message}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowNew(!showNew)} edge="end" size="small">
                    {showNew ? <EyeOff size={18} /> : <Eye size={18} />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          <TextField
            label="Confirm New Password"
            type={showConfirm ? 'text' : 'password'}
            fullWidth
            margin="normal"
            {...register('confirm_password')}
            error={!!errors.confirm_password}
            helperText={errors.confirm_password?.message}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowConfirm(!showConfirm)} edge="end" size="small">
                    {showConfirm ? <EyeOff size={18} /> : <Eye size={18} />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          <Button
            type="submit"
            variant="contained"
            fullWidth
            size="large"
            disabled={isSubmitting}
            sx={{
              mt: 3,
              mb: 1.5,
              py: 1.3,
              fontWeight: 600,
              textTransform: 'none',
              borderRadius: '8px',
              backgroundColor: '#0F172A',
              '&:hover': { backgroundColor: '#1E293B' },
            }}
          >
            {isSubmitting ? <CircularProgress size={24} color="inherit" /> : 'Update Password'}
          </Button>

          {!isFirstLogin && (
            <Button
              variant="text"
              fullWidth
              onClick={() => navigate(-1)}
              sx={{ textTransform: 'none', color: '#64748B' }}
            >
              Cancel
            </Button>
          )}
        </form>
      </Card>
    </Box>
  );
};

export default ChangePassword;
