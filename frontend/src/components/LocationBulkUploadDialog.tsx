import React, { useState, useRef } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Box, Typography, Button, IconButton, Card,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Chip, CircularProgress, Alert, Tabs, Tab
} from '@mui/material';
import { 
  X, Upload, Download, FileSpreadsheet, CheckCircle2, 
  AlertTriangle, AlertCircle, RefreshCw 
} from 'lucide-react';
import api from '../api/axios';
import { toast } from 'react-toastify';

interface PreviewRow {
  row_number: number;
  location_name: string;
  plant: string;
  area: string;
  department: string;
  building: string;
  floor: string;
  required_asset_type: string;
  required_capacity: string;
  qr_code?: string;
  status: 'VALID' | 'INVALID' | 'DUPLICATE';
  errors: string[];
}

interface PreviewSummary {
  total: number;
  valid: number;
  invalid: number;
  duplicates: number;
}

interface BulkUploadResult {
  summary: {
    total: number;
    imported: number;
    failed: number;
    duplicates: number;
    skipped: number;
  };
  error_report?: string | null;
}

interface LocationBulkUploadDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const LocationBulkUploadDialog: React.FC<LocationBulkUploadDialogProps> = ({
  open,
  onClose,
  onSuccess,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [previewRows, setPreviewRows] = useState<PreviewRow[]>([]);
  const [previewSummary, setPreviewSummary] = useState<PreviewSummary | null>(null);
  const [filterTab, setFilterTab] = useState<'ALL' | 'VALID' | 'ISSUES'>('ALL');
  const [uploadResult, setUploadResult] = useState<BulkUploadResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const resetState = () => {
    setSelectedFile(null);
    setIsDragging(false);
    setIsPreviewing(false);
    setIsSubmitting(false);
    setPreviewRows([]);
    setPreviewSummary(null);
    setFilterTab('ALL');
    setUploadResult(null);
    setErrorMessage(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleClose = () => {
    resetState();
    onClose();
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
    } catch {
      toast.error('Failed to download sample file');
    }
  };

  const processFile = async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'xlsx' && ext !== 'xls') {
      setErrorMessage('Please upload a valid Excel file (.xlsx or .xls)');
      return;
    }

    setSelectedFile(file);
    setErrorMessage(null);
    setIsPreviewing(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post('/locations/bulk-upload/preview', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      const data = res.data?.data;
      setPreviewRows(data?.preview || []);
      setPreviewSummary(data?.summary || null);
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.response?.data?.message || 'Failed to parse Excel file.';
      setErrorMessage(detail);
      setPreviewRows([]);
      setPreviewSummary(null);
    } finally {
      setIsPreviewing(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  const handleConfirmImport = async () => {
    if (!selectedFile) return;

    setIsSubmitting(true);
    setErrorMessage(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await api.post('/locations/bulk-upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      const data = res.data?.data;
      setUploadResult(data);
      onSuccess();
      toast.success(`Import completed: ${data?.summary?.imported || 0} locations imported.`);
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.response?.data?.message || 'Failed to import locations.';
      setErrorMessage(detail);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDownloadErrorReport = () => {
    if (!uploadResult?.error_report) return;
    const link = document.createElement('a');
    link.href = `data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,${uploadResult.error_report}`;
    link.download = 'Failed_Locations_Report.xlsx';
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
  };

  const filteredRows = previewRows.filter(row => {
    if (filterTab === 'VALID') return row.status === 'VALID';
    if (filterTab === 'ISSUES') return row.status === 'INVALID' || row.status === 'DUPLICATE';
    return true;
  });

  return (
    <Dialog 
      open={open} 
      onClose={handleClose} 
      maxWidth="lg" 
      fullWidth
      PaperProps={{ sx: { borderRadius: 2, minHeight: '520px' } }}
    >
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pb: 1, borderBottom: '1px solid #E2E8F0' }}>
        <Box display="flex" alignItems="center" gap={1.5}>
          <FileSpreadsheet size={24} color="#0052cc" />
          <Typography variant="h6" fontWeight="bold">Bulk Upload Locations</Typography>
        </Box>
        <IconButton size="small" onClick={handleClose} disabled={isSubmitting}>
          <X size={20} />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 2.5 }}>
        {/* Step 1: Upload Result View (Complete) */}
        {uploadResult ? (
          <Box display="flex" flexDirection="column" gap={3} py={2}>
            <Box textAlign="center" py={2}>
              <CheckCircle2 size={54} color="#388e3c" style={{ margin: '0 auto 12px' }} />
              <Typography variant="h5" fontWeight="bold">Location Import Completed</Typography>
              <Typography variant="body2" color="text.secondary">
                Review the outcome of your location bulk upload below.
              </Typography>
            </Box>

            <Box display="grid" gridTemplateColumns="repeat(4, 1fr)" gap={2}>
              <Card sx={{ p: 2, textAlign: 'center', bgcolor: '#F8FAFC', border: '1px solid #E2E8F0' }}>
                <Typography variant="h4" fontWeight="bold" color="primary.main">
                  {uploadResult.summary.total}
                </Typography>
                <Typography variant="body2" color="text.secondary" fontWeight={500}>Total Rows</Typography>
              </Card>
              <Card sx={{ p: 2, textAlign: 'center', bgcolor: '#F0FDF4', border: '1px solid #BBF7D0' }}>
                <Typography variant="h4" fontWeight="bold" color="success.main">
                  {uploadResult.summary.imported}
                </Typography>
                <Typography variant="body2" color="text.secondary" fontWeight={500}>Successful</Typography>
              </Card>
              <Card sx={{ p: 2, textAlign: 'center', bgcolor: '#FEF2F2', border: '1px solid #FECACA' }}>
                <Typography variant="h4" fontWeight="bold" color="error.main">
                  {uploadResult.summary.failed}
                </Typography>
                <Typography variant="body2" color="text.secondary" fontWeight={500}>Failed Rows</Typography>
              </Card>
              <Card sx={{ p: 2, textAlign: 'center', bgcolor: '#FFFBEB', border: '1px solid #FDE68A' }}>
                <Typography variant="h4" fontWeight="bold" color="warning.main">
                  {uploadResult.summary.duplicates}
                </Typography>
                <Typography variant="body2" color="text.secondary" fontWeight={500}>Duplicates</Typography>
              </Card>
            </Box>

            {uploadResult.error_report && (
              <Alert 
                severity="warning" 
                icon={<AlertTriangle size={20} />}
                action={
                  <Button 
                    color="inherit" 
                    size="small" 
                    variant="outlined" 
                    onClick={handleDownloadErrorReport}
                    startIcon={<Download size={16} />}
                  >
                    Download Report
                  </Button>
                }
              >
                Some rows failed to import or were duplicates. Download the error report to review row-by-row reasons.
              </Alert>
            )}
          </Box>
        ) : !previewSummary ? (
          /* Step 2: Dropzone & File Selection View */
          <Box display="flex" flexDirection="column" gap={3}>
            {errorMessage && (
              <Alert severity="error" icon={<AlertCircle size={20} />}>
                {errorMessage}
              </Alert>
            )}

            <Box 
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              sx={{
                border: '2px dashed',
                borderColor: isDragging ? 'primary.main' : '#CBD5E1',
                borderRadius: 2,
                p: 5,
                textAlign: 'center',
                backgroundColor: isDragging ? '#F0F7FF' : '#F8FAFC',
                cursor: 'pointer',
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  borderColor: 'primary.main',
                  backgroundColor: '#F8FAFF'
                }
              }}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx, .xls"
                style={{ display: 'none' }}
                onChange={handleFileChange}
              />
              <Upload size={48} color="#0052cc" style={{ margin: '0 auto 12px', opacity: 0.8 }} />
              <Typography variant="h6" fontWeight="bold" gutterBottom>
                {isPreviewing ? 'Analyzing Excel File...' : 'Choose an Excel file or drag & drop it here'}
              </Typography>
              <Typography variant="body2" color="text.secondary" mb={2}>
                Supports standard template files (.xlsx, .xls)
              </Typography>
              {isPreviewing ? (
                <CircularProgress size={28} />
              ) : (
                <Button variant="contained" size="medium" sx={{ mt: 1 }}>
                  Browse Files
                </Button>
              )}
            </Box>

            <Box display="flex" justifyContent="space-between" alignItems="center" p={2} bgcolor="#F1F5F9" borderRadius={1.5}>
              <Box>
                <Typography variant="subtitle2" fontWeight="bold">Need the official format?</Typography>
                <Typography variant="caption" color="text.secondary">
                  Download the sample template containing active plants, areas, departments, and asset types.
                </Typography>
              </Box>
              <Button 
                variant="outlined" 
                size="small" 
                startIcon={<Download size={16} />} 
                onClick={handleDownloadSample}
              >
                Download Sample Template
              </Button>
            </Box>
          </Box>
        ) : (
          /* Step 3: Data Preview & Pre-Submission Validation View */
          <Box display="flex" flexDirection="column" gap={2}>
            {errorMessage && (
              <Alert severity="error" icon={<AlertCircle size={20} />}>
                {errorMessage}
              </Alert>
            )}

            {/* Summary Cards */}
            <Box display="grid" gridTemplateColumns="repeat(4, 1fr)" gap={2}>
              <Card sx={{ p: 1.5, textAlign: 'center', bgcolor: '#F8FAFC', border: '1px solid #E2E8F0' }}>
                <Typography variant="h5" fontWeight="bold" color="primary.main">{previewSummary.total}</Typography>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>Total Rows</Typography>
              </Card>
              <Card sx={{ p: 1.5, textAlign: 'center', bgcolor: '#F0FDF4', border: '1px solid #BBF7D0' }}>
                <Typography variant="h5" fontWeight="bold" color="success.main">{previewSummary.valid}</Typography>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>Valid (Ready)</Typography>
              </Card>
              <Card sx={{ p: 1.5, textAlign: 'center', bgcolor: '#FEF2F2', border: '1px solid #FECACA' }}>
                <Typography variant="h5" fontWeight="bold" color="error.main">{previewSummary.invalid}</Typography>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>Invalid</Typography>
              </Card>
              <Card sx={{ p: 1.5, textAlign: 'center', bgcolor: '#FFFBEB', border: '1px solid #FDE68A' }}>
                <Typography variant="h5" fontWeight="bold" color="warning.main">{previewSummary.duplicates}</Typography>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>Duplicates</Typography>
              </Card>
            </Box>

            {/* Row Status Filter Tabs */}
            <Box display="flex" justifyContent="space-between" alignItems="center" borderBottom="1px solid #E2E8F0" pb={0.5}>
              <Tabs 
                value={filterTab} 
                onChange={(_, val) => setFilterTab(val)}
                textColor="primary"
                indicatorColor="primary"
                sx={{ minHeight: 36, '& .MuiTab-root': { minHeight: 36, py: 0.5, fontWeight: 600, fontSize: '0.85rem' } }}
              >
                <Tab label={`All (${previewSummary.total})`} value="ALL" />
                <Tab label={`Valid (${previewSummary.valid})`} value="VALID" />
                <Tab label={`Issues (${previewSummary.invalid + previewSummary.duplicates})`} value="ISSUES" />
              </Tabs>
              
              <Box display="flex" alignItems="center" gap={1}>
                <Typography variant="caption" color="text.secondary" sx={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {selectedFile?.name}
                </Typography>
                <Button 
                  size="small" 
                  color="inherit" 
                  startIcon={<RefreshCw size={14} />} 
                  onClick={() => {
                    setPreviewSummary(null);
                    setPreviewRows([]);
                    setSelectedFile(null);
                  }}
                >
                  Change File
                </Button>
              </Box>
            </Box>

            {/* Preview Table */}
            <TableContainer sx={{ maxHeight: 320, border: '1px solid #E2E8F0', borderRadius: 1 }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 'bold', width: 60 }}>#</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', width: 110 }}>Status</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>Location Name</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>Plant / Area</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>Dept / Bldg / Floor</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>Required Asset</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>Validation Details</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredRows.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                        No records match the selected filter.
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredRows.map((row) => {
                      const isRowValid = row.status === 'VALID';
                      const isRowDup = row.status === 'DUPLICATE';
                      return (
                        <TableRow 
                          key={row.row_number}
                          sx={{ 
                            bgcolor: isRowValid ? '#FAFDF9' : isRowDup ? '#FFFDF5' : '#FFF8F8',
                            '&:hover': { bgcolor: isRowValid ? '#F0FDF4' : isRowDup ? '#FEF9C3' : '#FEE2E2' }
                          }}
                        >
                          <TableCell>{row.row_number}</TableCell>
                          <TableCell>
                            {isRowValid ? (
                              <Chip label="Valid" color="success" size="small" sx={{ fontWeight: 600, height: 22 }} />
                            ) : isRowDup ? (
                              <Chip label="Duplicate" color="warning" size="small" sx={{ fontWeight: 600, height: 22 }} />
                            ) : (
                              <Chip label="Invalid" color="error" size="small" sx={{ fontWeight: 600, height: 22 }} />
                            )}
                          </TableCell>
                          <TableCell sx={{ fontWeight: 500 }}>{row.location_name || '-'}</TableCell>
                          <TableCell>
                            <Typography variant="body2">{row.plant || '-'}</Typography>
                            <Typography variant="caption" color="text.secondary">{row.area || '-'}</Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="caption" color="text.secondary" display="block">
                              {row.department || '-'}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {row.building || '-'}, Fl {row.floor || '-'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">{row.required_asset_type || '-'}</Typography>
                            <Typography variant="caption" color="text.secondary">{row.required_capacity || '-'}</Typography>
                          </TableCell>
                          <TableCell>
                            {row.errors.length > 0 ? (
                              <Box display="flex" flexDirection="column" gap={0.5}>
                                {row.errors.map((err, i) => (
                                  <Typography key={i} variant="caption" color="error.main" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                    • {err}
                                  </Typography>
                                ))}
                              </Box>
                            ) : (
                              <Typography variant="caption" color="success.main" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                <CheckCircle2 size={14} /> Ready to import
                              </Typography>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </TableContainer>

            {previewSummary.invalid + previewSummary.duplicates > 0 && (
              <Alert severity="info" sx={{ py: 0.5 }}>
                Rows with validation errors or duplicates will be safely skipped. Only valid rows will be imported into the database.
              </Alert>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2, borderTop: '1px solid #E2E8F0', justifyContent: 'space-between' }}>
        {uploadResult ? (
          <Box width="100%" display="flex" justifyContent="flex-end">
            <Button variant="contained" onClick={handleClose}>
              Done
            </Button>
          </Box>
        ) : !previewSummary ? (
          <>
            <Button onClick={handleClose} color="inherit">
              Cancel
            </Button>
            <Button 
              variant="outlined" 
              startIcon={<Download size={16} />} 
              onClick={handleDownloadSample}
            >
              Download Sample
            </Button>
          </>
        ) : (
          <>
            <Button 
              onClick={() => {
                setPreviewSummary(null);
                setPreviewRows([]);
                setSelectedFile(null);
              }} 
              color="inherit"
              disabled={isSubmitting}
            >
              Back
            </Button>
            <Box display="flex" gap={1.5}>
              <Button onClick={handleClose} color="inherit" disabled={isSubmitting}>
                Cancel
              </Button>
              <Button
                variant="contained"
                color="primary"
                disabled={previewSummary.valid === 0 || isSubmitting}
                onClick={handleConfirmImport}
                startIcon={isSubmitting ? <CircularProgress size={16} color="inherit" /> : <Upload size={16} />}
              >
                {isSubmitting 
                  ? 'Importing...' 
                  : `Import Valid Locations (${previewSummary.valid})`}
              </Button>
            </Box>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default LocationBulkUploadDialog;
