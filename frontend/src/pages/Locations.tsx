import React, { useState } from 'react';
import { 
  Box, Typography, Card, Button, Table, TableBody, TableCell, TableContainer, 
  TableHead, TableRow, IconButton, Dialog, DialogTitle, DialogContent, 
  DialogActions, TextField, CircularProgress, TablePagination, DialogContentText,
  FormControl, InputLabel, Select, MenuItem, InputAdornment
} from '@mui/material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Edit2, Trash2, QrCode, Search, Download, Upload } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import api from '../api/axios';
import { toast } from 'react-toastify';

const locationSchema = z.object({
  location_id: z.string().optional(),
  location_name: z.string().min(1, 'Required'),
  plant: z.string().min(1, 'Required'),
  area: z.string().min(1, 'Required'),
  department: z.string().min(1, 'Required'),
  building: z.string().min(1, 'Required'),
  floor: z.string().min(1, 'Required'),
  required_asset_type_id: z.coerce.number().min(1, 'Required'),
  required_capacity_id: z.coerce.number().min(1, 'Required'),
  qr_code: z.string().optional(),
});

type LocationForm = z.infer<typeof locationSchema>;

const Locations: React.FC = () => {
  const queryClient = useQueryClient();
  
  // Modal state
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  
  const userStr = localStorage.getItem('user');
  const user = userStr ? JSON.parse(userStr) : {};
  const isAdmin = user.role === 'ADMIN';

  // Bulk Upload state
  const [bulkSummary, setBulkSummary] = useState<any>(null);
  const [templateError, setTemplateError] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  
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

  const { data: mastersData } = useQuery({
    queryKey: ['mastersActive'],
    queryFn: async () => {
      const res = await api.get('/masters/active');
      return res.data.data;
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

  const handleDownloadSample = async () => {
    try {
      const res = await api.get('/locations/bulk-upload/sample', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'Location_Bulk_Upload_Sample.xlsx');
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch (err: any) {
      toast.error('Failed to download sample file');
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await api.post('/locations/bulk-upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setBulkSummary(res.data.data);
      queryClient.invalidateQueries({ queryKey: ['locations'] });
    } catch (err: any) {
      if (err.response?.headers?.['x-template-error'] || err.response?.data?.detail === "Invalid Excel Template") {
        setTemplateError(true);
      } else {
        toast.error(err.response?.data?.detail || 'Failed to upload locations');
      }
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDownloadErrorReport = () => {
    if (!bulkSummary?.error_report) return;
    const link = document.createElement('a');
    link.href = `data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,${bulkSummary.error_report}`;
    link.download = 'Failed_Locations_Report.xlsx';
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
  };

  if (isError) return <Typography color="error">Error loading locations.</Typography>;

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight="bold">Locations</Typography>
        <Box display="flex" gap={2}>
          {isAdmin && (
            <>
              <Button variant="outlined" startIcon={<Download size={18} />} onClick={handleDownloadSample}>
                Download Sample
              </Button>
              <Button variant="contained" color="secondary" startIcon={isUploading ? <CircularProgress size={18} /> : <Upload size={18} />} onClick={() => fileInputRef.current?.click()} disabled={isUploading}>
                Bulk Upload
              </Button>
              <input type="file" ref={fileInputRef} style={{ display: 'none' }} accept=".xlsx, .xls" onChange={handleFileUpload} />
            </>
          )}
          <Button variant="contained" startIcon={<Plus size={18} />} onClick={() => handleOpen()}>
            Add Location
          </Button>
        </Box>
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
                <TableCell>Current Assets</TableCell>
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
                      {loc.current_assets_count > 0 ? (
                        <Typography color="success.main" fontWeight="bold">{loc.current_assets_count} Asset{loc.current_assets_count > 1 ? 's' : ''}</Typography>
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
            {editingId && (
               <TextField label="Location ID" {...register('location_id')} disabled />
            )}
            <Box display="grid" gridTemplateColumns="1fr 1fr" gap={2}>
              <TextField label="Location Name" {...register('location_name')} error={!!errors.location_name} helperText={errors.location_name?.message} />
              <TextField select label="Plant" {...register('plant')} error={!!errors.plant} helperText={errors.plant?.message} defaultValue="" SelectProps={{ native: true }}>
                <option value=""></option>
                {mastersData?.plants?.map((p: any) => <option key={p.id} value={p.name}>{p.name}</option>)}
              </TextField>
            </Box>
            <Box display="grid" gridTemplateColumns="1fr 1fr" gap={2}>
              <TextField select label="Area" {...register('area')} error={!!errors.area} helperText={errors.area?.message} defaultValue="" SelectProps={{ native: true }}>
                <option value=""></option>
                {mastersData?.areas?.map((p: any) => <option key={p.id} value={p.name}>{p.name}</option>)}
              </TextField>
              <TextField select label="Department" {...register('department')} error={!!errors.department} helperText={errors.department?.message} defaultValue="" SelectProps={{ native: true }}>
                <option value=""></option>
                {mastersData?.departments?.map((p: any) => <option key={p.id} value={p.name}>{p.name}</option>)}
              </TextField>
            </Box>
            <Box display="grid" gridTemplateColumns="1fr 1fr" gap={2}>
              <TextField select label="Building" {...register('building')} error={!!errors.building} helperText={errors.building?.message} defaultValue="" SelectProps={{ native: true }}>
                <option value=""></option>
                {mastersData?.buildings?.map((p: any) => <option key={p.id} value={p.name}>{p.name}</option>)}
              </TextField>
              <TextField select label="Floor" {...register('floor')} error={!!errors.floor} helperText={errors.floor?.message} defaultValue="" SelectProps={{ native: true }}>
                <option value=""></option>
                {mastersData?.floors?.map((p: any) => <option key={p.id} value={p.name}>{p.name}</option>)}
              </TextField>
            </Box>
            <Box display="grid" gridTemplateColumns="1fr 1fr" gap={2}>
              <TextField select label="Required Asset" {...register('required_asset_type_id')} error={!!errors.required_asset_type_id} helperText={errors.required_asset_type_id?.message} defaultValue="" SelectProps={{ native: true }}>
                <option value=""></option>
                {mastersData?.asset_types?.map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </TextField>
              <TextField select label="Capacity" {...register('required_capacity_id')} error={!!errors.required_capacity_id} helperText={errors.required_capacity_id?.message} defaultValue="" SelectProps={{ native: true }}>
                <option value=""></option>
                {mastersData?.capacity_types?.map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </TextField>
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

      {/* Invalid Template Dialog */}
      <Dialog open={templateError} onClose={() => setTemplateError(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ color: 'error.main' }}>Invalid Excel Template</DialogTitle>
        <DialogContent>
          <Typography mb={2}>
            The uploaded Excel file does not match the required template.
          </Typography>
          <Typography>
            Please download the official sample template and upload your data using the same format.
          </Typography>
          <Box sx={{ mt: 2, p: 2, bgcolor: '#fff4e5', borderRadius: 1 }}>
            <Typography variant="subtitle2" fontWeight="bold" gutterBottom>Common Issues:</Typography>
            <ul>
              <li><Typography variant="body2">Missing Columns</Typography></li>
              <li><Typography variant="body2">Extra Columns</Typography></li>
              <li><Typography variant="body2">Incorrect Column Names</Typography></li>
              <li><Typography variant="body2">Wrong Column Order</Typography></li>
            </ul>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDownloadSample} variant="outlined" startIcon={<Download size={16} />}>Download Sample</Button>
          <Button onClick={() => setTemplateError(false)} variant="contained">Close</Button>
        </DialogActions>
      </Dialog>

      {/* Bulk Upload Summary Dialog */}
      <Dialog open={!!bulkSummary} onClose={() => setBulkSummary(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Import Summary</DialogTitle>
        <DialogContent dividers>
          <Box display="grid" gridTemplateColumns="1fr 1fr" gap={2}>
            <Card sx={{ p: 2, textAlign: 'center', bgcolor: '#f8f9fa' }}>
              <Typography variant="h4" fontWeight="bold" color="primary">{bulkSummary?.summary?.total || 0}</Typography>
              <Typography variant="body2" color="text.secondary">Total Rows</Typography>
            </Card>
            <Card sx={{ p: 2, textAlign: 'center', bgcolor: '#e6f4ea' }}>
              <Typography variant="h4" fontWeight="bold" color="success.main">{bulkSummary?.summary?.imported || 0}</Typography>
              <Typography variant="body2" color="text.secondary">Imported</Typography>
            </Card>
            <Card sx={{ p: 2, textAlign: 'center', bgcolor: '#fce8e6' }}>
              <Typography variant="h4" fontWeight="bold" color="error.main">{bulkSummary?.summary?.failed || 0}</Typography>
              <Typography variant="body2" color="text.secondary">Failed</Typography>
            </Card>
            <Card sx={{ p: 2, textAlign: 'center', bgcolor: '#fef7e0' }}>
              <Typography variant="h4" fontWeight="bold" color="warning.main">{bulkSummary?.summary?.skipped || 0}</Typography>
              <Typography variant="body2" color="text.secondary">Skipped</Typography>
            </Card>
          </Box>
          {bulkSummary?.error_report && (
             <Box mt={3} p={2} bgcolor="#fff4e5" borderRadius={1} display="flex" justifyContent="space-between" alignItems="center">
               <Typography variant="body2">Some rows failed to import. Download the error report to see the details.</Typography>
               <Button variant="contained" color="error" size="small" onClick={handleDownloadErrorReport} startIcon={<Download size={16} />}>Error Report</Button>
             </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBulkSummary(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Locations;
