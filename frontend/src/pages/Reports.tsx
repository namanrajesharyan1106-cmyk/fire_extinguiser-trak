import React, { useState } from 'react';
import {
  Box, Typography, Card, Button, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, CircularProgress,
  TextField, FormControl, InputLabel, Select, MenuItem,
  Chip, Tabs, Tab, Alert,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { Download, FileText, RefreshCw } from 'lucide-react';
import api from '../api/axios';
import { toast } from 'react-toastify';

// ─── Excel Export Utility ─────────────────────────────────────────────────────
const exportToExcel = async (data: any[], filename: string) => {
  try {
    const XLSX = await import('xlsx');
    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Report');
    XLSX.writeFile(wb, `${filename}.xlsx`);
    toast.success(`${filename}.xlsx downloaded!`);
  } catch {
    toast.error('Excel export failed');
  }
};

// ─── TabPanel helper ──────────────────────────────────────────────────────────
const TabPanel: React.FC<{ value: number; index: number; children: React.ReactNode }> = ({
  value, index, children,
}) => (
  <div hidden={value !== index}>
    {value === index && <Box pt={3}>{children}</Box>}
  </div>
);

// ─── Asset Register Report ────────────────────────────────────────────────────
const AssetRegisterReport: React.FC = () => {
  const [plant, setPlant] = useState('');
  const [status, setStatus] = useState('');
  const [assetType, setAssetType] = useState('');

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['report-assets', plant, status, assetType],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (plant) params.plant = plant;
      if (status) params.status = status;
      if (assetType) params.asset_type = assetType;
      const res = await api.get('/reports/asset-register', { params });
      return res.data?.data; // {count, data: [...]}
    },
  });

  const rows = Array.isArray(data?.data) ? data.data : [];

  return (
    <Box>
      <Box display="flex" gap={2} flexWrap="wrap" mb={3}>
        <TextField size="small" label="Plant" value={plant} onChange={(e) => setPlant(e.target.value)} sx={{ width: 180 }} />
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Status</InputLabel>
          <Select value={status} label="Status" onChange={(e) => setStatus(e.target.value)}>
            <MenuItem value=""><em>All</em></MenuItem>
            <MenuItem value="Active">Active</MenuItem>
            <MenuItem value="Expired">Expired</MenuItem>
            <MenuItem value="Retired">Retired</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel>Type</InputLabel>
          <Select value={assetType} label="Type" onChange={(e) => setAssetType(e.target.value)}>
            <MenuItem value=""><em>All</em></MenuItem>
            <MenuItem value="CO2">CO2</MenuItem>
            <MenuItem value="DCP">DCP</MenuItem>
            <MenuItem value="Foam">Foam</MenuItem>
          </Select>
        </FormControl>
        <Button variant="outlined" startIcon={<RefreshCw size={16} />} onClick={() => refetch()}>
          Refresh
        </Button>
        <Button
          variant="contained"
          startIcon={<Download size={16} />}
          disabled={rows.length === 0}
          onClick={() => exportToExcel(rows, 'Asset_Register')}
        >
          Export Excel
        </Button>
      </Box>
      <Typography variant="body2" color="text.secondary" mb={2}>{data?.count ?? 0} records</Typography>
      <TableContainer component={Card}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>Asset ID</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>S/N</TableCell>
              <TableCell>Expiry</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Location</TableCell>
              <TableCell>Plant</TableCell>
              <TableCell>Department</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={8} align="center" sx={{ py: 4 }}><CircularProgress /></TableCell></TableRow>
            ) : rows.length === 0 ? (
              <TableRow><TableCell colSpan={8} align="center" sx={{ py: 4 }}><Typography color="text.secondary">No data</Typography></TableCell></TableRow>
            ) : (
              rows.map((row: any, idx: number) => (
                <TableRow key={idx} hover>
                  <TableCell sx={{ fontFamily: 'monospace' }}>{row.asset_id}</TableCell>
                  <TableCell>{row.asset_type} {row.capacity}</TableCell>
                  <TableCell>{row.serial_number}</TableCell>
                  <TableCell sx={{ color: row.expiry_date && new Date(row.expiry_date) < new Date() ? 'error.main' : 'inherit' }}>
                    {row.expiry_date ?? '—'}
                  </TableCell>
                  <TableCell><Chip label={row.status} size="small" color={row.status === 'Active' ? 'success' : 'default'} /></TableCell>
                  <TableCell>{row.location_name ?? '—'}</TableCell>
                  <TableCell>{row.plant ?? '—'}</TableCell>
                  <TableCell>{row.department ?? '—'}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

// ─── Expired Assets Report ────────────────────────────────────────────────────
const ExpiredAssetsReport: React.FC = () => {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['report-expired'],
    queryFn: async () => {
      const res = await api.get('/reports/expired-assets');
      return res.data?.data;
    },
  });
  const rows = Array.isArray(data?.data) ? data.data : [];

  return (
    <Box>
      <Box display="flex" gap={2} mb={3}>
        <Button variant="outlined" startIcon={<RefreshCw size={16} />} onClick={() => refetch()}>Refresh</Button>
        <Button
          variant="contained"
          startIcon={<Download size={16} />}
          disabled={rows.length === 0}
          onClick={() => exportToExcel(rows, 'Expired_Assets')}
        >
          Export Excel
        </Button>
      </Box>
      {rows.length > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {rows.length} expired asset{rows.length > 1 ? 's' : ''} found. Immediate action required.
        </Alert>
      )}
      <TableContainer component={Card}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>Asset ID</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>S/N</TableCell>
              <TableCell>Expiry Date</TableCell>
              <TableCell>Days Expired</TableCell>
              <TableCell>Location</TableCell>
              <TableCell>Department</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={7} align="center" sx={{ py: 4 }}><CircularProgress /></TableCell></TableRow>
            ) : rows.length === 0 ? (
              <TableRow><TableCell colSpan={7} align="center" sx={{ py: 4 }}><Typography color="text.secondary">No expired assets</Typography></TableCell></TableRow>
            ) : (
              rows.map((row: any, idx: number) => (
                <TableRow key={idx} hover>
                  <TableCell sx={{ fontFamily: 'monospace' }}>{row.asset_id}</TableCell>
                  <TableCell>{row.asset_type}</TableCell>
                  <TableCell>{row.serial_number}</TableCell>
                  <TableCell sx={{ color: 'error.main' }}>{row.expiry_date}</TableCell>
                  <TableCell><Chip label={`${row.days_expired}d`} color="error" size="small" /></TableCell>
                  <TableCell>{row.location ?? 'Unassigned'}</TableCell>
                  <TableCell>{row.department ?? '—'}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

// ─── Inspection History Report ────────────────────────────────────────────────
const InspectionHistoryReport: React.FC = () => {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [overallStatus, setOverallStatus] = useState('');

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['report-inspections', startDate, endDate, overallStatus],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      if (overallStatus) params.overall_status = overallStatus;
      const res = await api.get('/reports/inspection-history', { params });
      return res.data?.data;
    },
  });
  const rows = Array.isArray(data?.data) ? data.data : [];

  return (
    <Box>
      <Box display="flex" gap={2} flexWrap="wrap" mb={3}>
        <TextField size="small" type="date" label="Start Date" InputLabelProps={{ shrink: true }} value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        <TextField size="small" type="date" label="End Date" InputLabelProps={{ shrink: true }} value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        <FormControl size="small" sx={{ minWidth: 130 }}>
          <InputLabel>Status</InputLabel>
          <Select value={overallStatus} label="Status" onChange={(e) => setOverallStatus(e.target.value)}>
            <MenuItem value=""><em>All</em></MenuItem>
            <MenuItem value="Pass">Pass</MenuItem>
            <MenuItem value="Fail">Fail</MenuItem>
          </Select>
        </FormControl>
        <Button variant="outlined" startIcon={<RefreshCw size={16} />} onClick={() => refetch()}>Refresh</Button>
        <Button
          variant="contained"
          startIcon={<Download size={16} />}
          disabled={rows.length === 0}
          onClick={() => exportToExcel(rows, 'Inspection_History')}
        >
          Export Excel
        </Button>
      </Box>
      <Typography variant="body2" color="text.secondary" mb={2}>{data?.count ?? 0} records</Typography>
      <TableContainer component={Card}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>#</TableCell>
              <TableCell>Location</TableCell>
              <TableCell>Asset</TableCell>
              <TableCell>Inspector</TableCell>
              <TableCell>Date</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Plant</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={7} align="center" sx={{ py: 4 }}><CircularProgress /></TableCell></TableRow>
            ) : rows.length === 0 ? (
              <TableRow><TableCell colSpan={7} align="center" sx={{ py: 4 }}><Typography color="text.secondary">No data for selected filters</Typography></TableCell></TableRow>
            ) : (
              rows.map((row: any, idx: number) => (
                <TableRow key={idx} hover>
                  <TableCell>#{row.inspection_id}</TableCell>
                  <TableCell>{row.location_name ?? row.location_id}</TableCell>
                  <TableCell>{row.asset_id ?? '—'}</TableCell>
                  <TableCell>{row.inspector ?? '—'}</TableCell>
                  <TableCell>{row.date ? new Date(row.date).toLocaleDateString() : '—'}</TableCell>
                  <TableCell>
                    <Chip
                      label={row.overall_status}
                      size="small"
                      color={row.overall_status === 'Pass' ? 'success' : 'error'}
                    />
                  </TableCell>
                  <TableCell>{row.plant ?? '—'}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

// ─── Pending Maintenance Report ───────────────────────────────────────────────
const MaintenancePendingReport: React.FC = () => {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['report-maintenance-pending'],
    queryFn: async () => {
      const res = await api.get('/reports/maintenance-pending');
      return res.data?.data;
    },
  });
  const rows = Array.isArray(data?.data) ? data.data : [];

  return (
    <Box>
      <Box display="flex" gap={2} mb={3}>
        <Button variant="outlined" startIcon={<RefreshCw size={16} />} onClick={() => refetch()}>Refresh</Button>
        <Button
          variant="contained"
          startIcon={<Download size={16} />}
          disabled={rows.length === 0}
          onClick={() => exportToExcel(rows, 'Pending_Maintenance')}
        >
          Export Excel
        </Button>
      </Box>
      <TableContainer component={Card}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>#</TableCell>
              <TableCell>Asset</TableCell>
              <TableCell>Location</TableCell>
              <TableCell>Issue</TableCell>
              <TableCell>Priority</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Days Open</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={7} align="center" sx={{ py: 4 }}><CircularProgress /></TableCell></TableRow>
            ) : rows.length === 0 ? (
              <TableRow><TableCell colSpan={7} align="center" sx={{ py: 4 }}><Typography color="text.secondary">No pending maintenance</Typography></TableCell></TableRow>
            ) : (
              rows.map((row: any, idx: number) => (
                <TableRow key={idx} hover>
                  <TableCell>#{row.maintenance_id}</TableCell>
                  <TableCell>{row.asset_id ?? '—'}</TableCell>
                  <TableCell>{row.location ?? '—'}</TableCell>
                  <TableCell><Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>{row.issue}</Typography></TableCell>
                  <TableCell><Chip label={row.priority} size="small" color={row.priority === 'Critical' || row.priority === 'High' ? 'error' : 'warning'} /></TableCell>
                  <TableCell><Chip label={row.status} size="small" /></TableCell>
                  <TableCell>
                    <Chip
                      label={`${row.days_open}d`}
                      size="small"
                      color={row.days_open > 7 ? 'error' : row.days_open > 3 ? 'warning' : 'default'}
                    />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

// ─── Compliance Report ────────────────────────────────────────────────────────
const ComplianceReport: React.FC = () => {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['report-compliance'],
    queryFn: async () => {
      const res = await api.get('/reports/compliance');
      return res.data?.data;
    },
  });
  const rows = Array.isArray(data?.data) ? data.data : [];

  return (
    <Box>
      <Box display="flex" gap={2} mb={3}>
        <Button variant="outlined" startIcon={<RefreshCw size={16} />} onClick={() => refetch()}>Refresh</Button>
        <Button
          variant="contained"
          startIcon={<Download size={16} />}
          disabled={rows.length === 0}
          onClick={() => exportToExcel(rows, 'Compliance_Report')}
        >
          Export Excel
        </Button>
      </Box>
      <TableContainer component={Card}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>Plant</TableCell>
              <TableCell>Department</TableCell>
              <TableCell>Total Locations</TableCell>
              <TableCell>Installed</TableCell>
              <TableCell>Uninstalled</TableCell>
              <TableCell>Compliance %</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={6} align="center" sx={{ py: 4 }}><CircularProgress /></TableCell></TableRow>
            ) : rows.length === 0 ? (
              <TableRow><TableCell colSpan={6} align="center" sx={{ py: 4 }}><Typography color="text.secondary">No data</Typography></TableCell></TableRow>
            ) : (
              rows.map((row: any, idx: number) => (
                <TableRow key={idx} hover>
                  <TableCell>{row.plant}</TableCell>
                  <TableCell>{row.department}</TableCell>
                  <TableCell>{row.total_locations}</TableCell>
                  <TableCell>{row.installed}</TableCell>
                  <TableCell sx={{ color: row.uninstalled > 0 ? 'error.main' : 'inherit' }}>{row.uninstalled}</TableCell>
                  <TableCell>
                    <Chip
                      label={`${row.compliance_percent}%`}
                      size="small"
                      color={
                        row.compliance_percent >= 90 ? 'success' :
                        row.compliance_percent >= 60 ? 'warning' : 'error'
                      }
                    />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────
const Reports: React.FC = () => {
  const [tab, setTab] = useState(0);

  const reportCards = [
    { label: 'Asset Register', count: null },
    { label: 'Expired Assets', count: null },
    { label: 'Inspection History', count: null },
    { label: 'Pending Maintenance', count: null },
    { label: 'Compliance', count: null },
  ];

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" fontWeight="bold">Reports</Typography>
          <Typography variant="body2" color="text.secondary">
            Generate, filter, and export reports. All data is live from the system.
          </Typography>
        </Box>
        <FileText size={32} color="#0052cc" />
      </Box>

      <Card>
        <Tabs
          value={tab}
          onChange={(_, v) => setTab(v)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}
        >
          {reportCards.map((r) => (
            <Tab key={r.label} label={r.label} />
          ))}
        </Tabs>

        <Box px={3} pb={3}>
          <TabPanel value={tab} index={0}><AssetRegisterReport /></TabPanel>
          <TabPanel value={tab} index={1}><ExpiredAssetsReport /></TabPanel>
          <TabPanel value={tab} index={2}><InspectionHistoryReport /></TabPanel>
          <TabPanel value={tab} index={3}><MaintenancePendingReport /></TabPanel>
          <TabPanel value={tab} index={4}><ComplianceReport /></TabPanel>
        </Box>
      </Card>
    </Box>
  );
};

export default Reports;
