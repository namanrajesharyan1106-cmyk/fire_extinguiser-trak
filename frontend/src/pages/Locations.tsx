import React, { useState } from 'react';
import { 
  Box, Typography, Card, Button, Table, TableBody, TableCell, TableContainer, 
  TableHead, TableRow, IconButton, Dialog, DialogTitle, DialogContent, 
  DialogActions, TextField, CircularProgress, TablePagination, DialogContentText,
  FormControl, InputLabel, Select, MenuItem, InputAdornment
} from '@mui/material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Edit2, Trash2, QrCode, Search, Download } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import api from '../api/axios';
import { toast } from 'react-toastify';

const locationSchema = z.object({
  location_id: z.string().min(1, 'Required'),
  location_name: z.string().min(1, 'Required'),
  plant: z.string().min(1, 'Required'),
  area: z.string().min(1, 'Required'),
  department: z.string().min(1, 'Required'),
  building: z.string().min(1, 'Required'),
  floor: z.string().min(1, 'Required'),
  required_asset_type: z.string().min(1, 'Required'),
  required_capacity: z.string().min(1, 'Required'),
  qr_code: z.string().optional(),
});

type LocationForm = z.infer<typeof locationSchema>;

const Locations: React.FC = () => {
  const queryClient = useQueryClient();
  
  // Modal state
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  
  // Delete Confirmation state
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // QR Preview state
  const [qrPreviewLoc, setQrPreviewLoc] = useState<any>(null);

  // Pagination & Filtering state
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [search, setSearch] = useState('');
  const [filterPlant, setFilterPlant] = useState('');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['locations', page, rowsPerPage, search, filterPlant],
    queryFn: async () => {
      const res = await api.get('/locations', {
        params: {
          skip: page * rowsPerPage,
          limit: rowsPerPage,
          search: search || undefined,
          plant: filterPlant || undefined,
        }
      });
      return res.data.data; // Standardized API response
    }
  });

  const locations = data?.items || [];
  const totalLocations = data?.total || 0;

  const { register, handleSubmit, reset, setValue, formState: { errors } } = useForm<LocationForm>({
    resolver: zodResolver(locationSchema)
  });

  const mutation = useMutation({
    mutationFn: async (formData: LocationForm) => {
      if (editingId) {
        return api.put(`/locations/${editingId}`, formData);
      }
      return api.post('/locations', formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['locations'] });
      toast.success(`Location successfully ${editingId ? 'updated' : 'added'}!`);
      handleClose();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || error.response?.data?.detail || 'An error occurred');
    }
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => api.delete(`/locations/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['locations'] });
      toast.success('Location deleted!');
      setDeleteConfirmId(null);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || error.response?.data?.detail || 'Failed to delete location');
      setDeleteConfirmId(null);
    }
  });

  const generateQrMutation = useMutation({
    mutationFn: async (locationId: string) =>
      api.post(`/locations/${locationId}/generate-qr`),
    onSuccess: (res, locationId) => {
      queryClient.invalidateQueries({ queryKey: ['locations'] });
      const updatedLoc = res.data?.data;
      if (updatedLoc) setQrPreviewLoc(updatedLoc);
      toast.success(`QR generated for ${locationId}`);
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.message || 'Failed to generate QR');
    },
  });

  const handleOpen = (location?: any) => {
    if (location) {
      setEditingId(location.location_id);
      Object.keys(location).forEach((key) => {
        if (key in locationSchema.shape) {
          setValue(key as any, location[key] || '');
        }
      });
    } else {
      setEditingId(null);
      reset();
    }
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    reset();
    setEditingId(null);
  };

  const onSubmit = (formData: LocationForm) => {
    mutation.mutate(formData);
  };

  if (isError) return <Typography color="error">Error loading locations.</Typography>;

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight="bold">Locations</Typography>
        <Button variant="contained" startIcon={<Plus size={18} />} onClick={() => handleOpen()}>
          Add Location
        </Button>
      </Box>

      {/* Filters */}
      <Box display="flex" gap={2} mb={3}>
        <TextField
          label="Search Locations"
          variant="outlined"
          size="small"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(0);
          }}
          sx={{ width: 300 }}
          InputProps={{
            startAdornment: <InputAdornment position="start"><Search size={18} /></InputAdornment>,
          }}
        />
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Filter by Plant</InputLabel>
          <Select
            value={filterPlant}
            label="Filter by Plant"
            onChange={(e) => {
              setFilterPlant(e.target.value);
              setPage(0);
            }}
          >
            <MenuItem value=""><em>All Plants</em></MenuItem>
            <MenuItem value="Plant A">Plant A</MenuItem>
            <MenuItem value="Plant B">Plant B</MenuItem>
            <MenuItem value="Main Facility">Main Facility</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Card>
        <TableContainer>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Plant / Area</TableCell>
                <TableCell>Req. Asset</TableCell>
                <TableCell>Current Asset</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 5 }}><CircularProgress /></TableCell>
                </TableRow>
              ) : locations.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 3 }}>
                    No locations found.
                  </TableCell>
                </TableRow>
              ) : (
                locations.map((loc: any) => (
                  <TableRow key={loc.location_id}>
                    <TableCell>{loc.location_id}</TableCell>
                    <TableCell>{loc.location_name}</TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight="bold">{loc.plant}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {loc.area} ({loc.building}, Fl {loc.floor})
                      </Typography>
                    </TableCell>
                    <TableCell>{loc.required_asset_type} {loc.required_capacity}</TableCell>
                    <TableCell>
                      {loc.current_asset_id ? (
                        <Typography color="success.main" fontWeight="bold">{loc.current_asset_id}</Typography>
                      ) : (
                        <Typography color="error.main">None</Typography>
                      )}
                    </TableCell>
                    <TableCell align="right">
                       <IconButton size="small" color="primary" title="Generate / View QR" onClick={() => { if (loc.qr_code) { setQrPreviewLoc(loc); } else { generateQrMutation.mutate(loc.location_id); } }}><QrCode size={18} /></IconButton>
                       <IconButton size="small" color="secondary" onClick={() => handleOpen(loc)}><Edit2 size={18} /></IconButton>
                       <IconButton size="small" color="error" onClick={() => setDeleteConfirmId(loc.location_id)}><Trash2 size={18} /></IconButton>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div"
          count={totalLocations}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
          rowsPerPageOptions={[10, 25, 50, 100]}
        />
      </Card>

      {/* Create / Edit Dialog */}
      <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogTitle>{editingId ? 'Edit Location' : 'Add Location'}</DialogTitle>
          <DialogContent dividers sx={{ display: 'grid', gap: 2 }}>
            <TextField label="Location ID" {...register('location_id')} error={!!errors.location_id} helperText={errors.location_id?.message} disabled={!!editingId} />
            <Box display="grid" gridTemplateColumns="1fr 1fr" gap={2}>
              <TextField label="Location Name" {...register('location_name')} error={!!errors.location_name} helperText={errors.location_name?.message} />
              <TextField label="Plant" {...register('plant')} error={!!errors.plant} helperText={errors.plant?.message} />
            </Box>
            <Box display="grid" gridTemplateColumns="1fr 1fr" gap={2}>
              <TextField label="Area" {...register('area')} error={!!errors.area} helperText={errors.area?.message} />
              <TextField label="Department" {...register('department')} error={!!errors.department} helperText={errors.department?.message} />
            </Box>
            <Box display="grid" gridTemplateColumns="1fr 1fr" gap={2}>
              <TextField label="Building" {...register('building')} error={!!errors.building} helperText={errors.building?.message} />
              <TextField label="Floor" {...register('floor')} error={!!errors.floor} helperText={errors.floor?.message} />
            </Box>
            <Box display="grid" gridTemplateColumns="1fr 1fr" gap={2}>
              <TextField label="Required Asset" {...register('required_asset_type')} error={!!errors.required_asset_type} helperText={errors.required_asset_type?.message} />
              <TextField label="Capacity" {...register('required_capacity')} error={!!errors.required_capacity} helperText={errors.required_capacity?.message} />
            </Box>
            <TextField label="QR Code Value (Optional)" {...register('qr_code')} error={!!errors.qr_code} helperText={errors.qr_code?.message} />
          </DialogContent>
          <DialogActions>
            <Button onClick={handleClose}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={mutation.isPending}>
              {mutation.isPending ? 'Saving...' : 'Save Location'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteConfirmId} onClose={() => setDeleteConfirmId(null)}>
        <DialogTitle>Confirm Deletion</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete Location '{deleteConfirmId}'? 
            This action cannot be undone. If an asset is assigned, the deletion will be rejected.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirmId(null)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={() => deleteConfirmId && deleteMutation.mutate(deleteConfirmId)} disabled={deleteMutation.isPending}>
            {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* QR Preview Dialog */}
      <Dialog open={!!qrPreviewLoc} onClose={() => setQrPreviewLoc(null)} maxWidth="xs" fullWidth>
        <DialogTitle>QR Code — {qrPreviewLoc?.location_id}</DialogTitle>
        <DialogContent>
          <Box display="flex" flexDirection="column" alignItems="center" gap={2} py={2}>
            {qrPreviewLoc?.qr_code && (
              <QRCodeSVG value={qrPreviewLoc.qr_code} size={200} level="H" includeMargin />
            )}
            <Box textAlign="center">
              <Typography fontWeight="bold">{qrPreviewLoc?.location_id}</Typography>
              <Typography variant="body2" color="text.secondary">{qrPreviewLoc?.location_name}</Typography>
              <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#0052cc' }}>
                {qrPreviewLoc?.qr_code}
              </Typography>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setQrPreviewLoc(null)}>Close</Button>
          <Button
            variant="outlined"
            startIcon={<Download size={16} />}
            onClick={() => qrPreviewLoc && generateQrMutation.mutate(qrPreviewLoc.location_id)}
          >
            Regenerate
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Locations;
