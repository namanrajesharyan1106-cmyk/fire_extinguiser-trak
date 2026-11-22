import React, { useState, useMemo } from 'react';
import {
  Drawer, Box, Typography, IconButton, Button, TextField, InputAdornment,
  Chip, Card, CardActionArea, CircularProgress, LinearProgress,
  useTheme, useMediaQuery, Collapse, Tabs, Tab, MenuItem, Select,
  FormControl, InputLabel, Dialog, DialogTitle, DialogContent, DialogActions,
  DialogContentText
} from '@mui/material';
import {
  X, Search, MapPin, CheckCircle, ArrowRight, ArrowRightCircle,
  Package, ShieldAlert
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import api from '../api/axios';

interface LocationInfo {
  location_id: string;
  location_name: string;
  plant: string;
  area: string;
  department: string;
  building: string;
  floor: string;
  required_asset_type: string;
  required_capacity: string;
  max_assets: number;
  current_assets_count: number;
  remaining_capacity: number;
}

interface AssignedAsset {
  asset_id: string;
  serial_number: string;
  asset_type: string;
  capacity: string;
  status: string;
}

interface CompatibleAsset {
  asset_id: string;
  serial_number: string;
  asset_type: string;
  capacity: string;
  status: string;
  current_location_id: string | null;
  current_location_name?: string | null;
}

interface RejectionReason {
  reason: string;
  expected: string;
  actual: string;
}

interface RejectedAsset {
  asset_id: string;
  serial_number: string;
  asset_type: string;
  capacity: string;
  status: string;
  current_location_id: string | null;
  rejection_reasons: RejectionReason[];
}

interface LocationAssetAssignmentDrawerProps {
  open: boolean;
  onClose: () => void;
  location: any | null;
}

const StatusChip: React.FC<{ status: string }> = ({ status }) => {
  const colorMap: Record<string, 'success' | 'error' | 'default' | 'warning' | 'info'> = {
    Active: 'success',
    Expired: 'error',
    Retired: 'default',
    'Under Maintenance': 'warning',
    Draft: 'info',
  };
  return <Chip label={status || 'Unknown'} color={colorMap[status] ?? 'default'} size="small" sx={{ fontWeight: 600, height: 22 }} />;
};

const CapacityIndicator: React.FC<{ current: number; max: number }> = ({ current, max }) => {
  const percent = max > 0 ? (current / max) * 100 : 100;
  let color: 'success' | 'warning' | 'error' = 'success';
  if (percent >= 100) color = 'error';
  else if (percent >= 70) color = 'warning';

  return (
    <Box sx={{ mt: 1 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
        <Typography variant="caption" color="text.secondary" fontWeight="bold">Capacity Utilization</Typography>
        <Typography variant="caption" color="text.secondary" fontWeight="bold">
          {current} / {max} {percent >= 100 ? '(Full)' : `(${Math.round(percent)}%)`}
        </Typography>
      </Box>
      <LinearProgress 
        variant="determinate" 
        value={percent > 100 ? 100 : percent} 
        color={color} 
        sx={{ height: 6, borderRadius: 3 }}
      />
    </Box>
  );
};

export const LocationAssetAssignmentDrawer: React.FC<LocationAssetAssignmentDrawerProps> = ({
  open,
  onClose,
  location
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<'COMPATIBLE' | 'REJECTED'>('COMPATIBLE');
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterCapacity, setFilterCapacity] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [selectedAsset, setSelectedAsset] = useState<CompatibleAsset | null>(null);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [successView, setSuccessView] = useState(false);

  const locationId = location?.location_id;

  // Query compatible and rejected assets for this location
  const { data: assetsData, isLoading, error: queryError, isError } = useQuery({
    queryKey: ['location-compatible-assets', locationId],
    queryFn: async () => {
      if (!locationId) return { location: null, currently_assigned: [], compatible: [], rejected: [] };
      const res = await api.get(`/locations/${locationId}/compatible-assets`);
      return res.data?.data || { location: null, currently_assigned: [], compatible: [], rejected: [] };
    },
    enabled: open && !!locationId && !successView,
    retry: false
  });

  const locInfo: LocationInfo | null = assetsData?.location || (location ? {
    location_id: location.location_id,
    location_name: location.location_name,
    plant: location.plant,
    area: location.area,
    department: location.department,
    building: location.building,
    floor: location.floor,
    required_asset_type: location.required_asset_type,
    required_capacity: location.required_capacity,
    max_assets: location.max_assets || 1,
    current_assets_count: location.current_assets_count || 0,
    remaining_capacity: Math.max(0, (location.max_assets || 1) - (location.current_assets_count || 0))
  } : null);

  const currentlyAssigned: AssignedAsset[] = assetsData?.currently_assigned || [];
  const compatibleAssets: CompatibleAsset[] = assetsData?.compatible || [];
  const rejectedAssets: RejectedAsset[] = assetsData?.rejected || [];

  // Extract unique filters from both compatible & rejected
  const allAssets = useMemo(() => {
    return [...compatibleAssets, ...rejectedAssets];
  }, [compatibleAssets, rejectedAssets]);

  const uniqueTypes = useMemo(() => {
    const set = new Set<string>();
    allAssets.forEach(a => { if (a.asset_type) set.add(a.asset_type); });
    return Array.from(set);
  }, [allAssets]);

  const uniqueCapacities = useMemo(() => {
    const set = new Set<string>();
    allAssets.forEach(a => { if (a.capacity) set.add(a.capacity); });
    return Array.from(set);
  }, [allAssets]);

  const uniqueStatuses = useMemo(() => {
    const set = new Set<string>();
    allAssets.forEach(a => { if (a.status) set.add(a.status); });
    return Array.from(set);
  }, [allAssets]);

  // Mutation to assign asset to location
  const assignMutation = useMutation({
    mutationFn: async () => {
      if (!locationId || !selectedAsset) throw new Error("Missing assignment data");
      return api.post(`/locations/${locationId}/assign-asset/${selectedAsset.asset_id}`, {
        movement_reason: 'Assigned via Enterprise Location Drawer',
        movement_type: 'Assignment',
        force: true
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['locations'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setConfirmDialogOpen(false);
      setSuccessView(true);
      toast.success(`Asset ${selectedAsset?.asset_id} assigned to ${locInfo?.location_name || locationId}!`);
    },
    onError: (err: any) => {
      setConfirmDialogOpen(false);
      toast.error(err.response?.data?.detail?.message || err.response?.data?.detail || 'Assignment failed');
    }
  });

  // Filter compatible assets
  const filteredCompatible = useMemo(() => {
    return compatibleAssets.filter(asset => {
      if (search) {
        const s = search.toLowerCase();
        const matchId = asset.asset_id.toLowerCase().includes(s);
        const matchSerial = (asset.serial_number || '').toLowerCase().includes(s);
        if (!matchId && !matchSerial) return false;
      }
      if (filterType && asset.asset_type !== filterType) return false;
      if (filterCapacity && asset.capacity !== filterCapacity) return false;
      if (filterStatus && asset.status !== filterStatus) return false;
      return true;
    });
  }, [compatibleAssets, search, filterType, filterCapacity, filterStatus]);

  // Filter rejected assets
  const filteredRejected = useMemo(() => {
    return rejectedAssets.filter(asset => {
      if (search) {
        const s = search.toLowerCase();
        const matchId = asset.asset_id.toLowerCase().includes(s);
        const matchSerial = (asset.serial_number || '').toLowerCase().includes(s);
        if (!matchId && !matchSerial) return false;
      }
      if (filterType && asset.asset_type !== filterType) return false;
      if (filterCapacity && asset.capacity !== filterCapacity) return false;
      if (filterStatus && asset.status !== filterStatus) return false;
      return true;
    });
  }, [rejectedAssets, search, filterType, filterCapacity, filterStatus]);

  const handleClose = () => {
    setTimeout(() => {
      setSearch('');
      setFilterType('');
      setFilterCapacity('');
      setFilterStatus('');
      setSelectedAsset(null);
      setConfirmDialogOpen(false);
      setSuccessView(false);
      setActiveTab('COMPATIBLE');
    }, 200);
    onClose();
  };

  const isLocationFull = (locInfo?.remaining_capacity ?? 1) <= 0;

  if (!location) return null;

  return (
    <>
      <Drawer
        anchor="right"
        open={open}
        onClose={handleClose}
        PaperProps={{
          sx: {
            width: isMobile ? '100%' : 620,
            backgroundColor: '#F4F5F7',
            display: 'flex',
            flexDirection: 'column'
          }
        }}
      >
        {/* Header */}
        <Box p={2.5} display="flex" justifyContent="space-between" alignItems="center" bgcolor="white" borderBottom="1px solid #DFE1E6">
          <Box display="flex" alignItems="center" gap={1.5}>
            <Package size={22} color="#0052cc" />
            <Box>
              <Typography variant="h6" fontWeight="bold" color="#172B4D">
                Assign Asset to Location
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Link a compatible fire extinguisher to this designated safety point
              </Typography>
            </Box>
          </Box>
          <IconButton onClick={handleClose} size="small">
            <X size={20} />
          </IconButton>
        </Box>

        {/* Content */}
        <Box flex={1} overflow="auto" p={3}>
          {/* Section 1: Location Details */}
          {locInfo && (
            <Card sx={{ p: 2.5, mb: 3, borderRadius: 2, boxShadow: '0 2px 4px rgba(0,0,0,0.05)', bgcolor: 'white' }}>
              <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1.5}>
                <Box>
                  <Typography variant="h6" fontWeight="bold">{locInfo.location_name}</Typography>
                  <Typography variant="caption" color="text.secondary" fontFamily="monospace">
                    {locInfo.location_id}
                  </Typography>
                </Box>
                <Chip 
                  label={isLocationFull ? 'Capacity Full' : `${locInfo.remaining_capacity} Slot Available`} 
                  color={isLocationFull ? 'error' : 'success'} 
                  size="small" 
                  sx={{ fontWeight: 'bold' }} 
                />
              </Box>

              <Box display="grid" gridTemplateColumns="1fr 1fr" gap={1.5} mb={2}>
                <Box>
                  <Typography variant="caption" color="text.secondary">Plant & Area</Typography>
                  <Typography variant="body2" fontWeight="500" display="flex" alignItems="center" gap={0.5}>
                    <MapPin size={14} color="#5E6C84" /> {locInfo.plant} / {locInfo.area}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Department</Typography>
                  <Typography variant="body2" fontWeight="500">{locInfo.department || '-'}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Building / Floor</Typography>
                  <Typography variant="body2" fontWeight="500">{locInfo.building}, Floor {locInfo.floor}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Required Asset</Typography>
                  <Typography variant="body2" fontWeight="bold" color="primary.main">
                    {locInfo.required_asset_type} ({locInfo.required_capacity})
                  </Typography>
                </Box>
              </Box>

              <CapacityIndicator current={locInfo.current_assets_count} max={locInfo.max_assets} />
            </Card>
          )}

          {/* Section 2: Currently Assigned Assets (if any) */}
          {currentlyAssigned.length > 0 && (
            <Box mb={3}>
              <Typography variant="subtitle2" fontWeight="bold" color="#5E6C84" mb={1}>
                Currently Assigned Assets ({currentlyAssigned.length})
              </Typography>
              <Box display="flex" flexDirection="column" gap={1.5}>
                {currentlyAssigned.map((item) => (
                  <Card key={item.asset_id} sx={{ p: 1.5, bgcolor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 1.5 }}>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Box>
                        <Typography variant="subtitle2" fontWeight="bold">{item.asset_id}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          SN: {item.serial_number || 'N/A'} • {item.asset_type} • {item.capacity}
                        </Typography>
                      </Box>
                      <StatusChip status={item.status} />
                    </Box>
                  </Card>
                ))}
              </Box>
            </Box>
          )}

          {/* Section 3: Success View */}
          {successView ? (
            <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" py={5}>
              <CheckCircle size={64} color={theme.palette.success.main} />
              <Typography variant="h5" fontWeight="bold" mt={2} mb={1}>Asset Assigned Successfully</Typography>
              <Typography color="text.secondary" mb={4} textAlign="center">
                <b>{selectedAsset?.asset_id}</b> has been linked to <b>{locInfo?.location_name}</b>.
                <br />Location and Asset records have been updated.
              </Typography>
              <Button variant="contained" size="large" onClick={handleClose} sx={{ px: 4 }}>
                Done
              </Button>
            </Box>
          ) : (
            /* Section 4: Available Assets Tabs & List */
            <Box>
              {isLocationFull && (
                <Box mb={2} p={1.5} bgcolor="#FFF4E5" borderRadius={1.5} border="1px solid #FFE0B2" display="flex" alignItems="center" gap={1}>
                  <ShieldAlert size={20} color="#F57C00" />
                  <Typography variant="caption" color="#B26A00" fontWeight={500}>
                    This location has reached its maximum asset capacity ({locInfo?.max_assets}).
                  </Typography>
                </Box>
              )}

              {/* Search & Filter Bar */}
              <Box display="flex" flexDirection="column" gap={1.5} mb={2}>
                <TextField
                  fullWidth
                  size="small"
                  placeholder="Search by Asset ID or Serial Number..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  sx={{ bgcolor: 'white', borderRadius: 1 }}
                  InputProps={{
                    startAdornment: <InputAdornment position="start"><Search size={18} /></InputAdornment>
                  }}
                />

                <Box display="grid" gridTemplateColumns="1fr 1fr 1fr" gap={1}>
                  <FormControl size="small" sx={{ bgcolor: 'white' }}>
                    <InputLabel>Type</InputLabel>
                    <Select value={filterType} label="Type" onChange={e => setFilterType(e.target.value)}>
                      <MenuItem value=""><em>All Types</em></MenuItem>
                      {uniqueTypes.map(t => <MenuItem key={t} value={t}>{t}</MenuItem>)}
                    </Select>
                  </FormControl>

                  <FormControl size="small" sx={{ bgcolor: 'white' }}>
                    <InputLabel>Capacity</InputLabel>
                    <Select value={filterCapacity} label="Capacity" onChange={e => setFilterCapacity(e.target.value)}>
                      <MenuItem value=""><em>All</em></MenuItem>
                      {uniqueCapacities.map(c => <MenuItem key={c} value={c}>{c}</MenuItem>)}
                    </Select>
                  </FormControl>

                  <FormControl size="small" sx={{ bgcolor: 'white' }}>
                    <InputLabel>Status</InputLabel>
                    <Select value={filterStatus} label="Status" onChange={e => setFilterStatus(e.target.value)}>
                      <MenuItem value=""><em>All</em></MenuItem>
                      {uniqueStatuses.map(s => <MenuItem key={s} value={s}>{s}</MenuItem>)}
                    </Select>
                  </FormControl>
                </Box>
              </Box>

              {/* Tabs */}
              <Tabs
                value={activeTab}
                onChange={(_, val) => setActiveTab(val)}
                textColor="primary"
                indicatorColor="primary"
                sx={{ mb: 2, borderBottom: '1px solid #DFE1E6', minHeight: 38, '& .MuiTab-root': { minHeight: 38, py: 0.5, fontWeight: 600 } }}
              >
                <Tab label={`Compatible Assets (${filteredCompatible.length})`} value="COMPATIBLE" />
                <Tab label={`Incompatible Assets (${filteredRejected.length})`} value="REJECTED" />
              </Tabs>

              {/* Loading & Error States */}
              {isError ? (
                <Box textAlign="center" py={4}>
                  <Typography color="error" fontWeight="bold">
                    {(queryError as any)?.response?.data?.detail || 'Failed to load assets.'}
                  </Typography>
                </Box>
              ) : isLoading ? (
                <Box display="flex" justifyContent="center" py={5}><CircularProgress /></Box>
              ) : activeTab === 'COMPATIBLE' ? (
                /* Compatible Assets List */
                filteredCompatible.length === 0 ? (
                  <Box textAlign="center" py={5} px={2} bgcolor="white" borderRadius={2} border="1px dashed #CBD5E1">
                    <Package size={36} color="#94A3B8" style={{ margin: '0 auto 8px' }} />
                    <Typography fontWeight="bold" color="text.secondary">No Compatible Assets Found</Typography>
                    <Typography variant="caption" color="text.secondary">
                      No unassigned active assets match this location's required type ({locInfo?.required_asset_type}) and capacity ({locInfo?.required_capacity}).
                    </Typography>
                  </Box>
                ) : (
                  <Box display="flex" flexDirection="column" gap={1.5}>
                    {filteredCompatible.map((asset) => {
                      const isSelected = selectedAsset?.asset_id === asset.asset_id;
                      return (
                        <Card
                          key={asset.asset_id}
                          sx={{
                            borderRadius: 2,
                            border: isSelected ? `2px solid ${theme.palette.primary.main}` : '2px solid transparent',
                            boxShadow: isSelected ? `0 4px 12px ${theme.palette.primary.light}40` : '0 1px 3px rgba(0,0,0,0.06)',
                            bgcolor: isSelected ? '#F0F7FF' : 'white',
                            transition: 'all 0.2s'
                          }}
                        >
                          <CardActionArea
                            onClick={() => setSelectedAsset(asset)}
                            sx={{ p: 2 }}
                          >
                            <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
                              <Box>
                                <Typography fontWeight="bold" color="#172B4D">{asset.asset_id}</Typography>
                                <Typography variant="caption" color="text.secondary">
                                  SN: {asset.serial_number || 'N/A'}
                                </Typography>
                              </Box>
                              <Box display="flex" gap={1} alignItems="center">
                                <Chip label="Compatible" color="success" size="small" variant="outlined" sx={{ fontWeight: 600, height: 22 }} />
                                <StatusChip status={asset.status} />
                              </Box>
                            </Box>

                            <Box display="grid" gridTemplateColumns="1fr 1fr" gap={1} mt={1}>
                              <Box>
                                <Typography variant="caption" color="text.secondary">Asset Type</Typography>
                                <Typography variant="body2" fontWeight="500">{asset.asset_type}</Typography>
                              </Box>
                              <Box>
                                <Typography variant="caption" color="text.secondary">Capacity</Typography>
                                <Typography variant="body2" fontWeight="500">{asset.capacity}</Typography>
                              </Box>
                            </Box>

                            <Box mt={1} pt={1} borderTop="1px dashed #E2E8F0" display="flex" justifyContent="space-between" alignItems="center">
                              <Typography variant="caption" color="text.secondary">
                                Current Location: <b>{asset.current_location_id || 'Unassigned'}</b>
                              </Typography>
                              {isSelected && (
                                <Typography variant="caption" color="primary.main" fontWeight="bold">
                                  ✓ Selected for Assignment
                                </Typography>
                              )}
                            </Box>
                          </CardActionArea>
                        </Card>
                      );
                    })}
                  </Box>
                )
              ) : (
                /* Incompatible Assets List with Explicit Rejection Reasons */
                filteredRejected.length === 0 ? (
                  <Box textAlign="center" py={5} px={2} bgcolor="white" borderRadius={2} border="1px dashed #CBD5E1">
                    <Typography color="text.secondary">No incompatible assets matching filters.</Typography>
                  </Box>
                ) : (
                  <Box display="flex" flexDirection="column" gap={1.5}>
                    {filteredRejected.map((asset) => (
                      <Card 
                        key={asset.asset_id}
                        sx={{ 
                          borderRadius: 2, 
                          bgcolor: '#FAFBFC', 
                          border: '1px solid #DFE1E6',
                          boxShadow: 'none'
                        }}
                      >
                        <Box p={2}>
                          <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
                            <Box>
                              <Typography fontWeight="bold" color="text.secondary">{asset.asset_id}</Typography>
                              <Typography variant="caption" color="text.secondary">
                                SN: {asset.serial_number || 'N/A'} • {asset.asset_type} ({asset.capacity})
                              </Typography>
                            </Box>
                            <Box display="flex" gap={1} alignItems="center">
                              <Chip label="Incompatible" size="small" variant="outlined" color="default" sx={{ height: 22 }} />
                              <StatusChip status={asset.status} />
                            </Box>
                          </Box>

                          <Box display="flex" flexDirection="column" gap={0.75} mt={1.5}>
                            {asset.rejection_reasons?.map((reason, idx) => (
                              <Box key={idx} p={1} bgcolor="#FFF" borderRadius={1} border="1px solid #EBECF0">
                                <Typography variant="caption" fontWeight="bold" color="error.main" display="block">
                                  {reason.reason}
                                </Typography>
                                <Box display="flex" justifyContent="space-between" mt={0.5}>
                                  <Typography variant="caption" color="text.secondary">Required: {reason.expected}</Typography>
                                  <Typography variant="caption" color="text.secondary">Actual: {reason.actual}</Typography>
                                </Box>
                              </Box>
                            ))}
                          </Box>
                        </Box>
                      </Card>
                    ))}
                  </Box>
                )
              )}
            </Box>
          )}
        </Box>

        {/* Footer / Assignment Action */}
        {!successView && (
          <Box p={2.5} bgcolor="white" borderTop="1px solid #DFE1E6" boxShadow="0 -4px 16px rgba(0,0,0,0.05)">
            <Collapse in={!!selectedAsset}>
              {selectedAsset && (
                <Box mb={2} p={1.5} bgcolor="#F4F5F7" borderRadius={1.5} border="1px dashed #B3BAC5">
                  <Typography variant="caption" fontWeight="bold" color="text.secondary" mb={0.5} display="block">
                    Assignment Preview
                  </Typography>
                  <Box display="flex" alignItems="center" justifyContent="space-between">
                    <Box textAlign="center">
                      <Typography variant="body2" fontWeight="bold">{selectedAsset.asset_id}</Typography>
                      <Typography variant="caption" color="text.secondary">{selectedAsset.asset_type}</Typography>
                    </Box>
                    <ArrowRight size={16} color="#8993A4" />
                    <Box textAlign="center">
                      <Typography variant="body2" fontWeight="bold">{locInfo?.location_name}</Typography>
                      <Typography variant="caption" color="text.secondary">{locInfo?.location_id}</Typography>
                    </Box>
                    <ArrowRight size={16} color="#8993A4" />
                    <Box textAlign="center">
                      <Typography variant="body2" fontWeight="bold" color="primary.main">
                        {(locInfo?.current_assets_count || 0) + 1}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">New Count</Typography>
                    </Box>
                  </Box>
                </Box>
              )}
            </Collapse>

            <Box display="flex" gap={1.5} justifyContent="flex-end">
              <Button onClick={handleClose} variant="outlined" color="inherit">
                Cancel
              </Button>
              <Button
                variant="contained"
                color="primary"
                disabled={!selectedAsset || assignMutation.isPending}
                onClick={() => setConfirmDialogOpen(true)}
                startIcon={<ArrowRightCircle size={18} />}
              >
                Assign Asset
              </Button>
            </Box>
          </Box>
        )}
      </Drawer>

      {/* Confirmation Dialog */}
      <Dialog open={confirmDialogOpen} onClose={() => setConfirmDialogOpen(false)}>
        <DialogTitle>Confirm Asset Assignment</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to assign asset <b>{selectedAsset?.asset_id}</b> ({selectedAsset?.asset_type}, {selectedAsset?.capacity}) to location <b>{locInfo?.location_name}</b> ({locInfo?.location_id})?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialogOpen(false)} disabled={assignMutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="primary"
            onClick={() => assignMutation.mutate()}
            disabled={assignMutation.isPending}
            startIcon={assignMutation.isPending ? <CircularProgress size={16} color="inherit" /> : null}
          >
            {assignMutation.isPending ? 'Assigning...' : 'Confirm Assignment'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default LocationAssetAssignmentDrawer;
