import React, { useState } from 'react';
import {
  Box, Typography, Card, Button, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, IconButton, Dialog,
  DialogTitle, DialogContent, DialogActions, TextField,
  CircularProgress, TablePagination, InputAdornment, Chip,
  Tooltip, FormControl, InputLabel, Select, MenuItem,
  Grid, Divider, Alert, Autocomplete
} from '@mui/material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Search, Eye, ArrowRight, Camera } from 'lucide-react';
import { useForm, Controller } from 'react-hook-form';
import api from '../api/axios';
import { toast } from 'react-toastify';
import QRScannerDialog from '../components/QRScannerDialog';

// ─── Types ───────────────────────────────────────────────────────────────────
interface MaintenanceTicket {
  maintenance_id: number;
  asset_id: string | null;
  location_id: string | null;
  issue: string | null;
  priority: string;
  status: string;
  assigned_to: string | null;
  remarks: string | null;
  source: string | null;
  opened_date: string;
  completion_date: string | null;
  closed_date: string | null;
  technician_id: number | null;
  verified_by: string | null;
}

// ─── Priority & Status config ─────────────────────────────────────────────────
const PRIORITY_COLOR: Record<string, 'error' | 'warning' | 'success' | 'default'> = {
  Critical: 'error',
  High: 'error',
  Medium: 'warning',
  Low: 'success',
};

const STATUS_COLOR: Record<string, 'default' | 'warning' | 'primary' | 'success' | 'error'> = {
  Open: 'warning',
  'In Progress': 'primary',
  'Waiting Parts': 'warning',
  Completed: 'success',
  Verified: 'success',
  Closed: 'default',
};

// Backend-defined allowed transitions
const STATUS_TRANSITIONS: Record<string, string[]> = {
  Open: ['In Progress', 'Closed'],
  'In Progress': ['Waiting Parts', 'Completed'],
  'Waiting Parts': ['In Progress'],
  Completed: ['Verified', 'Closed'],
  Verified: ['Closed'],
  Closed: [],
};

// ─── Detail / Status Update Dialog ───────────────────────────────────────────
const TicketDetailDialog: React.FC<{
  ticket: MaintenanceTicket | null;
  open: boolean;
  onClose: () => void;
}> = ({ ticket, open, onClose }) => {
  const queryClient = useQueryClient();
  const [newStatus, setNewStatus] = useState('');
  const [remarks, setRemarks] = useState('');

  const statusMutation = useMutation({
    mutationFn: async () =>
      api.put(`/maintenance/${ticket!.maintenance_id}/status`, {
        new_status: newStatus,
        remarks: remarks || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['maintenance'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      toast.success(`Ticket status updated to "${newStatus}"`);
      onClose();
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Status update failed');
    },
  });

  if (!ticket) return null;
  const allowed = STATUS_TRANSITIONS[ticket.status] ?? [];

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Ticket #{ticket.maintenance_id}</DialogTitle>
      <DialogContent dividers>
        <Grid container spacing={2} mb={2}>
          <Grid item xs={6}>
            <Typography variant="caption" color="text.secondary">Asset</Typography>
            <Typography fontWeight="bold">{ticket.asset_id ?? 'N/A'}</Typography>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="caption" color="text.secondary">Location</Typography>
            <Typography fontWeight="bold">{ticket.location_id ?? 'N/A'}</Typography>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="caption" color="text.secondary">Priority</Typography>
            <Box mt={0.5}><Chip label={ticket.priority} color={PRIORITY_COLOR[ticket.priority]} size="small" /></Box>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="caption" color="text.secondary">Status</Typography>
            <Box mt={0.5}><Chip label={ticket.status} color={STATUS_COLOR[ticket.status]} size="small" /></Box>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="caption" color="text.secondary">Assigned To</Typography>
            <Typography>{ticket.assigned_to ?? '—'}</Typography>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="caption" color="text.secondary">Opened</Typography>
            <Typography>{new Date(ticket.opened_date).toLocaleDateString()}</Typography>
          </Grid>
          <Grid item xs={12}>
            <Typography variant="caption" color="text.secondary">Issue</Typography>
            <Typography>{ticket.issue ?? '—'}</Typography>
          </Grid>
          {ticket.remarks && (
            <Grid item xs={12}>
              <Typography variant="caption" color="text.secondary">Remarks/History</Typography>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-line' }}>{ticket.remarks}</Typography>
            </Grid>
          )}
        </Grid>

        {allowed.length > 0 && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" fontWeight="bold" mb={1}>Update Status</Typography>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <FormControl fullWidth size="small">
                  <InputLabel>New Status</InputLabel>
                  <Select value={newStatus} label="New Status" onChange={(e) => setNewStatus(e.target.value)}>
                    {allowed.map((s) => (
                      <MenuItem key={s} value={s}>{ticket.status} <ArrowRight size={12} style={{ margin: '0 4px' }} /> {s}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  size="small"
                  label="Remarks (optional)"
                  multiline
                  rows={2}
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                />
              </Grid>
            </Grid>
          </>
        )}

        {allowed.length === 0 && (
          <Alert severity="info" sx={{ mt: 1 }}>
            This ticket is <strong>{ticket.status}</strong> — no further status transitions available.
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        {allowed.length > 0 && (
          <Button
            variant="contained"
            disabled={!newStatus || statusMutation.isPending}
            onClick={() => statusMutation.mutate()}
          >
            {statusMutation.isPending ? 'Updating...' : 'Update Status'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

// ─── Create Ticket Dialog ─────────────────────────────────────────────────────
const CreateTicketDialog: React.FC<{
  open: boolean;
  onClose: () => void;
}> = ({ open, onClose }) => {
  const queryClient = useQueryClient();
  const { register, handleSubmit, reset, control, watch, setValue } = useForm<any>({
    defaultValues: { priority: 'Medium', source: 'Manual' },
  });

  const [scannerOpen, setScannerOpen] = useState(false);
  const [scanResult, setScanResult] = useState<{type: 'Asset' | 'Location' | 'Unknown', data: any} | null>(null);

  const selectedAssetId = watch('asset_id');
  const selectedLocationId = watch('location_id');

  const { data: locations = [] } = useQuery({
    queryKey: ['locations-dropdown-maintenance'],
    queryFn: async () => {
      const res = await api.get('/locations', { params: { limit: 1000 } });
      return Array.isArray(res.data?.data?.items) ? res.data.data.items : [];
    },
    enabled: open,
  });

  const { data: assets = [] } = useQuery({
    queryKey: ['assets-dropdown-maintenance'],
    queryFn: async () => {
      const res = await api.get('/assets', { params: { limit: 1000 } });
      const items = res.data?.data?.items;
      return Array.isArray(items) ? items : [];
    },
    enabled: open,
  });

  let filteredAssets = assets;
  if (selectedLocationId) {
    // If a location is selected, only show assets assigned to this location
    filteredAssets = assets.filter((a: any) => a.current_location_id === selectedLocationId);
  }

  let filteredLocations = locations;
  if (selectedAssetId) {
    // If an asset is selected and assigned to a location, we can show that specific location
    const asset = assets.find((a: any) => a.asset_id === selectedAssetId);
    if (asset && asset.current_location_id) {
      filteredLocations = locations.filter((l: any) => l.location_id === asset.current_location_id);
    }
  }

  React.useEffect(() => {
    if (selectedAssetId) {
      const asset = assets.find((a: any) => a.asset_id === selectedAssetId);
      if (asset?.current_location_id && asset.current_location_id !== selectedLocationId) {
        setValue('location_id', asset.current_location_id, { shouldValidate: true });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAssetId, assets, setValue]);

  React.useEffect(() => {
    if (selectedLocationId && selectedAssetId) {
      const asset = assets.find((a: any) => a.asset_id === selectedAssetId);
      if (asset && asset.current_location_id !== selectedLocationId) {
        setValue('asset_id', '', { shouldValidate: true });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedLocationId, assets, setValue]);

  const mutation = useMutation({
    mutationFn: async (data: any) => api.post('/maintenance', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['maintenance'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      toast.success('Maintenance ticket created!');
      reset();
      onClose();
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to create ticket');
    },
  });

  const handleScan = (decodedText: string) => {
    setScannerOpen(false);
    let extractedId = decodedText.trim();
    try {
      const parsed = JSON.parse(decodedText);
      if (parsed.asset_id) extractedId = parsed.asset_id;
      else if (parsed.location_id) extractedId = parsed.location_id;
      else if (parsed.id) extractedId = parsed.id;
    } catch(e) {
      if (extractedId.startsWith('http')) {
        const parts = extractedId.split('/');
        extractedId = parts[parts.length - 1];
      }
    }

    const matchedAsset = assets.find((a: any) => a.asset_id === extractedId || a.asset_id === decodedText);
    if (matchedAsset) {
      setScanResult({ type: 'Asset', data: matchedAsset });
      return;
    }
    
    const matchedLocation = locations.find((l: any) => l.location_id === extractedId || l.location_id === decodedText || l.qr_code === decodedText);
    if (matchedLocation) {
      setScanResult({ type: 'Location', data: matchedLocation });
      return;
    }

    setScanResult({ type: 'Unknown', data: null });
  };

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
        <form onSubmit={handleSubmit((d) => mutation.mutate(d))}>
          <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            Create Maintenance Ticket
            <Button 
              variant="outlined" 
              color="primary" 
              size="small" 
              startIcon={<Camera size={16} />} 
              onClick={() => setScannerOpen(true)}
            >
              Scan QR Code
            </Button>
          </DialogTitle>
          <DialogContent dividers>
          <Grid container spacing={2} sx={{ pt: 1 }}>
            <Grid item xs={12} sm={6}>
              <Controller
                name="asset_id"
                control={control}
                render={({ field: { onChange, value, ref } }) => {
                  const selectedOption = filteredAssets.find((a: any) => a.asset_id === value) || value || null;
                  return (
                    <Autocomplete
                      freeSolo
                      options={filteredAssets}
                      getOptionLabel={(option) => typeof option === 'string' ? option : option.asset_id}
                      value={selectedOption}
                      onChange={(_, newValue) => {
                        onChange(typeof newValue === 'string' ? newValue : newValue?.asset_id || '');
                      }}
                      onInputChange={(_, newInputValue, reason) => {
                        if (reason === 'input' || reason === 'clear') {
                          onChange(newInputValue);
                        }
                      }}
                      renderInput={(params) => (
                        <TextField 
                          {...params} 
                          inputRef={ref}
                          label="Asset ID" 
                          placeholder="e.g. AST-001" 
                        />
                      )}
                      renderOption={(props, option: any) => {
                        const { key, ...otherProps } = props as any;
                        return (
                          <li key={option.asset_id} {...otherProps}>
                            <Box>
                              <Typography variant="body2" fontWeight="bold">{option.asset_id}</Typography>
                              <Typography variant="caption" color="text.secondary">
                                {option.current_location_id || 'Unassigned'} • {option.asset_type || 'Unknown'} {option.capacity ? `• ${option.capacity}` : ''}
                              </Typography>
                            </Box>
                          </li>
                        );
                      }}
                      noOptionsText={selectedLocationId ? "No assets assigned to this location" : "No matching assets found"}
                    />
                  );
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Controller
                name="location_id"
                control={control}
                render={({ field: { onChange, value, ref } }) => {
                  const selectedOption = filteredLocations.find((l: any) => l.location_id === value) || value || null;
                  return (
                    <Autocomplete
                      freeSolo
                      options={filteredLocations}
                      getOptionLabel={(option) => typeof option === 'string' ? option : option.location_id}
                      value={selectedOption}
                      onChange={(_, newValue) => {
                        onChange(typeof newValue === 'string' ? newValue : newValue?.location_id || '');
                      }}
                      onInputChange={(_, newInputValue, reason) => {
                        if (reason === 'input' || reason === 'clear') {
                          onChange(newInputValue);
                        }
                      }}
                      renderInput={(params) => (
                        <TextField 
                          {...params} 
                          inputRef={ref}
                          label="Location ID" 
                          placeholder="e.g. LOC-001" 
                        />
                      )}
                      renderOption={(props, option: any) => {
                        const { key, ...otherProps } = props as any;
                        return (
                          <li key={option.location_id} {...otherProps}>
                            <Box>
                              <Typography variant="body2" fontWeight="bold">{option.location_id}</Typography>
                              <Typography variant="caption" color="text.secondary">
                                {option.location_name} • {option.building || 'Unknown Bldg'} • {option.floor || 'Unknown Floor'}
                              </Typography>
                            </Box>
                          </li>
                        );
                      }}
                      noOptionsText="No matching locations found"
                    />
                  );
                }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Issue Description *"
                {...register('issue', { required: true })}
                multiline
                rows={3}
                required
                placeholder="Describe the problem..."
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Priority</InputLabel>
                <Controller
                  name="priority"
                  control={control}
                  render={({ field }) => (
                    <Select {...field} label="Priority">
                      <MenuItem value="Critical">🔴 Critical</MenuItem>
                      <MenuItem value="High">🟠 High</MenuItem>
                      <MenuItem value="Medium">🟡 Medium</MenuItem>
                      <MenuItem value="Low">🟢 Low</MenuItem>
                    </Select>
                  )}
                />
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField fullWidth label="Assigned To" {...register('assigned_to')} placeholder="Technician name or ID" />
            </Grid>
            <Grid item xs={12}>
              <TextField fullWidth label="Remarks" {...register('remarks')} multiline rows={2} />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={mutation.isPending}>
            {mutation.isPending ? 'Creating...' : 'Create Ticket'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>

    <QRScannerDialog 
      open={scannerOpen}
      onClose={() => setScannerOpen(false)}
      onScan={handleScan}
    />

    <Dialog open={!!scanResult} onClose={() => setScanResult(null)} maxWidth="xs" fullWidth>
      <DialogTitle>
        {scanResult?.type === 'Unknown' ? 'QR Code Not Recognized' : 'QR Code Detected'}
      </DialogTitle>
      <DialogContent dividers>
        {scanResult?.type === 'Unknown' ? (
          <Typography>Please scan a valid Asset or Location QR code.</Typography>
        ) : scanResult?.type === 'Asset' ? (
          <Box>
            <Typography variant="body2" color="text.secondary">Type</Typography>
            <Typography fontWeight="bold" mb={2}>Asset</Typography>
            
            <Typography variant="body2" color="text.secondary">Asset ID</Typography>
            <Typography fontWeight="bold" mb={2}>{scanResult.data.asset_id}</Typography>
            
            <Typography variant="body2" color="text.secondary">Location</Typography>
            <Typography fontWeight="bold">{scanResult.data.current_location_id || 'Unassigned'}</Typography>
          </Box>
        ) : scanResult?.type === 'Location' ? (
          <Box>
            <Typography variant="body2" color="text.secondary">Type</Typography>
            <Typography fontWeight="bold" mb={2}>Location</Typography>
            
            <Typography variant="body2" color="text.secondary">Location ID</Typography>
            <Typography fontWeight="bold" mb={2}>{scanResult.data.location_id}</Typography>
            
            <Typography variant="body2" color="text.secondary">Location Name</Typography>
            <Typography fontWeight="bold" mb={2}>{scanResult.data.location_name}</Typography>
            
            <Typography variant="body2" color="text.secondary">Assets found</Typography>
            <Typography fontWeight="bold">{assets.filter((a: any) => a.current_location_id === scanResult.data.location_id).length}</Typography>
          </Box>
        ) : null}
      </DialogContent>
      <DialogActions>
        {scanResult?.type === 'Unknown' ? (
          <>
            <Button onClick={() => setScanResult(null)}>Cancel</Button>
            <Button variant="contained" onClick={() => { setScanResult(null); setScannerOpen(true); }}>Scan Again</Button>
          </>
        ) : (
          <>
            <Button onClick={() => { setScanResult(null); setScannerOpen(true); }}>Scan Again</Button>
            <Button variant="contained" onClick={() => {
              if (scanResult?.type === 'Asset') {
                setValue('asset_id', scanResult.data.asset_id, { shouldValidate: true });
              } else if (scanResult?.type === 'Location') {
                setValue('location_id', scanResult.data.location_id, { shouldValidate: true });
              }
              setScanResult(null);
            }}>Use This Data</Button>
          </>
        )}
      </DialogActions>
    </Dialog>
    </>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────
const Maintenance: React.FC = () => {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterPriority, setFilterPriority] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [detailTicket, setDetailTicket] = useState<MaintenanceTicket | null>(null);

  // GET /maintenance — returns raw array
  const { data: ticketsRaw, isLoading, isError } = useQuery({
    queryKey: ['maintenance', filterStatus, filterPriority],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (filterStatus) params.status = filterStatus;
      if (filterPriority) params.priority = filterPriority;
      const res = await api.get('/maintenance', { params: { ...params, limit: 500 } });
      return Array.isArray(res.data?.data) ? res.data.data : [];
    },
  });

  const tickets: MaintenanceTicket[] = Array.isArray(ticketsRaw) ? ticketsRaw : [];

  const filtered = tickets.filter((t) => {
    const term = search.toLowerCase();
    if (!term) return true;
    return (
      String(t.maintenance_id).includes(term) ||
      (t.asset_id?.toLowerCase() ?? '').includes(term) ||
      (t.location_id?.toLowerCase() ?? '').includes(term) ||
      (t.issue?.toLowerCase() ?? '').includes(term) ||
      (t.assigned_to?.toLowerCase() ?? '').includes(term)
    );
  });

  const paginated = filtered.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  const openCount = tickets.filter((t) => !['Closed', 'Verified'].includes(t.status)).length;
  const criticalCount = tickets.filter((t) => t.priority === 'Critical' && t.status !== 'Closed').length;

  if (isError) {
    return (
      <Box p={4}>
        <Typography color="error">Failed to load maintenance tickets.</Typography>
        <Button variant="outlined" sx={{ mt: 2 }} onClick={() => queryClient.invalidateQueries({ queryKey: ['maintenance'] })}>Retry</Button>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" fontWeight="bold">Maintenance</Typography>
          <Typography variant="body2" color="text.secondary">
            {tickets.length} total · {openCount} open · {criticalCount} critical
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<Plus size={18} />} onClick={() => setCreateOpen(true)}>
          Create Ticket
        </Button>
      </Box>

      {/* Filters */}
      <Box display="flex" gap={2} mb={3} flexWrap="wrap">
        <TextField
          label="Search"
          size="small"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(0); }}
          sx={{ width: 260 }}
          InputProps={{
            startAdornment: <InputAdornment position="start"><Search size={16} /></InputAdornment>,
          }}
        />
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>Status</InputLabel>
          <Select value={filterStatus} label="Status" onChange={(e) => { setFilterStatus(e.target.value); setPage(0); }}>
            <MenuItem value=""><em>All</em></MenuItem>
            <MenuItem value="Open">Open</MenuItem>
            <MenuItem value="In Progress">In Progress</MenuItem>
            <MenuItem value="Waiting Parts">Waiting Parts</MenuItem>
            <MenuItem value="Completed">Completed</MenuItem>
            <MenuItem value="Verified">Verified</MenuItem>
            <MenuItem value="Closed">Closed</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel>Priority</InputLabel>
          <Select value={filterPriority} label="Priority" onChange={(e) => { setFilterPriority(e.target.value); setPage(0); }}>
            <MenuItem value=""><em>All</em></MenuItem>
            <MenuItem value="Critical">Critical</MenuItem>
            <MenuItem value="High">High</MenuItem>
            <MenuItem value="Medium">Medium</MenuItem>
            <MenuItem value="Low">Low</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Table */}
      <Card>
        <TableContainer>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>#</TableCell>
                <TableCell>Asset</TableCell>
                <TableCell>Location</TableCell>
                <TableCell>Issue</TableCell>
                <TableCell>Priority</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Assigned To</TableCell>
                <TableCell>Opened</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={9} align="center" sx={{ py: 5 }}><CircularProgress /></TableCell>
                </TableRow>
              ) : paginated.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">
                      {search || filterStatus || filterPriority
                        ? 'No tickets match your filters.'
                        : 'No maintenance tickets yet.'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                paginated.map((ticket) => (
                  <TableRow key={ticket.maintenance_id} hover>
                    <TableCell sx={{ fontFamily: 'monospace' }}>#{ticket.maintenance_id}</TableCell>
                    <TableCell>{ticket.asset_id ?? '—'}</TableCell>
                    <TableCell>{ticket.location_id ?? '—'}</TableCell>
                    <TableCell>
                      <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
                        {ticket.issue ?? '—'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={ticket.priority} color={PRIORITY_COLOR[ticket.priority]} size="small" />
                    </TableCell>
                    <TableCell>
                      <Chip label={ticket.status} color={STATUS_COLOR[ticket.status]} size="small" />
                    </TableCell>
                    <TableCell>{ticket.assigned_to ?? '—'}</TableCell>
                    <TableCell>{new Date(ticket.opened_date).toLocaleDateString()}</TableCell>
                    <TableCell align="right">
                      <Tooltip title="View Details / Update Status">
                        <IconButton size="small" color="primary" onClick={() => setDetailTicket(ticket)}>
                          <Eye size={16} />
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

      <CreateTicketDialog open={createOpen} onClose={() => setCreateOpen(false)} />
      <TicketDetailDialog
        ticket={detailTicket}
        open={!!detailTicket}
        onClose={() => setDetailTicket(null)}
      />
    </Box>
  );
};

export default Maintenance;
