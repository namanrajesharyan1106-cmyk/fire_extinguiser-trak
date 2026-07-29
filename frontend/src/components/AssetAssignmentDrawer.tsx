import React, { useState, useMemo } from 'react';
import {
  Drawer, Box, Typography, IconButton, Button, TextField, InputAdornment,
  Chip, Card, CardActionArea, Divider, CircularProgress, LinearProgress,
  useTheme, useMediaQuery, Collapse, Dialog, DialogTitle, DialogContent, DialogActions
} from '@mui/material';
import {
  X, Search, Filter, MapPin, Hash, CheckCircle, AlertTriangle, ArrowRight, ArrowRightCircle
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import api from '../api/axios';

// ─── Types ───────────────────────────────────────────────────────────────────
interface Asset {
  asset_id: string;
  serial_number: string;
  asset_type: string;
  capacity: string | null;
  status: string;
  current_location_id: string | null;
}

interface LocationRec {
  location_id: string;
  location_name: string;
  plant: string | null;
  area: string | null;
  building: string | null;
  floor: string | null;
  required_asset_type: string | null;
  required_capacity: string | null;
  max_assets: number;
  current_assets_count: number;
  remaining_capacity: number;
}

interface RejectionReason {
  reason: string;
  expected: string;
  actual: string;
}

interface RejectedLocationRec extends LocationRec {
  rejection_reasons: RejectionReason[];
}

interface AssetAssignmentDrawerProps {
  open: boolean;
  onClose: () => void;
  asset: Asset | null;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
const StatusChip = ({ status }: { status: string }) => {
  const colorMap: any = {
    Active: 'success', Expired: 'error', Retired: 'default', 'Under Maintenance': 'warning',
  };
  return <Chip label={status} color={colorMap[status] ?? 'default'} size="small" />;
};

const CapacityIndicator = ({ current, max }: { current: number; max: number }) => {
  const percent = max > 0 ? (current / max) * 100 : 100;
  let color: 'success' | 'warning' | 'error' = 'success';
  if (percent >= 90) color = 'error';
  else if (percent >= 70) color = 'warning';

  return (
    <Box sx={{ mt: 1 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
        <Typography variant="caption" color="text.secondary" fontWeight="bold">Capacity</Typography>
        <Typography variant="caption" color="text.secondary" fontWeight="bold">
          {current} / {max} ({Math.round(percent)}%)
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

// ─── Component ───────────────────────────────────────────────────────────────
const AssetAssignmentDrawer: React.FC<AssetAssignmentDrawerProps> = ({ open, onClose, asset }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [selectedLocation, setSelectedLocation] = useState<LocationRec | null>(null);
  const [reassignConfirmed, setReassignConfirmed] = useState(false);
  const [successView, setSuccessView] = useState(false);

  // Determine if we need reassign confirmation
  const needsReassignConfirm = asset?.current_location_id && !reassignConfirmed && !successView;

  // ─── Queries ───────────────────────────────────────────────────────────────
  const { data: locationsData, isLoading, error: queryError, isError } = useQuery({
    queryKey: ['compatible-locations', asset?.asset_id],
    queryFn: async () => {
      if (!asset) return { compatible: [], rejected: [] };
      const res = await api.get(`/assets/${asset.asset_id}/compatible-locations`);
      return {
        compatible: res.data?.data?.compatible || [],
        rejected: res.data?.data?.rejected || []
      };
    },
    enabled: open && !!asset && !needsReassignConfirm && !successView,
    retry: false
  });

  const locations: LocationRec[] = locationsData?.compatible || [];
  const rejectedLocations: RejectedLocationRec[] = locationsData?.rejected || [];

  // ─── Mutations ─────────────────────────────────────────────────────────────
  const assignMutation = useMutation({
    mutationFn: async () => {
      if (!asset || !selectedLocation) throw new Error("Missing assignment data");
      return api.post(`/assets/${asset.asset_id}/link/${selectedLocation.location_id}`, {
        movement_reason: 'Assigned via Enterprise Drawer',
        movement_type: 'Assignment'
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['locations'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setSuccessView(true);
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail?.message || err.response?.data?.detail || 'Assignment failed');
    }
  });

  // ─── Filtering ─────────────────────────────────────────────────────────────
  const filteredLocations = useMemo(() => {
    if (!search) return locations;
    const s = search.toLowerCase();
    return locations.filter(loc => 
      loc.location_name.toLowerCase().includes(s) ||
      loc.location_id.toLowerCase().includes(s) ||
      (loc.plant && loc.plant.toLowerCase().includes(s)) ||
      (loc.area && loc.area.toLowerCase().includes(s))
    );
  }, [locations, search]);

  const filteredRejected = useMemo(() => {
    if (!search) return rejectedLocations;
    const s = search.toLowerCase();
    return rejectedLocations.filter(loc => 
      loc.location_name.toLowerCase().includes(s) ||
      loc.location_id.toLowerCase().includes(s) ||
      (loc.plant && loc.plant.toLowerCase().includes(s)) ||
      (loc.area && loc.area.toLowerCase().includes(s))
    );
  }, [rejectedLocations, search]);

  // ─── Handlers ──────────────────────────────────────────────────────────────
  const handleClose = () => {
    setTimeout(() => {
      setSearch('');
      setSelectedLocation(null);
      setReassignConfirmed(false);
      setSuccessView(false);
    }, 200);
    onClose();
  };

  const handleAssign = () => {
    assignMutation.mutate();
  };

  // ─── Renderers ─────────────────────────────────────────────────────────────
  if (!asset) return null;

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={handleClose}
      PaperProps={{
        sx: {
          width: isMobile ? '100%' : 600,
          backgroundColor: '#F4F5F7',
          display: 'flex',
          flexDirection: 'column'
        }
      }}
    >
      {/* Header */}
      <Box p={3} pb={2} display="flex" justifyContent="space-between" alignItems="center" bgcolor="white" borderBottom="1px solid #DFE1E6">
        <Typography variant="h5" fontWeight="bold" color="#172B4D">
          Asset Assignment
        </Typography>
        <IconButton onClick={handleClose} size="small">
          <X size={20} />
        </IconButton>
      </Box>

      {/* Scrollable Content */}
      <Box flex={1} overflow="auto" p={3}>
        
        {/* Section 1: Asset Information */}
        <Card sx={{ p: 2, mb: 3, borderRadius: 2, boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
          <Box display="flex" justifyContent="space-between" mb={2}>
            <Box>
              <Typography variant="h6" fontWeight="bold">{asset.asset_id}</Typography>
              <Typography variant="body2" color="text.secondary">Asset ID</Typography>
            </Box>
            <StatusChip status={asset.status} />
          </Box>
          <Box display="grid" gridTemplateColumns="1fr 1fr" gap={2}>
            <Box>
              <Typography variant="caption" color="text.secondary">Type</Typography>
              <Typography variant="body2" fontWeight="500">{asset.asset_type}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">Capacity</Typography>
              <Typography variant="body2" fontWeight="500">{asset.capacity || '-'}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">Serial</Typography>
              <Typography variant="body2" fontWeight="500">{asset.serial_number || '-'}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">Current Location</Typography>
              <Typography variant="body2" fontWeight="500">{asset.current_location_id || 'Unassigned'}</Typography>
            </Box>
          </Box>
        </Card>

        {successView ? (
          /* Success Experience */
          <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" py={5}>
            <CheckCircle size={64} color={theme.palette.success.main} />
            <Typography variant="h5" fontWeight="bold" mt={2} mb={1}>Asset Assigned Successfully</Typography>
            <Typography color="text.secondary" mb={4}>
              {asset.asset_id} is now assigned to {selectedLocation?.location_name}.
            </Typography>
            <Button variant="contained" size="large" onClick={handleClose} sx={{ px: 4 }}>
              Done
            </Button>
          </Box>
        ) : needsReassignConfirm ? (
          /* Reassign Confirmation */
          <Box textAlign="center" py={5} px={3}>
            <AlertTriangle size={48} color={theme.palette.warning.main} style={{ margin: '0 auto' }} />
            <Typography variant="h6" fontWeight="bold" mt={2}>This Asset is Already Assigned</Typography>
            <Typography color="text.secondary" mt={1} mb={4}>
              Current Location: <b>{asset.current_location_id}</b><br/>
              Do you want to move this asset?
            </Typography>
            <Box display="flex" gap={2} justifyContent="center">
              <Button variant="outlined" onClick={handleClose}>Cancel</Button>
              <Button variant="contained" color="warning" onClick={() => setReassignConfirmed(true)}>
                Reassign Asset
              </Button>
            </Box>
          </Box>
        ) : (
          /* Location Selection */
          <Collapse in={true}>
            <Typography variant="subtitle1" fontWeight="bold" mb={1} color="#5E6C84">
              Recommended Locations
            </Typography>
            <TextField
              fullWidth
              size="small"
              placeholder="Search by ID, Name, Plant, Area..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              sx={{ mb: 2, bgcolor: 'white', borderRadius: 1 }}
              InputProps={{
                startAdornment: <InputAdornment position="start"><Search size={18} /></InputAdornment>
              }}
            />

            {isError ? (
              <Box textAlign="center" py={4}>
                <Typography color="error" fontWeight="bold">
                  {(queryError as any)?.response?.status === 404 
                    ? "Compatible Locations API is unavailable. This is a system configuration issue." 
                    : "An unexpected server error occurred. Please try again or contact the administrator."}
                </Typography>
              </Box>
            ) : isLoading ? (
              <Box display="flex" justifyContent="center" py={4}><CircularProgress /></Box>
            ) : filteredLocations.length === 0 ? (
              <Box textAlign="center" py={4}>
                <Typography color="text.secondary">No compatible locations are available for this Asset.</Typography>
              </Box>
            ) : (
              <Box display="flex" flexDirection="column" gap={2}>
                {filteredLocations.map(loc => {
                  const isFull = loc.remaining_capacity <= 0;
                  const isSelected = selectedLocation?.location_id === loc.location_id;
                  
                  return (
                    <Card 
                      key={loc.location_id}
                      sx={{ 
                        borderRadius: 2, 
                        border: isSelected ? `2px solid ${theme.palette.primary.main}` : '2px solid transparent',
                        opacity: isFull ? 0.6 : 1,
                        transition: 'all 0.2s',
                        boxShadow: isSelected ? `0 4px 12px ${theme.palette.primary.light}40` : '0 1px 3px rgba(0,0,0,0.1)'
                      }}
                    >
                      <CardActionArea 
                        disabled={isFull} 
                        onClick={() => setSelectedLocation(loc)}
                        sx={{ p: 2 }}
                      >
                        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
                          <Box>
                            <Typography fontWeight="bold">{loc.location_name}</Typography>
                            <Typography variant="caption" color="text.secondary" fontFamily="monospace">
                              {loc.location_id}
                            </Typography>
                          </Box>
                          {isFull ? (
                            <Chip label="FULL" color="error" size="small" fontWeight="bold" />
                          ) : (
                            <Chip label={`${loc.remaining_capacity} left`} color="success" size="small" variant="outlined" />
                          )}
                        </Box>

                        <Box display="flex" gap={2} mb={1}>
                          <Typography variant="caption" color="text.secondary" display="flex" alignItems="center" gap={0.5}>
                            <MapPin size={12} /> {loc.plant || '-'} / {loc.area || '-'}
                          </Typography>
                        </Box>

                        <CapacityIndicator current={loc.current_assets_count} max={loc.max_assets} />
                      </CardActionArea>
                    </Card>
                  );
                })}
              </Box>
            )}

            {/* Rejected Locations Section */}
            {!isLoading && !isError && filteredRejected.length > 0 && (
              <Box mt={4}>
                <Typography variant="subtitle1" fontWeight="bold" mb={2} color="#5E6C84">
                  Rejected Locations
                </Typography>
                <Box display="flex" flexDirection="column" gap={2}>
                  {filteredRejected.map(loc => (
                    <Card 
                      key={loc.location_id}
                      sx={{ 
                        borderRadius: 2, 
                        border: '2px solid transparent',
                        bgcolor: '#FAFBFC',
                        boxShadow: 'none',
                        borderBottom: '1px solid #DFE1E6'
                      }}
                    >
                      <Box p={2}>
                        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
                          <Box>
                            <Typography fontWeight="bold" color="text.secondary">{loc.location_name}</Typography>
                            <Typography variant="caption" color="text.disabled" fontFamily="monospace">
                              {loc.location_id}
                            </Typography>
                          </Box>
                          <Chip label="Incompatible" size="small" variant="outlined" />
                        </Box>
                        
                        <Box display="flex" flexDirection="column" gap={1} mt={2}>
                          {loc.rejection_reasons?.map((reason, idx) => (
                            <Box key={idx} p={1} bgcolor="#FFF" borderRadius={1} border="1px solid #EBECF0">
                              <Typography variant="caption" fontWeight="bold" color="error.main" display="block">
                                {reason.reason}
                              </Typography>
                              <Box display="flex" justifyContent="space-between" mt={0.5}>
                                <Typography variant="caption" color="text.secondary">Expected: {reason.expected}</Typography>
                                <Typography variant="caption" color="text.secondary">Found: {reason.actual}</Typography>
                              </Box>
                            </Box>
                          ))}
                        </Box>
                      </Box>
                    </Card>
                  ))}
                </Box>
              </Box>
            )}
          </Collapse>
        )}
      </Box>

      {/* Footer Preview & Action */}
      {!successView && !needsReassignConfirm && (
        <Box p={3} bgcolor="white" borderTop="1px solid #DFE1E6" boxShadow="0 -4px 16px rgba(0,0,0,0.05)">
          <Collapse in={!!selectedLocation}>
            {selectedLocation && (
              <Box mb={2} p={2} bgcolor="#F4F5F7" borderRadius={2} border="1px dashed #B3BAC5">
                <Typography variant="caption" fontWeight="bold" color="text.secondary" mb={1} display="block">
                  Assignment Preview
                </Typography>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box textAlign="center">
                    <Typography variant="body2" fontWeight="bold">{asset.asset_id}</Typography>
                    <Typography variant="caption" color="text.secondary">Asset</Typography>
                  </Box>
                  <ArrowRight size={16} color="#8993A4" />
                  <Box textAlign="center">
                    <Typography variant="body2" fontWeight="bold">{selectedLocation.location_name}</Typography>
                    <Typography variant="caption" color="text.secondary">Location</Typography>
                  </Box>
                  <ArrowRight size={16} color="#8993A4" />
                  <Box textAlign="center">
                    <Typography variant="body2" fontWeight="bold" color="primary.main">
                      {selectedLocation.current_assets_count + 1}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">New Count</Typography>
                  </Box>
                </Box>
              </Box>
            )}
          </Collapse>
          
          <Box display="flex" gap={2} justifyContent="flex-end">
            <Button onClick={handleClose} variant="outlined" color="inherit">
              Cancel
            </Button>
            <Button 
              variant="contained" 
              color="primary" 
              disabled={!selectedLocation || assignMutation.isPending}
              onClick={handleAssign}
              startIcon={assignMutation.isPending ? <CircularProgress size={16} color="inherit" /> : <ArrowRightCircle size={18} />}
            >
              Assign Asset
            </Button>
          </Box>
        </Box>
      )}
    </Drawer>
  );
};

export default AssetAssignmentDrawer;
