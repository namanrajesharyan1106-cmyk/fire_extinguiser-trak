import React, { useState } from 'react';
import {
  Box, Typography, Card, Button, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, IconButton, Dialog,
  DialogTitle, DialogContent, DialogActions, TextField,
  CircularProgress, TablePagination, InputAdornment, Chip,
  Tooltip, Paper, Tabs, Tab
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { Search, Download, Printer, Eye } from 'lucide-react';
import { QRCodeCanvas } from 'qrcode.react';
import api from '../api/axios';
import { toast } from 'react-toastify';

// ─── Types ───────────────────────────────────────────────────────────────────
interface LocationQR {
  location_id: string;
  location_name: string;
  plant: string | null;
  building: string | null;
  floor: string | null;
  department: string | null;
  area: string | null;
  qr_code: string | null;
  current_asset_id: string | null;
  status: string;
}

interface AssetQR {
  asset_id: string;
  asset_type: string;
  serial_number: string | null;
  status: string;
  current_location_id: string | null;
}

// ─── QR Preview Dialog ────────────────────────────────────────────────────────
const QRPreviewDialog: React.FC<{
  item: any;
  type: 'location' | 'asset';
  open: boolean;
  onClose: () => void;
}> = ({ item, type, open, onClose }) => {
  const downloadQR = () => {
    if (!item) return;
    const container = document.getElementById('qr-canvas-container');
    const canvas = container?.querySelector('canvas');
    if (!canvas) {
      toast.error('Canvas not ready');
      return;
    }

    const exportCanvas = document.createElement('canvas');
    const size = 280;
    exportCanvas.width = size;
    exportCanvas.height = size + 60;
    const ctx = exportCanvas.getContext('2d')!;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);
    ctx.drawImage(canvas, 0, 0, size, size);

    ctx.fillStyle = '#172B4D';
    ctx.font = 'bold 14px Arial';
    ctx.textAlign = 'center';
    
    const id = type === 'location' ? item.location_id : item.asset_id;
    const name = type === 'location' ? item.location_name : item.asset_type;

    ctx.fillText(id, size / 2, size + 20);
    ctx.font = '12px Arial';
    ctx.fillStyle = '#5E6C84';
    ctx.fillText(name.substring(0, 40), size / 2, size + 42);

    const link = document.createElement('a');
    link.download = `QR_${id}.png`;
    link.href = exportCanvas.toDataURL('image/png');
    link.click();
  };

  const printQR = () => {
    if (!item) return;
    const win = window.open('', '_blank');
    if (!win) return;
    const id = type === 'location' ? item.location_id : item.asset_id;
    const qrValue = type === 'location' ? (item.qr_code || id) : id;
    const name = type === 'location' ? item.location_name : item.asset_type;
    
    win.document.write(`
      <html><head><title>QR - ${id}</title>
      <style>
        body { font-family: Arial, sans-serif; display: flex; flex-direction: column;
               align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
        .label { margin-top: 12px; text-align: center; }
        .id { font-size: 16px; font-weight: bold; color: #172B4D; }
        .name { font-size: 13px; color: #5E6C84; margin-top: 4px; }
      </style></head><body>
      <div id="qr"></div>
      <div class="label">
        <div class="id">${id}</div>
        <div class="name">${name}</div>
      </div>
      <script src="https://cdn.jsdelivr.net/npm/qrcode/build/qrcode.min.js"></script>
      <script>
        QRCode.toCanvas(document.createElement('canvas'), '${qrValue}', { width: 250 }, function(err, canvas) {
          if (!err) document.getElementById('qr').appendChild(canvas);
          window.onload = () => { window.print(); window.close(); };
        });
      </script></body></html>
    `);
    win.document.close();
  };

  if (!item) return null;
  const id = type === 'location' ? item.location_id : item.asset_id;
  const qrValue = type === 'location' ? (item.qr_code || id) : id;
  const name = type === 'location' ? item.location_name : item.asset_type;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>QR Code — {id}</DialogTitle>
      <DialogContent>
        <Box display="flex" flexDirection="column" alignItems="center" gap={2} py={2}>
          <Paper elevation={3} sx={{ p: 3, borderRadius: 2 }} id="qr-canvas-container">
            <QRCodeCanvas value={qrValue} size={220} level="H" includeMargin />
          </Paper>
          <Box textAlign="center">
            <Typography variant="h6" fontWeight="bold">{id}</Typography>
            <Typography variant="body2" color="text.secondary">{name}</Typography>
            <Typography variant="caption" display="block" sx={{ mt: 1, color: '#5E6C84', fontFamily: 'monospace' }}>
              Value: {qrValue}
            </Typography>
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        <Button startIcon={<Printer size={16} />} onClick={printQR} variant="outlined">Print</Button>
        <Button startIcon={<Download size={16} />} onClick={downloadQR} variant="contained">Download</Button>
      </DialogActions>
    </Dialog>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────
const QRCodes: React.FC = () => {
  const [tab, setTab] = useState(0); // 0 = Locations, 1 = Assets
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [search, setSearch] = useState('');
  
  const [previewOpen, setPreviewOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<any>(null);

  // Locations Query
  const { data: locData, isLoading: locLoading } = useQuery({
    queryKey: ['qr-locations', page, rowsPerPage, search],
    queryFn: async () => {
      const res = await api.get('/locations', {
        params: { skip: page * rowsPerPage, limit: rowsPerPage, search: search || undefined }
      });
      return res.data?.data ?? { items: [], total: 0 };
    },
    enabled: tab === 0
  });

  // Assets Query
  const { data: assetData, isLoading: assetLoading } = useQuery({
    queryKey: ['qr-assets', page, rowsPerPage, search],
    queryFn: async () => {
      const res = await api.get('/assets', {
        params: { skip: page * rowsPerPage, limit: rowsPerPage, search: search || undefined }
      });
      return res.data?.data ?? { items: [], total: 0 };
    },
    enabled: tab === 1
  });

  const locations: LocationQR[] = Array.isArray(locData?.items) ? locData.items : [];
  const assets: AssetQR[] = Array.isArray(assetData?.items) ? assetData.items : [];
  
  const total = tab === 0 ? (locData?.total ?? 0) : (assetData?.total ?? 0);
  const isLoading = tab === 0 ? locLoading : assetLoading;
  const currentItems = tab === 0 ? locations : assets;

  const handlePreview = (item: any) => {
    setSelectedItem(item);
    setPreviewOpen(true);
  };

  const handleBulkPrint = () => {
    if (currentItems.length === 0) return toast.warning("No items to print");
    
    const win = window.open('', '_blank');
    if (!win) return;
    
    const qrItems = currentItems.map((item: any) => {
      const id = tab === 0 ? item.location_id : item.asset_id;
      const val = tab === 0 ? (item.qr_code || id) : id;
      const name = tab === 0 ? item.location_name : item.asset_type;
      return { id, val, name };
    });

    win.document.write(`
      <html><head><title>Bulk Print QR Codes</title>
      <style>
        body { font-family: Arial; padding: 20px; }
        .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
        .card { border: 1px dashed #ccc; padding: 15px; text-align: center; page-break-inside: avoid; }
        .id { font-weight: bold; margin-top: 10px; font-size: 14px; }
        .name { color: #555; font-size: 11px; margin-top: 4px; }
      </style>
      <script src="https://cdn.jsdelivr.net/npm/qrcode/build/qrcode.min.js"></script>
      </head><body>
      <h2>Bulk Print - ${tab === 0 ? 'Locations' : 'Assets'}</h2>
      <div class="grid" id="grid"></div>
      <script>
        const items = ${JSON.stringify(qrItems)};
        const grid = document.getElementById('grid');
        let rendered = 0;
        
        items.forEach(item => {
          const card = document.createElement('div');
          card.className = 'card';
          const canvasContainer = document.createElement('div');
          card.appendChild(canvasContainer);
          
          const label = document.createElement('div');
          label.innerHTML = '<div class="id">' + item.id + '</div><div class="name">' + item.name + '</div>';
          card.appendChild(label);
          grid.appendChild(card);
          
          QRCode.toCanvas(document.createElement('canvas'), item.val, { width: 150 }, function(err, canvas) {
            if (!err) canvasContainer.appendChild(canvas);
            rendered++;
            if(rendered === items.length) {
              setTimeout(() => { window.print(); }, 1000);
            }
          });
        });
      </script>
      </body></html>
    `);
    win.document.close();
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" fontWeight="bold">QR Codes</Typography>
          <Typography variant="body2" color="text.secondary">
            Manage QR codes for locations and assets. Scan QR to pull up corresponding records.
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<Printer size={18}/>} onClick={handleBulkPrint} disabled={isLoading || currentItems.length === 0}>
          Bulk Print ({currentItems.length})
        </Button>
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tab} onChange={(_, v) => { setTab(v); setPage(0); setSearch(''); }}>
          <Tab label="Location QR Codes" />
          <Tab label="Asset QR Codes" />
        </Tabs>
      </Box>

      <Box mb={3}>
        <TextField
          label="Search..."
          variant="outlined"
          size="small"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(0); }}
          sx={{ width: 320 }}
          InputProps={{ startAdornment: <InputAdornment position="start"><Search size={16} /></InputAdornment> }}
        />
      </Box>

      <Card>
        <TableContainer>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>{tab === 0 ? 'Location ID' : 'Asset ID'}</TableCell>
                <TableCell>{tab === 0 ? 'Location Name' : 'Asset Type'}</TableCell>
                <TableCell>{tab === 0 ? 'Current Asset' : 'Location'}</TableCell>
                <TableCell>QR Value</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow><TableCell colSpan={6} align="center" sx={{ py: 5 }}><CircularProgress /></TableCell></TableRow>
              ) : currentItems.length === 0 ? (
                <TableRow><TableCell colSpan={6} align="center" sx={{ py: 4 }}><Typography color="text.secondary">No records found.</Typography></TableCell></TableRow>
              ) : (
                currentItems.map((item: any) => {
                  const id = tab === 0 ? item.location_id : item.asset_id;
                  const name = tab === 0 ? item.location_name : item.asset_type;
                  const relation = tab === 0 ? item.current_asset_id : item.current_location_id;
                  const val = tab === 0 ? (item.qr_code || id) : id;
                  
                  return (
                    <TableRow key={id} hover>
                      <TableCell sx={{ fontFamily: 'monospace', fontWeight: 600 }}>{id}</TableCell>
                      <TableCell>{name}</TableCell>
                      <TableCell>{relation ? <Chip label={relation} size="small" /> : '-'}</TableCell>
                      <TableCell><Typography variant="body2" sx={{ fontFamily: 'monospace', color: '#0052cc' }}>{val}</Typography></TableCell>
                      <TableCell><Chip label={item.status} size="small" color={item.status === 'Active' ? 'success' : 'default'} /></TableCell>
                      <TableCell align="right">
                        <Tooltip title="Preview & Download">
                          <IconButton size="small" color="primary" onClick={() => handlePreview(item)}>
                            <Eye size={16} />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Print QR">
                          <IconButton size="small" onClick={() => handlePreview(item)}>
                            <Printer size={16} />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div"
          count={total}
          page={page}
          onPageChange={(_, p) => setPage(p)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(_) => { setRowsPerPage(parseInt(_.target.value, 10)); setPage(0); }}
        />
      </Card>

      <QRPreviewDialog
        item={selectedItem}
        type={tab === 0 ? 'location' : 'asset'}
        open={previewOpen}
        onClose={() => { setPreviewOpen(false); setSelectedItem(null); }}
      />
    </Box>
  );
};

export default QRCodes;
