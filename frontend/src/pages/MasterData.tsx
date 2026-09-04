import React, { useState } from 'react';
import { 
  Box, Typography, Card, Tabs, Tab, Table, TableBody, TableCell, TableContainer, 
  TableHead, TableRow, Button, IconButton, Dialog, DialogTitle, DialogContent, 
  DialogActions, TextField, CircularProgress, Chip, Alert, AlertTitle
} from '@mui/material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Edit2, Power, Download, Upload, AlertCircle } from 'lucide-react';
import { useForm } from 'react-hook-form';
import api from '../api/axios';
import { toast } from 'react-toastify';

const MASTER_TYPES = [
  { id: 'plants', label: 'Plants' },
  { id: 'departments', label: 'Departments' },
  { id: 'areas', label: 'Areas' },
  { id: 'buildings', label: 'Buildings' },
  { id: 'floors', label: 'Floors' },
  { id: 'asset_types', label: 'Asset Types' },
  { id: 'capacity_types', label: 'Capacity Types' },
  { id: 'risk_categories', label: 'Risk Categories' },
  { id: 'inspection_frequencies', label: 'Inspection Freq' },
];

const MasterData: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const activeMasterType = MASTER_TYPES[activeTab].id;
  const queryClient = useQueryClient();

  const [open, setOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<any>(null);

  const [bulkUploadOpen, setBulkUploadOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<{
    added?: number;
    skipped?: number;
    errors?: number;
    message?: string;
    error_report?: string;
  } | null>(null);
  const [uploading, setUploading] = useState(false);

  const { register, handleSubmit, reset, setValue, formState: { errors } } = useForm();

  const { data: records, isLoading } = useQuery({
    queryKey: ['masters', activeMasterType],
    queryFn: async () => {
      const res = await api.get(`/masters/admin/${activeMasterType}`);
      return res.data.data;
    }
  });

  const saveMutation = useMutation({
    mutationFn: async (data: { name: string }) => {
      if (editingItem) {
        return api.put(`/masters/admin/${activeMasterType}/${editingItem.id}`, data);
      }
      return api.post(`/masters/admin/${activeMasterType}`, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['masters', activeMasterType] });
      toast.success('Record saved successfully');
      handleClose();
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to save record');
    }
  });

  const toggleMutation = useMutation({
    mutationFn: async (id: number) => {
      return api.put(`/masters/admin/${activeMasterType}/${id}/toggle-status`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['masters', activeMasterType] });
      toast.success('Status updated');
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to update status');
    }
  });

  const handleOpen = (item?: any) => {
    if (item) {
      setEditingItem(item);
      setValue('name', item.name);
    } else {
      setEditingItem(null);
      reset();
    }
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    reset();
    setEditingItem(null);
  };

  const handleDownloadSample = async () => {
    try {
      const response = await api.get(`/masters/admin/${activeMasterType}/bulk-upload/sample`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${activeMasterType}_sample.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      toast.error('Failed to download sample excel');
    }
  };

  const handleBulkUploadClose = () => {
    setBulkUploadOpen(false);
    setSelectedFile(null);
    setUploadResult(null);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setUploadResult(null);
    }
  };

  const handleUploadSubmit = async () => {
    if (!selectedFile) {
      toast.error("Please select a file to upload");
      return;
    }

    if (!selectedFile.name.endsWith('.xlsx')) {
      toast.error("Invalid file type. Please upload an .xlsx file");
      return;
    }

    setUploading(true);
    setUploadResult(null);
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await api.post(`/masters/admin/${activeMasterType}/bulk-upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const result = res.data;
      if (result.success) {
        toast.success(result.message || 'Bulk upload completed successfully');
        queryClient.invalidateQueries({ queryKey: ['masters', activeMasterType] });
        handleBulkUploadClose();
      } else {
        setUploadResult(result);
      }
    } catch (err: any) {
      const result = err.response?.data;
      if (result && result.error_report) {
        setUploadResult(result);
      } else {
        toast.error(result?.detail || result?.message || 'Failed to upload file');
      }
    } finally {
      setUploading(false);
    }
  };

  const downloadErrorReport = () => {
    if (uploadResult?.error_report) {
      const linkSource = `data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,${uploadResult.error_report}`;
      const downloadLink = document.createElement("a");
      downloadLink.href = linkSource;
      downloadLink.download = `${activeMasterType}_error_report.xlsx`;
      downloadLink.click();
    }
  };

  const onSubmit = (data: any) => {
    saveMutation.mutate(data);
  };

  return (
    <Box>
      <Typography variant="h4" fontWeight="bold" mb={3}>Master Data Management</Typography>
      
      <Card sx={{ mb: 3 }}>
        <Tabs 
          value={activeTab} 
          onChange={(_, newVal) => setActiveTab(newVal)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          {MASTER_TYPES.map((type, idx) => (
            <Tab key={type.id} label={type.label} value={idx} />
          ))}
        </Tabs>
      </Card>

      <Card>
        <Box display="flex" justifyContent="space-between" alignItems="center" p={2} borderBottom="1px solid #f0f0f0">
          <Typography variant="h6" fontWeight="bold">{MASTER_TYPES[activeTab].label}</Typography>
          <Box display="flex" gap={2}>
            <Button variant="outlined" startIcon={<Download size={18} />} onClick={handleDownloadSample}>
              Download Sample Excel
            </Button>
            <Button variant="outlined" startIcon={<Upload size={18} />} onClick={() => setBulkUploadOpen(true)}>
              Bulk Upload
            </Button>
            <Button variant="contained" startIcon={<Plus size={18} />} onClick={() => handleOpen()}>
              Add Record
            </Button>
          </Box>
        </Box>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={4} align="center" sx={{ py: 3 }}><CircularProgress size={24} /></TableCell>
                </TableRow>
              ) : records?.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} align="center" sx={{ py: 3 }}>No records found.</TableCell>
                </TableRow>
              ) : (
                records?.map((record: any) => {
                  const isActive = record.is_active === true || record.status === "Active";
                  return (
                    <TableRow key={record.id}>
                      <TableCell>{record.id}</TableCell>
                      <TableCell sx={{ fontWeight: 'medium' }}>{record.name}</TableCell>
                      <TableCell>
                        <Chip 
                          label={isActive ? 'Active' : 'Inactive'} 
                          color={isActive ? 'success' : 'default'} 
                          size="small" 
                        />
                      </TableCell>
                      <TableCell align="right">
                        <IconButton color="primary" onClick={() => handleOpen(record)} title="Edit">
                          <Edit2 size={18} />
                        </IconButton>
                        <IconButton color={isActive ? 'error' : 'success'} onClick={() => toggleMutation.mutate(record.id)} title={isActive ? "Deactivate" : "Activate"}>
                          <Power size={18} />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogTitle>{editingItem ? 'Edit' : 'Add'} {MASTER_TYPES[activeTab].label}</DialogTitle>
          <DialogContent dividers>
            <TextField
              fullWidth
              label="Name"
              {...register('name', { required: 'Name is required' })}
              error={!!errors.name}
              helperText={errors.name?.message as string}
              margin="dense"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={handleClose}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving...' : 'Save'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      <Dialog open={bulkUploadOpen} onClose={handleBulkUploadClose} maxWidth="sm" fullWidth>
        <DialogTitle>Bulk Upload {MASTER_TYPES[activeTab].label}</DialogTitle>
        <DialogContent dividers>
          <Box display="flex" flexDirection="column" gap={3}>
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Select Excel File (.xlsx)
              </Typography>
              <TextField
                type="file"
                inputProps={{ accept: ".xlsx" }}
                onChange={handleFileChange}
                fullWidth
                size="small"
              />
            </Box>

            {uploadResult && (
              <Alert severity="error" icon={<AlertCircle />}>
                <AlertTitle>Validation Failed</AlertTitle>
                <Typography variant="body2" paragraph>
                  {uploadResult.message || `Found ${uploadResult.errors} errors in the uploaded file.`}
                </Typography>
                {uploadResult.error_report && (
                  <Button 
                    variant="outlined" 
                    color="error" 
                    size="small"
                    onClick={downloadErrorReport}
                  >
                    Download Error Report
                  </Button>
                )}
              </Alert>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleBulkUploadClose} disabled={uploading}>Cancel</Button>
          <Button 
            variant="contained" 
            onClick={handleUploadSubmit} 
            disabled={!selectedFile || uploading}
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default MasterData;
