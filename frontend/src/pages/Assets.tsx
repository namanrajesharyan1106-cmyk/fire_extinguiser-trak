import React, { useState } from 'react';
import {
  Box, Typography, Card, Button, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, IconButton, Dialog,
  DialogTitle, DialogContent, DialogActions, TextField,
  CircularProgress, MenuItem, Select, InputLabel, FormControl,
  TablePagination, InputAdornment, Chip, Tooltip
} from '@mui/material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Edit2, Link as LinkIcon, Trash2, Search, Unlink, QrCode, Download, Upload } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import api from '../api/axios';
import { toast } from 'react-toastify';
import AssetAssignmentDrawer from '../components/AssetAssignmentDrawer';
import QRScannerDialog from '../components/QRScannerDialog';
import AssetBulkUploadDialog from '../components/AssetBulkUploadDialog';

// ─── Types ───────────────────────────────────────────────────────────────────
interface Asset {
  asset_id: string;
  serial_number: string;
  asset_type: string;
  asset_type_id?: number;
  capacity: string | null;
  capacity_id?: number;
  manufacturer: string | null;
  manufacturing_date: string | null;
  refill_date: string | null;
  expiry_date: string | null;
  status: string;
  current_location_id: string | null;
  photo: string | null;
}

// ─── Schema ──────────────────────────────────────────────────────────────────
const assetSchema = z.object({
  asset_id: z.string().optional(),
  serial_number: z.string().min(1, 'Serial number is required'),
  asset_type_id: z.coerce.number().min(1, 'Asset type is required'),
  capacity_id: z.coerce.number().optional(),
  manufacturer: z.string().optional(),
  manufacturing_date: z.string().optional(),
  refill_date: z.string().optional(),
  expiry_date: z.string().optional(),
  status: z.string().optional(),
  remarks: z.string().optional(),
});

type AssetForm = z.infer<typeof assetSchema>;

// ─── Status chip helper ───────────────────────────────────────────────────────
const StatusChip = ({ status }: { status: string }) => {
  const colorMap: Record<string, 'success' | 'error' | 'warning' | 'default'> = {
    Active: 'success',
    Expired: 'error',
    Retired: 'default',
    'Under Maintenance': 'warning',
  };
  return <Chip label={status} color={colorMap[status] ?? 'default'} size="small" />;
};

// ─── Component ───────────────────────────────────────────────────────────────
const Assets: React.FC = () => {
  const queryClient = useQueryClient();

  // Dialog state
  const [open, setOpen] = useState(false);
  const [linkOpen, setLinkOpen] = useState(false);
  const [scannerOpen, setScannerOpen] = useState(false);
  const [bulkUploadOpen, setBulkUploadOpen] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [selectedAssetForLink, setSelectedAssetForLink] = useState<string | null>(null);

  // Pagination & filter state
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterType, setFilterType] = useState('');

  // ─── Queries ─────────────────────────────────────────────────────────────
  // GET /assets — returns a raw array
  const { data: assetsRaw, isLoading, isError } = useQuery({
    queryKey: ['assets', filterStatus, filterType],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (filterStatus) params.status = filterStatus;
      if (filterType) params.asset_type = filterType;
      const res = await api.get('/assets', { params });
      const items = res.data?.data?.items;
      return Array.isArray(items) ? items : [];
    },
  });

  // GET /masters/active
  const { data: mastersData } = useQuery({
    queryKey: ['mastersActive'],
    queryFn: async () => {
      const res = await api.get('/masters/active');
      return res.data?.data;
    }
  });

  const assets: Asset[] = Array.isArray(assetsRaw) ? assetsRaw : [];

  // Client-side search filter
  const filtered = assets.filter((a) => {
    const term = search.toLowerCase();
    if (!term) return true;
    return (
      a.asset_id.toLowerCase().includes(term) ||
      a.serial_number.toLowerCase().includes(term) ||
      a.asset_type.toLowerCase().includes(term) ||
      (a.manufacturer?.toLowerCase() ?? '').includes(term) ||
      (a.current_location_id?.toLowerCase() ?? '').includes(term)
    );
  });

  const paginated = filtered.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  // ─── Form ────────────────────────────────────────────────────────────────
  const { register, handleSubmit, reset, setValue, formState: { errors } } = useForm<AssetForm>({
    resolver: zodResolver(assetSchema),
  });

  // ─── Mutations ───────────────────────────────────────────────────────────
  const mutation = useMutation({
    mutationFn: async (data: AssetForm) => {
      if (editingId) return api.put(`/assets/${editingId}`, data);
      return api.post('/assets', data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      toast.success(`Asset ${editingId ? 'updated' : 'created'} successfully!`);
      handleClose();
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || err.response?.data?.message || 'An error occurred');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => api.delete(`/assets/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      toast.success('Asset deleted successfully!');
      setDeleteConfirmId(null);
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Cannot delete assigned asset. Unlink first.');
      setDeleteConfirmId(null);
    },
  });

  const unlinkMutation = useMutation({
    mutationFn: async (id: string) => api.delete(`/assets/${id}/unlink`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      toast.success('Asset unlinked!');
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Unlink failed');
    },
  });

  // ─── Handlers ────────────────────────────────────────────────────────────
  const handleDownloadSample = async () => {
    try {
      const res = await api.get('/assets/bulk-upload/sample', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'Asset_Bulk_Upload_Sample.xlsx');
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch {
      toast.error('Failed to download asset sample file');
    }
  };

  const handleOpen = (asset?: Asset) => {
    if (asset) {
      setEditingId(asset.asset_id);
      setValue('serial_number', asset.serial_number ?? '');
      setValue('asset_type_id', asset.asset_type_id ?? ('' as any));
      setValue('capacity_id', asset.capacity_id ?? ('' as any));
      setValue('manufacturer', asset.manufacturer ?? '');
      setValue('manufacturing_date', asset.manufacturing_date?.slice(0, 10) ?? '');
      setValue('refill_date', asset.refill_date?.slice(0, 10) ?? '');
      setValue('expiry_date', asset.expiry_date?.slice(0, 10) ?? '');
      setValue('status', asset.status ?? 'Active');
    } else {
      setEditingId(null);
      reset();
    }
    setOpen(true);
  };

  const handleClose = () => { setOpen(false); reset(); setEditingId(null); };

  const handleLinkOpen = (id: string) => {
    setSelectedAssetForLink(id);
    setLinkOpen(true);
  };

  const handleScanAsset = (decodedText: string) => {
    setScannerOpen(false);
    
    // Attempt to match decodedText (might be full QR JSON or just the ID)
    let scannedId = decodedText;
    try {
      const parsed = JSON.parse(decodedText);
      if (parsed.asset_id) scannedId = parsed.asset_id;
    } catch(e) {}
    
    const asset = assetsRaw?.find(a => a.asset_id === scannedId);
    if (asset) {
      handleLinkOpen(asset.asset_id);
    } else {
      toast.error('Scanned asset not found in database.');
    }
  };

  const onSubmit = (data: AssetForm) => mutation.mutate(data);

  // ─── Render ──────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <Box p={4}>
        <Typography color="error" variant="h6">Failed to load assets.</Typography>
        <Button variant="outlined" sx={{ mt: 2 }} onClick={() => queryClient.invalidateQueries({ queryKey: ['assets'] })}>
          Retry
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight="bold">Assets</Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            color="primary"
            startIcon={<QrCode size={18} />}
            onClick={() => setScannerOpen(true)}
          >
            Scan Asset
          </Button>
          <Button
            variant="outlined"
            startIcon={<Download size={18} />}
            onClick={handleDownloadSample}
          >
            Download Sample
          </Button>
          <Button
            variant="contained"
            color="secondary"
            startIcon={<Upload size={18} />}
            onClick={() => setBulkUploadOpen(true)}
          >
            Bulk Upload
          </Button>
          <Button
            variant="contained"
            color="primary"
            startIcon={<Plus size={18} />}
            onClick={() => handleOpen()}
          >
            Add Asset
          </Button>
        </Box>
      </Box>

      {/* Filters */}
      <Box display="flex" gap={2} mb={3} flexWrap="wrap">
        <TextField
          label="Search Assets"
          variant="outlined"
          size="small"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(0); }}
          sx={{ width: 280 }}
          InputProps={{
            startAdornment: <InputAdornment position="start"><Search size={16} /></InputAdornment>,
          }}
        />
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>Status</InputLabel>
          <Select value={filterStatus} label="Status" onChange={(e) => { setFilterStatus(e.target.value); setPage(0); }}>
            <MenuItem value=""><em>All</em></MenuItem>
            <MenuItem value="Active">Active</MenuItem>
            <MenuItem value="Expired">Expired</MenuItem>
            <MenuItem value="Under Maintenance">Under Maintenance</MenuItem>
            <MenuItem value="Retired">Retired</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>Type</InputLabel>
          <Select value={filterType} label="Type" onChange={(e) => { setFilterType(e.target.value); setPage(0); }}>
            <MenuItem value=""><em>All Types</em></MenuItem>
            {mastersData?.asset_types?.map((p: any) => (
              <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {/* Table */}
      <Card>
        <TableContainer>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>Asset ID</TableCell>
                <TableCell>Type / Capacity</TableCell>
                <TableCell>Serial No.</TableCell>
                <TableCell>Expiry Date</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Location</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 5 }}>
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : paginated.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">
                      {search || filterStatus || filterType ? 'No assets match your filters.' : 'No assets found. Create one to get started.'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                paginated.map((asset) => (
                  <TableRow key={asset.asset_id} hover>
                    <TableCell sx={{ fontFamily: 'monospace', fontWeight: 600 }}>{asset.asset_id}</TableCell>
                    <TableCell>{asset.asset_type}{asset.capacity ? ` (${asset.capacity})` : ''}</TableCell>
                    <TableCell>{asset.serial_number}</TableCell>
                    <TableCell sx={{ color: asset.expiry_date && new Date(asset.expiry_date) < new Date() ? 'error.main' : 'inherit' }}>
                      {asset.expiry_date ? asset.expiry_date.slice(0, 10) : '—'}
                    </TableCell>
                    <TableCell><StatusChip status={asset.status ?? 'Active'} /></TableCell>
                    <TableCell>
                      {asset.current_location_id ? (
                        <Typography color="primary.main" fontWeight={600} variant="body2">{asset.current_location_id}</Typography>
                      ) : (
                        <Typography color="text.disabled" variant="body2">Unassigned</Typography>
                      )}
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="Link to Location">
                        <IconButton size="small" color="primary" onClick={() => handleLinkOpen(asset.asset_id)}>
                          <LinkIcon size={16} />
                        </IconButton>
                      </Tooltip>
                      {asset.current_location_id && (
                        <Tooltip title="Unlink from Location">
                          <IconButton size="small" color="warning" onClick={() => unlinkMutation.mutate(asset.asset_id)}>
                            <Unlink size={16} />
                          </IconButton>
                        </Tooltip>
                      )}
                      <Tooltip title="Edit">
                        <IconButton size="small" color="secondary" onClick={() => handleOpen(asset)}>
                          <Edit2 size={16} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton size="small" color="error" onClick={() => setDeleteConfirmId(asset.asset_id)}>
                          <Trash2 size={16} />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div"
          count={filtered.length}
          page={page}
          onPageChange={(_, p) => setPage(p)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
          rowsPerPageOptions={[10, 25, 50, 100]}
        />
      </Card>

      {/* Create / Edit Dialog */}
      <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogTitle>{editingId ? 'Edit Asset' : 'Add Asset'}</DialogTitle>
          <DialogContent dividers sx={{ display: 'grid', gap: 2, pt: 2 }}>
            {!editingId && (
              <TextField label="Asset ID (optional — auto-generated if blank)" {...register('asset_id')} helperText="e.g. AST-001" />
            )}
            <TextField label="Serial Number *" {...register('serial_number')} error={!!errors.serial_number} helperText={errors.serial_number?.message} />
            <Box display="grid" gridTemplateColumns="1fr 1fr" gap={2}>
              <FormControl fullWidth error={!!errors.asset_type_id}>
                <InputLabel shrink>Asset Type *</InputLabel>
                <Select native label="Asset Type *" {...register('asset_type_id')} defaultValue="">
                  <option value="" disabled></option>
                  {mastersData?.asset_types?.map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </Select>
                {errors.asset_type_id && <Typography color="error" variant="caption">{errors.asset_type_id.message}</Typography>}
              </FormControl>
              <FormControl fullWidth error={!!errors.capacity_id}>
                <InputLabel shrink>Capacity</InputLabel>
                <Select native label="Capacity" {...register('capacity_id')} defaultValue="">
                  <option value=""></option>
                  {mastersData?.capacity_types?.map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </Select>
                {errors.capacity_id && <Typography color="error" variant="caption">{errors.capacity_id.message}</Typography>}
              </FormControl>
            </Box>
            <TextField label="Manufacturer" {...register('manufacturer')} />
            <Box display="grid" gridTemplateColumns="1fr 1fr 1fr" gap={2}>
              <TextField type="date" label="Mfg. Date" InputLabelProps={{ shrink: true }} {...register('manufacturing_date')} />
              <TextField type="date" label="Refill Date" InputLabelProps={{ shrink: true }} {...register('refill_date')} />
              <TextField type="date" label="Expiry Date" InputLabelProps={{ shrink: true }} {...register('expiry_date')} />
            </Box>
            {editingId && (
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Select label="Status" defaultValue="Active" {...register('status')}>
                  <MenuItem value="Active">Active</MenuItem>
                  <MenuItem value="Under Maintenance">Under Maintenance</MenuItem>
                  <MenuItem value="Expired">Expired</MenuItem>
                  <MenuItem value="Retired">Retired</MenuItem>
                </Select>
              </FormControl>
            )}
            <TextField label="Remarks" {...register('remarks')} multiline rows={2} />
          </DialogContent>
          <DialogActions>
            <Button onClick={handleClose}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={mutation.isPending}>
              {mutation.isPending ? 'Saving...' : 'Save Asset'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      <AssetAssignmentDrawer
        open={linkOpen}
        onClose={() => setLinkOpen(false)}
        asset={assetsRaw?.find(a => a.asset_id === selectedAssetForLink) || null}
      />
      
      <QRScannerDialog 
        open={scannerOpen}
        onClose={() => setScannerOpen(false)}
        onScan={handleScanAsset}
      />

      {/* Delete Confirm Dialog */}
      <Dialog open={!!deleteConfirmId} onClose={() => setDeleteConfirmId(null)}>
        <DialogTitle>Confirm Deletion</DialogTitle>
        <DialogContent>
          <Typography>
            Delete asset <strong>{deleteConfirmId}</strong>? Assets assigned to a location must be unlinked first.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirmId(null)}>Cancel</Button>
          <Button
            color="error"
            variant="contained"
            disabled={deleteMutation.isPending}
            onClick={() => deleteConfirmId && deleteMutation.mutate(deleteConfirmId)}
          >
            {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
      {/* Asset Bulk Upload Modal */}
      <AssetBulkUploadDialog
        open={bulkUploadOpen}
        onClose={() => setBulkUploadOpen(false)}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['assets'] });
          queryClient.invalidateQueries({ queryKey: ['locations'] });
          queryClient.invalidateQueries({ queryKey: ['dashboard'] });
        }}
      />
    </Box>
  );
};

export default Assets;
