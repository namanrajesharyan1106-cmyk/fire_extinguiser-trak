import React, { useState } from 'react';
import {
  Box, Typography, Card, Button, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, IconButton, Dialog,
  DialogTitle, DialogContent, DialogActions, TextField,
  CircularProgress, TablePagination, InputAdornment, Chip,
  Tooltip, FormControl, InputLabel, Select, MenuItem,
  Grid, Divider, ToggleButton, ToggleButtonGroup, Alert, Paper
} from '@mui/material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Search, Eye, ClipboardCheck, Clock, CheckCircle, XCircle, Scan } from 'lucide-react';
import { useForm, Controller } from 'react-hook-form';
import { Html5QrcodeScanner } from 'html5-qrcode';
import api from '../api/axios';
import { toast } from 'react-toastify';

// ─── Types ───────────────────────────────────────────────────────────────────
interface Inspection {
  inspection_id: number;
  inspection_no: string | null;
  location_id: string;
  asset_id: string | null;
  inspector: string | null;
  overall_status: string | null;
  inspection_date: string;
  pressure: string | null;
  seal: string | null;
  pin: string | null;
  gauge: string | null;
  hose: string | null;
  nozzle: string | null;
  visibility: string | null;
  accessibility: string | null;
  mounting: string | null;
  safety_tag: string | null;
  cylinder_damage: string | null;
  remarks: string | null;
}

interface Location {
  location_id: string;
  location_name: string;
}

// ─── Checklist fields ─────────────────────────────────────────────────────────
const CHECKLIST_FIELDS = [
  { key: 'pressure', label: 'Pressure Gauge' },
  { key: 'seal', label: 'Safety Seal' },
  { key: 'pin', label: 'Safety Pin' },
  { key: 'gauge', label: 'Gauge Indicator' },
  { key: 'hose', label: 'Hose Condition' },
  { key: 'nozzle', label: 'Nozzle Condition' },
  { key: 'visibility', label: 'Visibility / Signage' },
  { key: 'accessibility', label: 'Accessibility' },
  { key: 'mounting', label: 'Mounting Bracket' },
  { key: 'safety_tag', label: 'Safety Tag Present' },
  { key: 'cylinder_damage', label: 'Cylinder Damage' },
];

// ─── Status helpers ───────────────────────────────────────────────────────────
const StatusChip = ({ status }: { status: string | null }) => {
  if (!status) return <Chip label="Pending" size="small" />;
  if (status === 'Pass') return <Chip label="Pass" color="success" size="small" icon={<CheckCircle size={12} />} />;
  if (status === 'Fail') return <Chip label="Fail" color="error" size="small" icon={<XCircle size={12} />} />;
  return <Chip label={status} size="small" />;
};

// ─── Inspection Detail Dialog ─────────────────────────────────────────────────
const InspectionDetailDialog: React.FC<{
  inspection: Inspection | null;
  open: boolean;
  onClose: () => void;
}> = ({ inspection, open, onClose }) => {
  if (!inspection) return null;
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Inspection {inspection.inspection_no ? `#${inspection.inspection_no}` : `#${inspection.inspection_id}`} — {inspection.overall_status}
      </DialogTitle>
      <DialogContent dividers>
        <Grid container spacing={2} mb={2}>
          <Grid item xs={6}>
            <Typography variant="caption" color="text.secondary">Location</Typography>
            <Typography fontWeight="bold">{inspection.location_id}</Typography>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="caption" color="text.secondary">Asset</Typography>
            <Typography fontWeight="bold">{inspection.asset_id ?? 'N/A'}</Typography>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="caption" color="text.secondary">Inspector</Typography>
            <Typography>{inspection.inspector ?? '—'}</Typography>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="caption" color="text.secondary">Date</Typography>
            <Typography>{new Date(inspection.inspection_date).toLocaleDateString()}</Typography>
          </Grid>
        </Grid>
        <Divider sx={{ mb: 2 }} />
        <Typography variant="subtitle2" fontWeight="bold" mb={1}>Checklist Results</Typography>
        <Grid container spacing={1}>
          {CHECKLIST_FIELDS.map(({ key, label }) => {
            const val = (inspection as any)[key];
            return (
              <Grid item xs={6} key={key}>
                <Box display="flex" alignItems="center" gap={1} py={0.5}>
                  {val === 'OK' || val === 'Good' || val === 'Present' || val === 'Accessible' || val === 'Secure' || val === 'Pass' ? (
                    <CheckCircle size={14} color="#36B37E" />
                  ) : val ? (
                    <XCircle size={14} color="#FF5630" />
                  ) : (
                    <Clock size={14} color="#FFAB00" />
                  )}
                  <Typography variant="body2">{label}: <strong>{val ?? 'N/A'}</strong></Typography>
                </Box>
              </Grid>
            );
          })}
        </Grid>
        {inspection.remarks && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="caption" color="text.secondary">Remarks</Typography>
            <Typography variant="body2">{inspection.remarks}</Typography>
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

const CHECKLIST_OPTIONS = ['OK', 'Damaged', 'Missing', 'Needs Attention'];

const InspectionFormDialog: React.FC<{
  open: boolean;
  onClose: () => void;
}> = ({ open, onClose }) => {
  const queryClient = useQueryClient();
  const [step, setStep] = React.useState<'init' | 'scan' | 'loading' | 'form'>('init');
  const [scanError, setScanError] = React.useState('');
  const [assetData, setAssetData] = React.useState<any>(null);

  const { register, handleSubmit, reset, control } = useForm<any>({
    defaultValues: {
      inspector: '',
      pressure: 'OK', seal: 'OK', pin: 'OK', gauge: 'OK',
      hose: 'OK', nozzle: 'OK', visibility: 'OK',
      accessibility: 'OK', mounting: 'OK',
      safety_tag: 'OK', cylinder_damage: 'OK',
      remarks: '',
    },
  });

  const handleClose = () => {
    reset();
    setStep('init');
    setScanError('');
    setAssetData(null);
    onClose();
  };

  React.useEffect(() => {
    if (step === 'scan') {
      const scanner = new Html5QrcodeScanner('reader', { fps: 10, qrbox: { width: 250, height: 250 } }, false);
      scanner.render(
        async (decodedText) => {
          scanner.clear();
          setStep('loading');
          try {
            const parsed = (() => { try { return JSON.parse(decodedText).id || decodedText } catch { return decodedText } })();
            const res = await api.get(`/assets/by-qr/${encodeURIComponent(parsed)}`);
            if (res.data?.data?.asset) {
              setAssetData(res.data.data);
              setStep('form');
            } else {
              setScanError('Asset not found for this QR code.');
              setStep('init');
            }
          } catch (err: any) {
            setScanError(err.response?.data?.detail || 'Asset not found or invalid QR code.');
            setStep('init');
          }
        },
        () => {}
      );
      return () => { scanner.clear().catch(console.error); };
    }
  }, [step]);

  const mutation = useMutation({
    mutationFn: async (data: any) => {
      const payload = {
        ...data,
        asset_id: assetData.asset?.asset_id,
        location_id: assetData.location?.location_id,
      };
      return api.post('/inspections', payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inspections'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      toast.success('Inspection submitted successfully!');
      handleClose();
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Failed to submit inspection');
    },
  });

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>New Inspection</DialogTitle>
      <DialogContent dividers sx={{ minHeight: 400 }}>
        {step === 'init' && (
          <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" height="100%" gap={3} py={5}>
            <Scan size={64} color="#94a3b8" />
            <Typography variant="h6" color="text.secondary">Scan QR Code to begin inspection</Typography>
            {scanError && <Alert severity="error">{scanError}</Alert>}
            <Button variant="contained" size="large" onClick={() => setStep('scan')} startIcon={<Scan />}>
              Open Camera
            </Button>
          </Box>
        )}

        {step === 'scan' && (
          <Box display="flex" flexDirection="column" alignItems="center">
            <Typography mb={2}>Point camera at the Asset QR Code</Typography>
            <Box id="reader" sx={{ width: '100%', maxWidth: 400 }} />
            <Button sx={{ mt: 3 }} onClick={() => setStep('init')}>Cancel Scan</Button>
          </Box>
        )}

        {step === 'loading' && (
          <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" height="100%" gap={2} py={5}>
            <CircularProgress />
            <Typography>Fetching Asset Details...</Typography>
          </Box>
        )}

        {step === 'form' && assetData && (
          <form onSubmit={handleSubmit((d) => mutation.mutate(d))} id="insp-form">
            <Paper variant="outlined" sx={{ p: 2, mb: 3, bgcolor: '#f8fafc' }}>
              <Typography variant="subtitle2" fontWeight="bold" mb={2} color="primary">Asset Details</Typography>
              <Grid container spacing={2}>
                <Grid item xs={6} sm={3}><Typography variant="caption" color="text.secondary">Asset ID</Typography><Typography variant="body2" fontWeight={600}>{assetData.asset.asset_id}</Typography></Grid>
                <Grid item xs={6} sm={3}><Typography variant="caption" color="text.secondary">Asset Type</Typography><Typography variant="body2">{assetData.asset.asset_type || '—'}</Typography></Grid>
                <Grid item xs={6} sm={3}><Typography variant="caption" color="text.secondary">Capacity</Typography><Typography variant="body2">{assetData.asset.capacity || '—'}</Typography></Grid>
                <Grid item xs={6} sm={3}><Typography variant="caption" color="text.secondary">Location</Typography><Typography variant="body2">{assetData.location?.location_id || 'Unassigned'}</Typography></Grid>
                <Grid item xs={6} sm={3}><Typography variant="caption" color="text.secondary">Serial Number</Typography><Typography variant="body2">{assetData.asset.serial_number || '—'}</Typography></Grid>
                <Grid item xs={6} sm={3}><Typography variant="caption" color="text.secondary">Current Status</Typography><Typography variant="body2">{assetData.asset.status || '—'}</Typography></Grid>
                <Grid item xs={6} sm={3}><Typography variant="caption" color="text.secondary">Last Inspection</Typography><Typography variant="body2">{assetData.inspection?.last_inspection_date ? new Date(assetData.inspection.last_inspection_date).toLocaleDateString() : 'Never'}</Typography></Grid>
                <Grid item xs={6} sm={3}><Typography variant="caption" color="text.secondary">Next Due</Typography><Typography variant="body2">{assetData.inspection?.next_inspection_due ? new Date(assetData.inspection.next_inspection_due).toLocaleDateString() : '—'}</Typography></Grid>
              </Grid>
            </Paper>

            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField fullWidth label="Inspector Name" {...register('inspector')} />
              </Grid>

              <Grid item xs={12}>
                <Divider />
                <Typography variant="subtitle2" fontWeight="bold" mt={2} mb={1}>
                  Checklist (select condition for each item)
                </Typography>
              </Grid>

              {CHECKLIST_FIELDS.map(({ key, label }) => (
                <Grid item xs={12} sm={6} key={key}>
                  <Typography variant="body2" fontWeight={600} mb={0.5}>{label}</Typography>
                  <Controller
                    name={key}
                    control={control}
                    render={({ field }) => (
                      <ToggleButtonGroup exclusive value={field.value} onChange={(_, val) => { if (val) field.onChange(val); }} size="small">
                        {CHECKLIST_OPTIONS.map((opt) => (
                          <ToggleButton
                            key={opt} value={opt}
                            sx={{
                              fontSize: 11,
                              '&.Mui-selected': { bgcolor: opt === 'OK' ? '#e3fcef' : '#ffebe6', color: opt === 'OK' ? '#36B37E' : '#FF5630', fontWeight: 'bold' },
                            }}
                          >
                            {opt}
                          </ToggleButton>
                        ))}
                      </ToggleButtonGroup>
                    )}
                  />
                </Grid>
              ))}

              <Grid item xs={12}>
                <TextField fullWidth label="Remarks" multiline rows={2} {...register('remarks')} placeholder="Any additional notes..." />
              </Grid>

              <Grid item xs={12}>
                <Alert severity="info" sx={{ fontSize: 12 }}>
                  Overall Pass/Fail status is auto-calculated by the backend. If FAIL, a Maintenance Ticket is automatically created.
                </Alert>
              </Grid>
            </Grid>
          </form>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        {step === 'form' && (
          <Button type="submit" form="insp-form" variant="contained" disabled={mutation.isPending} startIcon={<ClipboardCheck size={16} />}>
            {mutation.isPending ? 'Submitting...' : 'Submit Inspection'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────
const Inspections: React.FC = () => {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [detailInspection, setDetailInspection] = useState<Inspection | null>(null);

  // Inspections — returns raw array
  const { data: inspectionsRaw, isLoading, isError } = useQuery({
    queryKey: ['inspections', filterStatus],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (filterStatus) params.overall_status = filterStatus;
      const res = await api.get('/inspections', { params: { ...params, limit: 500 } });
      return Array.isArray(res.data?.data) ? res.data.data : [];
    },
  });

  const inspections: Inspection[] = Array.isArray(inspectionsRaw) ? inspectionsRaw : [];

  // Client-side filter + search
  const filtered = inspections.filter((ins) => {
    const term = search.toLowerCase();
    if (!term) return true;
    return (
      (ins.inspection_no?.toLowerCase() ?? '').includes(term) ||
      ins.location_id.toLowerCase().includes(term) ||
      (ins.asset_id?.toLowerCase() ?? '').includes(term) ||
      (ins.inspector?.toLowerCase() ?? '').includes(term)
    );
  });

  const paginated = filtered.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  const passCount = inspections.filter((i) => i.overall_status === 'Pass').length;
  const failCount = inspections.filter((i) => i.overall_status === 'Fail').length;

  if (isError) {
    return (
      <Box p={4}>
        <Typography color="error">Failed to load inspections.</Typography>
        <Button variant="outlined" sx={{ mt: 2 }} onClick={() => queryClient.invalidateQueries({ queryKey: ['inspections'] })}>Retry</Button>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" fontWeight="bold">Inspections</Typography>
          <Typography variant="body2" color="text.secondary">
            {inspections.length} total · {passCount} passed · {failCount} failed
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<Plus size={18} />} onClick={() => setFormOpen(true)}>
          New Inspection
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
            <MenuItem value="Pass">Pass</MenuItem>
            <MenuItem value="Fail">Fail</MenuItem>
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
                <TableCell>Location</TableCell>
                <TableCell>Asset</TableCell>
                <TableCell>Inspector</TableCell>
                <TableCell>Date</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Remarks</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 5 }}><CircularProgress /></TableCell>
                </TableRow>
              ) : paginated.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">
                      {search || filterStatus ? 'No results match your filters.' : 'No inspections yet. Submit your first inspection!'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                paginated.map((ins) => (
                  <TableRow key={ins.inspection_id} hover>
                    <TableCell sx={{ fontFamily: 'monospace' }}>{ins.inspection_no ? ins.inspection_no : `#${ins.inspection_id}`}</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>{ins.location_id}</TableCell>
                    <TableCell>{ins.asset_id ?? '—'}</TableCell>
                    <TableCell>{ins.inspector ?? '—'}</TableCell>
                    <TableCell>{new Date(ins.inspection_date).toLocaleDateString()}</TableCell>
                    <TableCell><StatusChip status={ins.overall_status} /></TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary" noWrap sx={{ maxWidth: 150, display: 'block' }}>
                        {ins.remarks ?? '—'}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="View Details">
                        <IconButton size="small" color="primary" onClick={() => setDetailInspection(ins)}>
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

      {/* Form Dialog */}
      <InspectionFormDialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
      />

      {/* Detail Dialog */}
      <InspectionDetailDialog
        inspection={detailInspection}
        open={!!detailInspection}
        onClose={() => setDetailInspection(null)}
      />
    </Box>
  );
};

export default Inspections;
