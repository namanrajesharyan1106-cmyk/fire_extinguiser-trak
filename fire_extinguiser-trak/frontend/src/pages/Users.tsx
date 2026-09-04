import React, { useState } from 'react';
import {
  Box, Typography, Card, Button, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, IconButton, Dialog,
  DialogTitle, DialogContent, DialogActions, TextField,
  CircularProgress, Chip, Tooltip, FormControl,
  InputLabel, Select, MenuItem, Grid, Avatar, Alert,
  InputAdornment,
} from '@mui/material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Edit2, UserX, Key, Search } from 'lucide-react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import api from '../api/axios';
import { toast } from 'react-toastify';

// ─── Types ───────────────────────────────────────────────────────────────────
interface User {
  id: number;
  employee_id: string | null;
  name: string | null;
  email: string | null;
  role: string | null;
  department: string | null;
  plant: string | null;
  status: string | null;
}

// ─── Schemas ──────────────────────────────────────────────────────────────────
const createUserSchema = z.object({
  employee_id: z.string().min(1, 'Employee ID is required'),
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email'),
  password: z.string().min(8, 'Min 8 characters'),
  role: z.string().min(1, 'Role is required'),
  department: z.string().optional(),
  plant: z.string().optional(),
  status: z.string().optional(),
});

const updateUserSchema = z.object({
  name: z.string().min(1).optional(),
  role: z.string().optional(),
  department: z.string().optional(),
  plant: z.string().optional(),
  status: z.string().optional(),
});

type CreateUserForm = z.infer<typeof createUserSchema>;
type UpdateUserForm = z.infer<typeof updateUserSchema>;

const formatRole = (r: string | null) => (r || '').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');

const roleColor = (role: string | null): 'error' | 'warning' | 'primary' | 'success' | 'default' => {
  const r = (role || '').toUpperCase();
  if (r === 'ADMIN' || r === 'IT ADMIN') return 'error';
  if (r === 'SAFETY HEAD') return 'warning';
  if (r === 'SAFETY OFFICER') return 'primary';
  if (r === 'INSPECTOR' || r === 'MAINTENANCE' || r === 'TECHNICIAN') return 'success';
  return 'default';
};

const getInitials = (name: string | null) =>
  (name || '').split(' ').map((n) => n ? n[0] : '').join('').toUpperCase().slice(0, 2);

const avatarColors = ['#0052cc', '#36B37E', '#FFAB00', '#FF5630', '#6554C0', '#00B8D9'];

// ─── Create User Dialog ───────────────────────────────────────────────────────
const CreateUserDialog: React.FC<{ open: boolean; onClose: () => void; roles: string[] }> = ({ open, onClose, roles }) => {
  const queryClient = useQueryClient();
  const { register, handleSubmit, reset, control, formState: { errors } } = useForm<CreateUserForm>({
    resolver: zodResolver(createUserSchema),
    defaultValues: { role: roles[0] || 'INSPECTOR', status: 'Active' },
  });

  const mutation = useMutation({
    mutationFn: async (data: CreateUserForm) => api.post('/auth/users', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('User created successfully!');
      reset();
      onClose();
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.message || err.response?.data?.detail || 'Failed to create user');
    },
  });

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit((d) => mutation.mutate(d))}>
        <DialogTitle>Create New User</DialogTitle>
        <DialogContent dividers>
          <Grid container spacing={2} sx={{ pt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth label="Employee ID *"
                {...register('employee_id')}
                error={!!errors.employee_id}
                helperText={errors.employee_id?.message}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth label="Full Name *"
                {...register('name')}
                error={!!errors.name}
                helperText={errors.name?.message}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth label="Email *"
                type="email"
                {...register('email')}
                error={!!errors.email}
                helperText={errors.email?.message}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth label="Password *"
                type="password"
                {...register('password')}
                error={!!errors.password}
                helperText={errors.password?.message || 'Min 8 characters'}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Role *</InputLabel>
                <Controller
                  name="role"
                  control={control}
                  render={({ field }) => (
                    <Select {...field} label="Role *">
                      {roles.map((r) => <MenuItem key={r} value={r}>{formatRole(r)}</MenuItem>)}
                    </Select>
                  )}
                />
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Controller
                  name="status"
                  control={control}
                  render={({ field }) => (
                    <Select {...field} label="Status">
                      <MenuItem value="Active">Active</MenuItem>
                      <MenuItem value="Inactive">Inactive</MenuItem>
                    </Select>
                  )}
                />
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField fullWidth label="Department" {...register('department')} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField fullWidth label="Plant" {...register('plant')} />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={mutation.isPending}>
            {mutation.isPending ? 'Creating...' : 'Create User'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

// ─── Edit User Dialog ─────────────────────────────────────────────────────────
const EditUserDialog: React.FC<{ user: User | null; open: boolean; onClose: () => void; roles: string[] }> = ({
  user, open, onClose, roles
}) => {
  const queryClient = useQueryClient();
  const { register, handleSubmit, control } = useForm<UpdateUserForm>({
    resolver: zodResolver(updateUserSchema),
    values: user
      ? { name: user.name ?? '', role: user.role ?? '', department: user.department ?? '', plant: user.plant ?? '', status: user.status ?? '' }
      : undefined,
  });

  const mutation = useMutation({
    mutationFn: async (data: UpdateUserForm) => api.put(`/auth/users/${user!.id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('User updated!');
      onClose();
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.message || 'Update failed');
    },
  });

  if (!user) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit((d) => mutation.mutate(d))}>
        <DialogTitle>Edit User — {user.name}</DialogTitle>
        <DialogContent dividers>
          <Grid container spacing={2} sx={{ pt: 1 }}>
            <Grid item xs={12}>
              <TextField fullWidth label="Full Name" {...register('name')} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Role</InputLabel>
                <Controller
                  name="role"
                  control={control}
                  render={({ field }) => (
                    <Select {...field} label="Role">
                      {roles.map((r) => <MenuItem key={r} value={r}>{formatRole(r)}</MenuItem>)}
                    </Select>
                  )}
                />
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Controller
                  name="status"
                  control={control}
                  render={({ field }) => (
                    <Select {...field} label="Status">
                      <MenuItem value="Active">Active</MenuItem>
                      <MenuItem value="Inactive">Inactive</MenuItem>
                    </Select>
                  )}
                />
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField fullWidth label="Department" {...register('department')} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField fullWidth label="Plant" {...register('plant')} />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={mutation.isPending}>
            {mutation.isPending ? 'Saving...' : 'Save Changes'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

// ─── Reset Password Dialog ────────────────────────────────────────────────────
const ResetPasswordDialog: React.FC<{ user: User | null; open: boolean; onClose: () => void }> = ({
  user, open, onClose,
}) => {
  const [newPassword, setNewPassword] = useState('');

  const mutation = useMutation({
    mutationFn: async () =>
      api.post(`/auth/users/${user!.id}/reset-password`, { new_password: newPassword }),
    onSuccess: () => {
      toast.success(`Password reset for ${user?.name}. They must change it on next login.`);
      setNewPassword('');
      onClose();
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Reset failed');
    },
  });

  if (!user) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Reset Password — {user.name}</DialogTitle>
      <DialogContent dividers>
        <Alert severity="warning" sx={{ mb: 2 }}>
          The user will be forced to change their password on next login.
        </Alert>
        <TextField
          fullWidth
          label="New Password"
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          helperText="Minimum 8 characters"
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          color="warning"
          disabled={newPassword.length < 8 || mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          {mutation.isPending ? 'Resetting...' : 'Reset Password'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────
const Users: React.FC = () => {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [editUser, setEditUser] = useState<User | null>(null);
  const [resetUser, setResetUser] = useState<User | null>(null);

  // GET /auth/users — returns {success, data: User[]}
  const { data: usersData, isLoading, isError } = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const res = await api.get('/auth/users');
      const users = res.data?.data;
      return Array.isArray(users) ? users : [];
    },
  });

  // GET /auth/roles — dynamically load roles
  const { data: rolesData } = useQuery({
    queryKey: ['roles'],
    queryFn: async () => {
      const res = await api.get('/auth/roles');
      return res.data?.data?.roles || [];
    },
  });

  const roles: string[] = Array.isArray(rolesData) ? rolesData : [];
  const users: User[] = Array.isArray(usersData) ? usersData : [];

  const filtered = users.filter((u) => {
    const term = (search || '').toLowerCase();
    return (
      (u.name || '').toLowerCase().includes(term) ||
      (u.email || '').toLowerCase().includes(term) ||
      (u.employee_id || '').toLowerCase().includes(term) ||
      (u.role || '').toLowerCase().includes(term)
    );
  });

  const deactivateMutation = useMutation({
    mutationFn: async (userId: number) => api.delete(`/auth/users/${userId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('User deactivated successfully');
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.message || 'Deactivation failed');
    },
  });

  if (isError) {
    return (
      <Box p={4}>
        <Typography color="error">Failed to load users. You may not have permission to view this page.</Typography>
        <Button variant="outlined" sx={{ mt: 2 }} onClick={() => queryClient.invalidateQueries({ queryKey: ['users'] })}>
          Retry
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" fontWeight="bold">Users</Typography>
          <Typography variant="body2" color="text.secondary">
            {users.length} total · {users.filter((u) => u.status === 'Active').length} active
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<Plus size={18} />} onClick={() => setCreateOpen(true)}>
          Add User
        </Button>
      </Box>

      {/* Search */}
      <Box mb={3}>
        <TextField
          label="Search Users"
          size="small"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ width: 300 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start"><Search size={16} /></InputAdornment>
            ),
          }}
        />
      </Box>

      {/* Table */}
      <Card>
        <TableContainer>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>User</TableCell>
                <TableCell>Employee ID</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Department</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 5 }}><CircularProgress /></TableCell>
                </TableRow>
              ) : filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">
                      {search ? 'No users match your search.' : 'No users found.'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((user, idx) => (
                  <TableRow key={user.id} hover>
                    <TableCell>
                      <Box display="flex" alignItems="center" gap={1.5}>
                        <Avatar
                          sx={{
                            width: 36, height: 36, fontSize: 14, fontWeight: 'bold',
                            bgcolor: avatarColors[idx % avatarColors.length],
                          }}
                        >
                          {getInitials(user.name)}
                        </Avatar>
                        <Typography fontWeight={600}>{user.name || 'Unnamed User'}</Typography>
                      </Box>
                    </TableCell>
                    <TableCell sx={{ fontFamily: 'monospace' }}>{user.employee_id || '—'}</TableCell>
                    <TableCell>{user.email || '—'}</TableCell>
                    <TableCell>
                      <Chip label={formatRole(user.role)} color={roleColor(user.role)} size="small" />
                    </TableCell>
                    <TableCell>{user.department ?? '—'}</TableCell>
                    <TableCell>
                      <Chip
                        label={user.status || 'Unknown'}
                        size="small"
                        color={user.status === 'Active' ? 'success' : 'default'}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="Edit User">
                        <IconButton size="small" color="primary" onClick={() => setEditUser(user)}>
                          <Edit2 size={16} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Reset Password">
                        <IconButton size="small" color="warning" onClick={() => setResetUser(user)}>
                          <Key size={16} />
                        </IconButton>
                      </Tooltip>
                      {user.status === 'Active' && (
                        <Tooltip title="Deactivate User">
                          <IconButton
                            size="small"
                            color="error"
                            disabled={deactivateMutation.isPending}
                            onClick={() => {
                              if (window.confirm(`Deactivate ${user.name}?`)) {
                                deactivateMutation.mutate(user.id);
                              }
                            }}
                          >
                            <UserX size={16} />
                          </IconButton>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      <CreateUserDialog open={createOpen} onClose={() => setCreateOpen(false)} roles={roles} />
      <EditUserDialog user={editUser} open={!!editUser} onClose={() => setEditUser(null)} roles={roles} />
      <ResetPasswordDialog user={resetUser} open={!!resetUser} onClose={() => setResetUser(null)} />
    </Box>
  );
};

class ErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean, error: Error | null}> {
  constructor(props: {children: React.ReactNode}) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box p={4}>
          <Alert severity="error" sx={{ mb: 2 }}>
            Something went wrong rendering this page.
          </Alert>
          <Typography variant="body2" color="text.secondary">
            {this.state.error?.message}
          </Typography>
        </Box>
      );
    }
    return this.props.children;
  }
}

const UsersWithErrorBoundary = () => (
  <ErrorBoundary>
    <Users />
  </ErrorBoundary>
);

export default UsersWithErrorBoundary;
