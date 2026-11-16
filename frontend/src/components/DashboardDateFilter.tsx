import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Button,
  TextField,
  Typography,
  Chip,
  ButtonGroup,
  Alert,
  Tooltip,
} from '@mui/material';
import {
  Calendar,
  Filter,
  RotateCcw,
  AlertCircle,
  Clock,
} from 'lucide-react';
import {
  format,
  startOfWeek,
  startOfMonth,
  subMonths,
  startOfYear,
} from 'date-fns';

export type PresetKey = 'today' | 'this_week' | 'this_month' | 'last_3_months' | 'this_year' | 'custom';

export interface DateRange {
  fromDate: string;
  toDate: string;
  preset: PresetKey;
  label: string;
}

interface DashboardDateFilterProps {
  currentRange: DateRange;
  onRangeChange: (range: DateRange) => void;
  isLoading?: boolean;
}

export const getPresetRange = (key: PresetKey): { from: string; to: string; label: string } => {
  const now = new Date();
  const todayStr = format(now, 'yyyy-MM-dd');

  switch (key) {
    case 'today':
      return {
        from: todayStr,
        to: todayStr,
        label: 'Today',
      };
    case 'this_week':
      return {
        from: format(startOfWeek(now, { weekStartsOn: 1 }), 'yyyy-MM-dd'),
        to: todayStr,
        label: 'This Week',
      };
    case 'this_month':
      return {
        from: format(startOfMonth(now), 'yyyy-MM-dd'),
        to: todayStr,
        label: 'This Month',
      };
    case 'last_3_months':
      return {
        from: format(subMonths(now, 3), 'yyyy-MM-dd'),
        to: todayStr,
        label: 'Last 3 Months',
      };
    case 'this_year':
      return {
        from: format(startOfYear(now), 'yyyy-MM-dd'),
        to: todayStr,
        label: 'This Year',
      };
    default:
      return {
        from: format(startOfMonth(now), 'yyyy-MM-dd'),
        to: todayStr,
        label: 'This Month',
      };
  }
};

const formatReadableDate = (dateStr: string): string => {
  try {
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      const d = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
      return format(d, 'MMM d, yyyy');
    }
    return dateStr;
  } catch {
    return dateStr;
  }
};

const DashboardDateFilter: React.FC<DashboardDateFilterProps> = ({
  currentRange,
  onRangeChange,
  isLoading = false,
}) => {
  const [localFrom, setLocalFrom] = useState(currentRange.fromDate);
  const [localTo, setLocalTo] = useState(currentRange.toDate);
  const [activePreset, setActivePreset] = useState<PresetKey>(currentRange.preset);
  const [error, setError] = useState<string | null>(null);

  // Sync with prop changes if parent updates
  useEffect(() => {
    setLocalFrom(currentRange.fromDate);
    setLocalTo(currentRange.toDate);
    setActivePreset(currentRange.preset);
  }, [currentRange]);

  const validateDates = (from: string, to: string): boolean => {
    if (!from || !to) {
      setError('Both From and To dates are required.');
      return false;
    }
    if (from > to) {
      setError('From Date cannot be greater than To Date.');
      return false;
    }
    setError(null);
    return true;
  };

  const handlePresetClick = (presetKey: PresetKey) => {
    const range = getPresetRange(presetKey);
    setLocalFrom(range.from);
    setLocalTo(range.to);
    setActivePreset(presetKey);
    setError(null);
    onRangeChange({
      fromDate: range.from,
      toDate: range.to,
      preset: presetKey,
      label: range.label,
    });
  };

  const handleApplyCustom = () => {
    if (validateDates(localFrom, localTo)) {
      setActivePreset('custom');
      onRangeChange({
        fromDate: localFrom,
        toDate: localTo,
        preset: 'custom',
        label: `${formatReadableDate(localFrom)} – ${formatReadableDate(localTo)}`,
      });
    }
  };

  const handleReset = () => {
    const defaultRange = getPresetRange('this_month');
    setLocalFrom(defaultRange.from);
    setLocalTo(defaultRange.to);
    setActivePreset('this_month');
    setError(null);
    onRangeChange({
      fromDate: defaultRange.from,
      toDate: defaultRange.to,
      preset: 'this_month',
      label: defaultRange.label,
    });
  };

  const handleFromChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalFrom(val);
    setActivePreset('custom');
    if (val && localTo && val > localTo) {
      setError('From Date cannot be greater than To Date.');
    } else {
      setError(null);
    }
  };

  const handleToChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalTo(val);
    setActivePreset('custom');
    if (localFrom && val && localFrom > val) {
      setError('From Date cannot be greater than To Date.');
    } else {
      setError(null);
    }
  };

  const presets: { key: PresetKey; label: string }[] = [
    { key: 'today', label: 'Today' },
    { key: 'this_week', label: 'This Week' },
    { key: 'this_month', label: 'This Month' },
    { key: 'last_3_months', label: 'Last 3 Months' },
    { key: 'this_year', label: 'This Year' },
  ];

  return (
    <Card
      elevation={0}
      sx={{
        backgroundColor: '#FFFFFF',
        borderRadius: '12px',
        border: '1px solid #E2E8F0',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
        mb: 3.5,
      }}
    >
      <CardContent sx={{ p: { xs: 2, sm: 2.5 }, '&:last-child': { pb: { xs: 2, sm: 2.5 } } }}>
        <Box
          sx={{
            display: 'flex',
            flexDirection: { xs: 'column', lg: 'row' },
            alignItems: { xs: 'stretch', lg: 'center' },
            justifyContent: 'space-between',
            gap: 2,
          }}
        >
          {/* Left: Presets Group */}
          <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mr: 1 }}>
              <Clock size={16} color="#475569" />
              <Typography variant="body2" sx={{ fontWeight: 600, color: '#334155', fontSize: '0.82rem' }}>
                Quick Presets:
              </Typography>
            </Box>

            <ButtonGroup size="small" variant="outlined" sx={{ flexWrap: 'wrap' }}>
              {presets.map((p) => {
                const isActive = activePreset === p.key;
                return (
                  <Button
                    key={p.key}
                    onClick={() => handlePresetClick(p.key)}
                    variant={isActive ? 'contained' : 'outlined'}
                    disabled={isLoading}
                    sx={{
                      fontSize: '0.78rem',
                      fontWeight: isActive ? 600 : 500,
                      textTransform: 'none',
                      py: 0.6,
                      px: 1.5,
                      borderColor: isActive ? '#1E40AF' : '#CBD5E1',
                      backgroundColor: isActive ? '#1E40AF' : 'transparent',
                      color: isActive ? '#FFFFFF' : '#475569',
                      '&:hover': {
                        backgroundColor: isActive ? '#1D4ED8' : '#F1F5F9',
                        borderColor: isActive ? '#1D4ED8' : '#94A3B8',
                      },
                    }}
                  >
                    {p.label}
                  </Button>
                );
              })}
            </ButtonGroup>
          </Box>

          {/* Right: Custom Date Pickers, Apply, and Reset */}
          <Box
            sx={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              gap: 1.5,
            }}
          >
            <TextField
              label="From Date"
              type="date"
              size="small"
              value={localFrom}
              onChange={handleFromChange}
              InputLabelProps={{ shrink: true }}
              inputProps={{ max: localTo || undefined }}
              sx={{
                width: { xs: '100%', sm: 145 },
                '& .MuiInputBase-input': { fontSize: '0.82rem', py: 0.8 },
                '& .MuiInputLabel-root': { fontSize: '0.82rem' },
              }}
              error={Boolean(error)}
            />

            <TextField
              label="To Date"
              type="date"
              size="small"
              value={localTo}
              onChange={handleToChange}
              InputLabelProps={{ shrink: true }}
              inputProps={{ min: localFrom || undefined }}
              sx={{
                width: { xs: '100%', sm: 145 },
                '& .MuiInputBase-input': { fontSize: '0.82rem', py: 0.8 },
                '& .MuiInputLabel-root': { fontSize: '0.82rem' },
              }}
              error={Boolean(error)}
            />

            <Tooltip title={error || 'Apply date range filter'}>
              <span>
                <Button
                  variant="contained"
                  size="small"
                  startIcon={<Filter size={15} />}
                  onClick={handleApplyCustom}
                  disabled={isLoading || Boolean(error)}
                  sx={{
                    textTransform: 'none',
                    fontWeight: 600,
                    fontSize: '0.82rem',
                    backgroundColor: '#1E40AF',
                    py: 0.8,
                    px: 1.8,
                    '&:hover': { backgroundColor: '#1D4ED8' },
                  }}
                >
                  Apply
                </Button>
              </span>
            </Tooltip>

            <Tooltip title="Reset to default (This Month)">
              <Button
                variant="outlined"
                size="small"
                startIcon={<RotateCcw size={14} />}
                onClick={handleReset}
                disabled={isLoading}
                sx={{
                  textTransform: 'none',
                  fontWeight: 500,
                  fontSize: '0.82rem',
                  color: '#64748B',
                  borderColor: '#CBD5E1',
                  py: 0.8,
                  px: 1.5,
                  '&:hover': {
                    borderColor: '#94A3B8',
                    backgroundColor: '#F8FAFC',
                    color: '#334155',
                  },
                }}
              >
                Reset
              </Button>
            </Tooltip>
          </Box>
        </Box>

        {/* Validation Error Message */}
        {error && (
          <Alert
            severity="error"
            icon={<AlertCircle size={18} />}
            sx={{
              mt: 2,
              py: 0.25,
              fontSize: '0.82rem',
              borderRadius: '8px',
            }}
          >
            {error}
          </Alert>
        )}

        {/* Active Filter Indicator Badge */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            mt: 2,
            pt: 1.5,
            borderTop: '1px solid #F1F5F9',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
            <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600, fontSize: '0.75rem' }}>
              ACTIVE RANGE:
            </Typography>
            <Chip
              icon={<Calendar size={13} style={{ marginLeft: 4 }} />}
              label={`${formatReadableDate(currentRange.fromDate)}  —  ${formatReadableDate(currentRange.toDate)} (${currentRange.label})`}
              size="small"
              sx={{
                fontWeight: 600,
                fontSize: '0.76rem',
                backgroundColor: '#EFF6FF',
                color: '#1E40AF',
                borderColor: '#BFDBFE',
                border: '1px solid',
              }}
            />
          </Box>

          <Typography variant="caption" sx={{ color: '#94A3B8', fontSize: '0.72rem' }}>
            Metrics & charts update dynamically based on this period
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default DashboardDateFilter;
