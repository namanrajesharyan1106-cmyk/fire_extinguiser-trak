import React, { useState } from 'react';
import {
  Box,
  Card,
  Typography,
  TextField,
  Button,
  Alert,
  CircularProgress,
  Checkbox,
  FormControlLabel,
  Link,
  IconButton,
  InputAdornment,
} from '@mui/material';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import { Shield, Eye, EyeOff } from 'lucide-react';
import { toast } from 'react-toastify';

const loginSchema = z.object({
  username: z.string().email('Invalid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
});

type LoginForm = z.infer<typeof loginSchema>;

const Login: React.FC = () => {
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    try {
      setError('');

      const formData = new URLSearchParams();
      formData.append('username', data.username);
      formData.append('password', data.password);

      const response = await api.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      console.log('==============================');
      console.log('Login Response:', response.data);
      console.log('==============================');

      // Save token — backend hoists access_token to root level
      if (response.data.access_token) {
        localStorage.setItem('token', response.data.access_token);
      }

      // Save user — backend wraps inside data.data.user
      const userData = response.data?.data?.user || response.data?.user;
      if (userData) {
        localStorage.setItem('user', JSON.stringify(userData));
        if (userData.is_first_login) {
          navigate('/change-password');
        } else {
          navigate('/');
        }
      } else {
        console.warn('Backend did not return a user object.');
        localStorage.removeItem('user');
        navigate('/');
      }
    } catch (err: any) {
      console.error('Login Error:', err);

      setError(
        err?.response?.data?.detail ||
        err?.message ||
        'Login failed. Please try again.'
      );
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#F4F5F7',
      }}
    >
      <Card
        sx={{
          p: 4,
          width: '100%',
          maxWidth: 400,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Box
          sx={{
            p: 2,
            backgroundColor: '#0052cc',
            borderRadius: '50%',
            mb: 2,
          }}
        >
          <Shield color="white" size={32} />
        </Box>

        <Typography
          variant="h5"
          sx={{ mb: 1, fontWeight: 'bold' }}
        >
          FireSafety Pro
        </Typography>

        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mb: 3 }}
        >
          Sign in to your account
        </Typography>

        {error && (
          <Alert severity="error" sx={{ width: '100%', mb: 2 }}>
            {error}
          </Alert>
        )}

        <form
          onSubmit={handleSubmit(onSubmit)}
          style={{ width: '100%' }}
        >
          <TextField
            fullWidth
            margin="normal"
            label="Email Address"
            {...register('username')}
            error={!!errors.username}
            helperText={errors.username?.message}
            autoComplete="email"
          />

          <TextField
            fullWidth
            margin="normal"
            label="Password"
            type={showPassword ? 'text' : 'password'}
            {...register('password')}
            error={!!errors.password}
            helperText={errors.password?.message}
            autoComplete="current-password"
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowPassword(!showPassword)} edge="end">
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          <Box display="flex" justifyContent="space-between" alignItems="center" mt={1}>
            <FormControlLabel
              control={<Checkbox size="small" />}
              label={<Typography variant="body2" color="text.secondary">Remember Me</Typography>}
            />
            <Link 
              href="#" 
              variant="body2" 
              underline="hover" 
              onClick={(e) => { 
                e.preventDefault(); 
                toast.info("Please contact your administrator to reset your password."); 
              }}
            >
              Forgot Password?
            </Link>
          </Box>

          <Button
            type="submit"
            variant="contained"
            fullWidth
            size="large"
            disabled={isSubmitting}
            sx={{ mt: 2, height: 48 }}
          >
            {isSubmitting ? (
              <Box display="flex" alignItems="center" gap={1}>
                <CircularProgress size={20} color="inherit" />
                Signing In...
              </Box>
            ) : (
              'Sign In'
            )}
          </Button>
        </form>
      </Card>
    </Box>
  );
};

export default Login;