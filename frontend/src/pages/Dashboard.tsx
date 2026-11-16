import React, { useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  List,
  ListItem,
  ListItemText,
  Chip,
  Skeleton,
  Button,
  Alert,
  Tooltip as MuiTooltip,
  IconButton,
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import {
  ShieldAlert,
  Wrench,
  AlertTriangle,
  MapPin,
  Clock,
  TrendingUp,
  Shield,
  CheckCircle2,
  XCircle,
  BarChart3,
  PieChart as PieChartIcon,
  RefreshCw,
  ArrowUpRight,
  ChevronRight,
  ClipboardCheck,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import DashboardDateFilter, {
  type DateRange,
  getPresetRange,
} from '../components/DashboardDateFilter';

// ─── Interfaces ──────────────────────────────────────────────────────────────
interface DashboardStats {
  total_locations: number;
  total_assets: number;
  installed_assets: number;
  unassigned_assets: number;
  inspection_due_today: number;
  inspection_completed_today: number;
  open_maintenance: number;
  expired_assets: number;
  refill_due: number;
  compliance_percent: number;
  overdue_inspections: number;
  inspections_in_range?: number | null;
  maintenance_in_range?: number | null;
  inspections_passed?: number | null;
  inspections_failed?: number | null;
}

interface MonthlyTrend {
  month: string;
  inspections: number;
  maintenance: number;
  passed: number;
  failed: number;
}

interface ActivityItem {
  id: number;
  action: string;
  table: string;
  record_id: string;
  user: string;
  timestamp: string;
}

interface InspectionStatusItem {
  status: string;
  count: number;
}

interface OverdueLocation {
  location_id: string;
  location_name: string;
  last_inspection: string | null;
  days_overdue: number;
  current_asset_id: string | null;
  department?: string | null;
  area?: string | null;
}

interface RecentMaintenanceTicket {
  maintenance_id: number;
  asset_id: string;
  location_id: string;
  issue: string;
  priority: string;
  status: string;
  assigned_to?: string | null;
  opened_date: string | null;
}

// ─── Stat Card Component ──────────────────────────────────────────────────────
interface ModernStatCardProps {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  accentColor: string;
  subtitle?: string;
  loading?: boolean;
  highlight?: boolean;
}

const ModernStatCard: React.FC<ModernStatCardProps> = ({
  title,
  value,
  icon,
  accentColor,
  subtitle,
  loading,
}) => (
  <Card
    elevation={0}
    sx={{
      height: '100%',
      minHeight: 135,
      backgroundColor: '#FFFFFF',
      borderRadius: '12px',
      border: '1px solid #E2E8F0',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02)',
      transition: 'transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      '&:hover': {
        transform: 'translateY(-2px)',
        boxShadow: '0 8px 16px -2px rgba(0, 0, 0, 0.08), 0 4px 8px -2px rgba(0, 0, 0, 0.04)',
        borderColor: '#CBD5E1',
      },
    }}
  >
    <CardContent sx={{ p: 2.5, pb: '20px !important' }}>
      <Box display="flex" alignItems="flex-start" justifyContent="space-between" mb={1.5}>
        <Typography
          variant="caption"
          sx={{
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color: '#64748B',
            fontSize: '0.73rem',
          }}
        >
          {title}
        </Typography>
        <Box
          sx={{
            p: 1.2,
            borderRadius: '10px',
            backgroundColor: `${accentColor}18`,
            color: accentColor,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {icon}
        </Box>
      </Box>

      {loading ? (
        <Skeleton width={100} height={42} sx={{ my: 0.5 }} />
      ) : (
        <Typography
          variant="h4"
          sx={{
            fontWeight: 800,
            color: '#0F172A',
            fontSize: '1.9rem',
            letterSpacing: '-0.02em',
            lineHeight: 1.1,
            mb: 0.75,
          }}
        >
          {value}
        </Typography>
      )}

      {subtitle && (
        <Typography
          variant="caption"
          sx={{
            color: '#64748B',
            fontWeight: 500,
            fontSize: '0.77rem',
            display: 'block',
          }}
        >
          {subtitle}
        </Typography>
      )}
    </CardContent>
  </Card>
);

// ─── Custom Tooltip for Trends Chart ──────────────────────────────────────────
const CustomTrendTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const inspections = payload.find((p: any) => p.dataKey === 'inspections')?.value ?? 0;
    const passed = payload.find((p: any) => p.dataKey === 'passed')?.value ?? 0;
    const failed = payload.find((p: any) => p.dataKey === 'failed')?.value ?? 0;
    const maintenance = payload.find((p: any) => p.dataKey === 'maintenance')?.value ?? 0;
    const passRate = inspections > 0 ? Math.round((passed / inspections) * 100) : 0;

    return (
      <Box
        sx={{
          backgroundColor: '#0F172A',
          color: '#FFFFFF',
          p: 1.75,
          borderRadius: '8px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.3)',
          border: '1px solid #334155',
          fontSize: '0.8rem',
          minWidth: 180,
        }}
      >
        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1, color: '#38BDF8' }}>
          {label}
        </Typography>
        <Box display="flex" justifyContent="space-between" mb={0.5}>
          <span style={{ color: '#93C5FD' }}>Inspections:</span>
          <strong>{inspections}</strong>
        </Box>
        <Box display="flex" justifyContent="space-between" mb={0.5}>
          <span style={{ color: '#86EFAC' }}>Passed:</span>
          <strong>{passed}</strong>
        </Box>
        <Box display="flex" justifyContent="space-between" mb={0.5}>
          <span style={{ color: '#FCA5A5' }}>Failed:</span>
          <strong>{failed}</strong>
        </Box>
        <Box display="flex" justifyContent="space-between" mb={0.75}>
          <span style={{ color: '#FDE047' }}>Maintenance:</span>
          <strong>{maintenance}</strong>
        </Box>
        {inspections > 0 && (
          <Box
            sx={{
              pt: 0.75,
              mt: 0.5,
              borderTop: '1px solid #334155',
              display: 'flex',
              justifyContent: 'space-between',
              color: '#38BDF8',
              fontWeight: 600,
            }}
          >
            <span>Pass Rate:</span>
            <span>{passRate}%</span>
          </Box>
        )}
      </Box>
    );
  }
  return null;
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
const getActionColor = (action: string): 'default' | 'primary' | 'success' | 'warning' | 'error' => {
  if (action === 'CREATE') return 'success';
  if (action === 'UPDATE' || action === 'ASSIGN') return 'primary';
  if (action === 'DELETE' || action === 'UNLINK') return 'error';
  if (action === 'STATUS_CHANGE') return 'warning';
  return 'default';
};

const getPriorityColor = (priority: string): { bg: string; text: string } => {
  const p = (priority || '').toUpperCase();
  if (p === 'HIGH' || p === 'CRITICAL') return { bg: '#FEE2E2', text: '#DC2626' };
  if (p === 'MEDIUM') return { bg: '#FEF3C7', text: '#D97706' };
  return { bg: '#F1F5F9', text: '#475569' };
};

const getStatusBadge = (status: string): { bg: string; text: string } => {
  const s = (status || '').toUpperCase();
  if (s === 'CLOSED' || s === 'VERIFIED') return { bg: '#DCFCE7', text: '#15803D' };
  if (s === 'IN PROGRESS') return { bg: '#DBEAFE', text: '#1D4ED8' };
  return { bg: '#FFEDD5', text: '#C2410C' };
};

const timeAgo = (timestamp: string) => {
  if (!timestamp) return '-';
  const diff = Date.now() - new Date(timestamp).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
};

const PIE_COLORS = ['#2563EB', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4', '#64748B'];

// ─── Main Dashboard Component ─────────────────────────────────────────────────
const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  // Date Range Filter State — default is "this_month"
  const defaultPreset = getPresetRange('this_month');
  const [dateRange, setDateRange] = useState<DateRange>({
    fromDate: defaultPreset.from,
    toDate: defaultPreset.to,
    preset: 'this_month',
    label: defaultPreset.label,
  });

  // ─── Query 1: Dashboard Stats ───────────────────────────────────────────────
  const {
    data: stats,
    isLoading: statsLoading,
    isError: statsError,
    refetch: refetchStats,
  } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats', dateRange.fromDate, dateRange.toDate],
    queryFn: async () => {
      const res = await api.get('/dashboard/stats', {
        params: {
          start_date: dateRange.fromDate,
          end_date: dateRange.toDate,
        },
      });
      return res.data?.data || res.data;
    },
    refetchInterval: 60_000,
  });

  // ─── Query 2: Monthly Trends ────────────────────────────────────────────────
  const {
    data: trend,
    isLoading: trendLoading,
    isError: trendError,
    refetch: refetchTrend,
  } = useQuery<MonthlyTrend[]>({
    queryKey: ['dashboard-trend', dateRange.fromDate, dateRange.toDate],
    queryFn: async () => {
      const res = await api.get('/dashboard/monthly-trend', {
        params: {
          start_date: dateRange.fromDate,
          end_date: dateRange.toDate,
        },
      });
      return Array.isArray(res.data?.data) ? res.data.data : Array.isArray(res.data) ? res.data : [];
    },
  });

  // ─── Query 3: Asset Type Distribution ───────────────────────────────────────
  const { data: assetTypeData, isLoading: assetTypeLoading } = useQuery<{ asset_type: string; count: number }[]>({
    queryKey: ['dashboard-asset-types'],
    queryFn: async () => {
      const res = await api.get('/dashboard/asset-type-distribution');
      return Array.isArray(res.data?.data) ? res.data.data : Array.isArray(res.data) ? res.data : [];
    },
  });

  // ─── Query 4: Inspection Status Distribution (in date range) ────────────────
  const { data: inspectionStatusData, isLoading: statusLoading } = useQuery<InspectionStatusItem[]>({
    queryKey: ['dashboard-inspection-status', dateRange.fromDate, dateRange.toDate],
    queryFn: async () => {
      const res = await api.get('/dashboard/inspection-status-distribution', {
        params: {
          start_date: dateRange.fromDate,
          end_date: dateRange.toDate,
        },
      });
      return Array.isArray(res.data?.data) ? res.data.data : Array.isArray(res.data) ? res.data : [];
    },
  });

  // ─── Query 5: Overdue Inspections ───────────────────────────────────────────
  const { data: overdueData, isLoading: overdueLoading } = useQuery<OverdueLocation[]>({
    queryKey: ['dashboard-overdue-inspections'],
    queryFn: async () => {
      const res = await api.get('/dashboard/overdue-inspections', { params: { limit: 6 } });
      return Array.isArray(res.data?.data) ? res.data.data : Array.isArray(res.data) ? res.data : [];
    },
    refetchInterval: 60_000,
  });

  // ─── Query 6: Recent Maintenance Activities ─────────────────────────────────
  const { data: recentMaintenanceData, isLoading: maintenanceLoading } = useQuery<RecentMaintenanceTicket[]>({
    queryKey: ['dashboard-recent-maintenance', dateRange.fromDate, dateRange.toDate],
    queryFn: async () => {
      const res = await api.get('/dashboard/recent-maintenance', {
        params: {
          start_date: dateRange.fromDate,
          end_date: dateRange.toDate,
          limit: 6,
        },
      });
      return Array.isArray(res.data?.data) ? res.data.data : Array.isArray(res.data) ? res.data : [];
    },
  });

  // ─── Query 7: Audit Activity Feed ───────────────────────────────────────────
  const { data: activityData, isLoading: activityLoading } = useQuery<{ activity: ActivityItem[] }>({
    queryKey: ['dashboard-activity'],
    queryFn: async () => {
      const res = await api.get('/dashboard/recent-activity', { params: { limit: 10 } });
      return res.data?.data || res.data;
    },
    refetchInterval: 30_000,
  });

  const activities = activityData?.activity ?? [];
  const anyLoading = statsLoading || trendLoading || statusLoading;

  // ─── KPI Card Configurations ───────────────────────────────────────────────
  const statCards = [
    {
      title: 'Total Assets',
      value: stats?.total_assets ?? 0,
      icon: <Shield size={22} />,
      accentColor: '#2563EB', // Blue
      subtitle: `${stats?.installed_assets ?? 0} installed • ${stats?.unassigned_assets ?? 0} in stock`,
    },
    {
      title: 'Inspections Due',
      value: stats?.inspection_due_today ?? 0,
      icon: <AlertTriangle size={22} />,
      accentColor: '#D97706', // Amber
      subtitle: `${stats?.overdue_inspections ?? 0} locations overdue`,
    },
    {
      title: 'Open Maintenance',
      value: stats?.open_maintenance ?? 0,
      icon: <Wrench size={22} />,
      accentColor: '#EA580C', // Orange / Red
      subtitle:
        stats?.maintenance_in_range !== null && stats?.maintenance_in_range !== undefined
          ? `${stats.maintenance_in_range} opened in period`
          : 'Pending resolution',
    },
    {
      title: 'Expired Assets',
      value: stats?.expired_assets ?? 0,
      icon: <ShieldAlert size={22} />,
      accentColor: '#DC2626', // Red
      subtitle: `${stats?.refill_due ?? 0} refill overdue`,
    },
    {
      title: 'Total Locations',
      value: stats?.total_locations ?? 0,
      icon: <MapPin size={22} />,
      accentColor: '#1E40AF', // Navy
      subtitle: `${stats?.compliance_percent ?? 0}% active spot coverage`,
    },
    {
      title: 'Compliance',
      value: `${Math.round(stats?.compliance_percent ?? 0)}%`,
      icon: <TrendingUp size={22} />,
      accentColor: '#059669', // Emerald
      subtitle: `${stats?.installed_assets ?? 0} / ${stats?.total_locations ?? 0} locations active`,
    },
  ];

  // Calculate totals for inspection status
  const totalPeriodInspections = (inspectionStatusData || []).reduce((acc, curr) => acc + curr.count, 0);
  const passedInspections = (inspectionStatusData || []).find((s) => s.status.toLowerCase() === 'pass')?.count ?? 0;
  const passRate = totalPeriodInspections > 0 ? Math.round((passedInspections / totalPeriodInspections) * 100) : 0;

  return (
    <Box sx={{ maxWidth: 1600, mx: 'auto' }}>
      {/* ─── Top Header Row ─────────────────────────────────────────────────── */}
      <Box
        display="flex"
        flexDirection={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'flex-start', sm: 'center' }}
        gap={1}
        mb={2.5}
      >
        <Box>
          <Typography
            variant="h4"
            sx={{
              fontWeight: 800,
              color: '#0F172A',
              fontSize: { xs: '1.5rem', sm: '1.9rem' },
              letterSpacing: '-0.02em',
            }}
          >
            Dashboard Overview
          </Typography>
          <Typography variant="body2" sx={{ color: '#64748B', mt: 0.3 }}>
            Fire safety asset operational readiness, compliance metrics, and maintenance tracking.
          </Typography>
        </Box>

        <Box display="flex" alignItems="center" gap={1.5}>
          {anyLoading && (
            <Chip
              icon={<CircularProgress size={14} color="inherit" />}
              label="Syncing live data..."
              size="small"
              sx={{ backgroundColor: '#EFF6FF', color: '#1E40AF', fontWeight: 500 }}
            />
          )}
          <MuiTooltip title="Refresh all data">
            <IconButton
              size="small"
              onClick={() => {
                refetchStats();
                refetchTrend();
              }}
              sx={{
                border: '1px solid #E2E8F0',
                backgroundColor: '#FFFFFF',
                borderRadius: '8px',
                p: 1,
                '&:hover': { backgroundColor: '#F8FAFC' },
              }}
            >
              <RefreshCw size={16} color="#475569" />
            </IconButton>
          </MuiTooltip>
        </Box>
      </Box>

      {/* ─── Error Alert State ──────────────────────────────────────────────── */}
      {(statsError || trendError) && (
        <Alert
          severity="error"
          sx={{ mb: 3, borderRadius: '10px' }}
          action={
            <Button
              color="inherit"
              size="small"
              onClick={() => {
                refetchStats();
                refetchTrend();
              }}
            >
              Retry
            </Button>
          }
        >
          Failed to load some dashboard metrics. The backend service may be temporarily unavailable.
        </Alert>
      )}

      {/* ─── Date Range Filter Toolbar ──────────────────────────────────────── */}
      <DashboardDateFilter
        currentRange={dateRange}
        onRangeChange={(newRange) => setDateRange(newRange)}
        isLoading={anyLoading}
      />

      {/* ─── KPI Cards Grid ─────────────────────────────────────────────────── */}
      <Grid container spacing={2.5} sx={{ mb: 3.5 }}>
        {statCards.map((stat, idx) => (
          <Grid item xs={12} sm={6} md={4} lg={2} key={idx}>
            <ModernStatCard {...stat} loading={statsLoading} />
          </Grid>
        ))}
      </Grid>

      {/* ─── Charts Row 1: Monthly Trends & Asset Distribution ──────────────── */}
      <Grid container spacing={3} sx={{ mb: 3.5 }}>
        {/* Left: Monthly Trends Chart */}
        <Grid item xs={12} lg={8}>
          <Card
            elevation={0}
            sx={{
              height: '100%',
              backgroundColor: '#FFFFFF',
              borderRadius: '12px',
              border: '1px solid #E2E8F0',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 700, color: '#0F172A', fontSize: '1.05rem' }}>
                    Inspection vs Maintenance Trends
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#64748B' }}>
                    Monthly breakdown of total inspections, pass/fail results, and opened maintenance
                  </Typography>
                </Box>
                <Chip
                  label={dateRange.label}
                  size="small"
                  sx={{ backgroundColor: '#F1F5F9', color: '#334155', fontWeight: 600, fontSize: '0.74rem' }}
                />
              </Box>

              <Box sx={{ height: 320, width: '100%', mt: 2 }}>
                {trendLoading ? (
                  <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" height="100%">
                    <CircularProgress size={32} sx={{ color: '#1E40AF', mb: 1.5 }} />
                    <Typography variant="caption" color="text.secondary">
                      Loading trend analytics...
                    </Typography>
                  </Box>
                ) : !trend || trend.length === 0 ? (
                  <Box
                    display="flex"
                    flexDirection="column"
                    alignItems="center"
                    justifyContent="center"
                    height="100%"
                    sx={{ backgroundColor: '#F8FAFC', borderRadius: '8px', p: 3 }}
                  >
                    <BarChart3 size={40} color="#94A3B8" style={{ marginBottom: 8 }} />
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#475569' }}>
                      No trend data found
                    </Typography>
                    <Typography variant="caption" color="text.secondary" textAlign="center">
                      There are no inspection or maintenance records recorded for the selected date range.
                    </Typography>
                  </Box>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={trend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                      <XAxis
                        dataKey="month"
                        axisLine={{ stroke: '#E2E8F0' }}
                        tickLine={false}
                        tick={{ fontSize: 12, fill: '#64748B' }}
                      />
                      <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fontSize: 12, fill: '#64748B' }}
                        allowDecimals={false}
                      />
                      <RechartsTooltip content={<CustomTrendTooltip />} />
                      <Legend
                        wrapperStyle={{ paddingTop: 14, fontSize: '0.8rem' }}
                        iconType="circle"
                        iconSize={8}
                      />
                      <Bar dataKey="inspections" fill="#1E40AF" radius={[4, 4, 0, 0]} name="Inspections" />
                      <Bar dataKey="passed" fill="#10B981" radius={[4, 4, 0, 0]} name="Passed" />
                      <Bar dataKey="failed" fill="#EF4444" radius={[4, 4, 0, 0]} name="Failed" />
                      <Bar dataKey="maintenance" fill="#F59E0B" radius={[4, 4, 0, 0]} name="Maintenance" />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Right: Asset Type Distribution (Doughnut) */}
        <Grid item xs={12} lg={4}>
          <Card
            elevation={0}
            sx={{
              height: '100%',
              backgroundColor: '#FFFFFF',
              borderRadius: '12px',
              border: '1px solid #E2E8F0',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <CardContent sx={{ p: 3, flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
              <Box mb={2}>
                <Typography variant="h6" sx={{ fontWeight: 700, color: '#0F172A', fontSize: '1.05rem' }}>
                  Asset Type Distribution
                </Typography>
                <Typography variant="caption" sx={{ color: '#64748B' }}>
                  Inventory breakdown across extinguisher classes
                </Typography>
              </Box>

              {assetTypeLoading ? (
                <Box display="flex" alignItems="center" justifyContent="center" height={280}>
                  <CircularProgress size={32} sx={{ color: '#1E40AF' }} />
                </Box>
              ) : !assetTypeData || assetTypeData.length === 0 ? (
                <Box
                  display="flex"
                  flexDirection="column"
                  alignItems="center"
                  justifyContent="center"
                  height={280}
                  sx={{ backgroundColor: '#F8FAFC', borderRadius: '8px' }}
                >
                  <PieChartIcon size={40} color="#94A3B8" style={{ marginBottom: 8 }} />
                  <Typography variant="body2" sx={{ fontWeight: 600, color: '#475569' }}>
                    No asset inventory records
                  </Typography>
                </Box>
              ) : (
                <>
                  <Box sx={{ height: 210, width: '100%', position: 'relative' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={assetTypeData}
                          dataKey="count"
                          nameKey="asset_type"
                          cx="50%"
                          cy="50%"
                          innerRadius={55}
                          outerRadius={85}
                          paddingAngle={3}
                        >
                          {assetTypeData.map((_, idx) => (
                            <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                          ))}
                        </Pie>
                        <RechartsTooltip
                          formatter={(value: any, name: any) => [`${value} units`, name]}
                          contentStyle={{
                            backgroundColor: '#0F172A',
                            borderColor: '#334155',
                            color: '#FFFFFF',
                            borderRadius: '8px',
                            fontSize: '0.8rem',
                          }}
                          itemStyle={{ color: '#FFFFFF' }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </Box>

                  {/* Summary Legend Breakdown */}
                  <Box sx={{ mt: 'auto', pt: 1.5, borderTop: '1px solid #F1F5F9' }}>
                    <Grid container spacing={1}>
                      {assetTypeData.slice(0, 4).map((item, idx) => (
                        <Grid item xs={6} key={item.asset_type}>
                          <Box display="flex" alignItems="center" gap={1}>
                            <Box
                              sx={{
                                width: 10,
                                height: 10,
                                borderRadius: '50%',
                                backgroundColor: PIE_COLORS[idx % PIE_COLORS.length],
                                flexShrink: 0,
                              }}
                            />
                            <Typography
                              variant="caption"
                              sx={{
                                color: '#475569',
                                fontWeight: 500,
                                fontSize: '0.75rem',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              {item.asset_type}: <strong>{item.count}</strong>
                            </Typography>
                          </Box>
                        </Grid>
                      ))}
                    </Grid>
                  </Box>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* ─── Charts Row 2: Inspection Status Distribution & Overdue Inspections */}
      <Grid container spacing={3} sx={{ mb: 3.5 }}>
        {/* Left: Inspection Status Distribution (in Date Range) */}
        <Grid item xs={12} lg={4}>
          <Card
            elevation={0}
            sx={{
              height: '100%',
              backgroundColor: '#FFFFFF',
              borderRadius: '12px',
              border: '1px solid #E2E8F0',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <CardContent sx={{ p: 3, flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
              <Box mb={2}>
                <Typography variant="h6" sx={{ fontWeight: 700, color: '#0F172A', fontSize: '1.05rem' }}>
                  Inspection Status Distribution
                </Typography>
                <Typography variant="caption" sx={{ color: '#64748B' }}>
                  Pass vs Fail ratio in {dateRange.label}
                </Typography>
              </Box>

              {statusLoading ? (
                <Box display="flex" alignItems="center" justifyContent="center" height={220}>
                  <CircularProgress size={30} sx={{ color: '#1E40AF' }} />
                </Box>
              ) : !inspectionStatusData || inspectionStatusData.length === 0 ? (
                <Box
                  display="flex"
                  flexDirection="column"
                  alignItems="center"
                  justifyContent="center"
                  height={220}
                  sx={{ backgroundColor: '#F8FAFC', borderRadius: '8px', p: 3 }}
                >
                  <ClipboardCheck size={36} color="#94A3B8" style={{ marginBottom: 8 }} />
                  <Typography variant="body2" sx={{ fontWeight: 600, color: '#475569' }}>
                    No inspections in range
                  </Typography>
                  <Typography variant="caption" color="text.secondary" textAlign="center">
                    Select a wider date range to inspect compliance records.
                  </Typography>
                </Box>
              ) : (
                <>
                  <Box sx={{ height: 180, width: '100%', position: 'relative' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={inspectionStatusData}
                          dataKey="count"
                          nameKey="status"
                          cx="50%"
                          cy="50%"
                          innerRadius={50}
                          outerRadius={75}
                          paddingAngle={4}
                        >
                          {inspectionStatusData.map((item, idx) => {
                            const isPass = item.status.toLowerCase() === 'pass';
                            const isFail = item.status.toLowerCase() === 'fail';
                            const color = isPass ? '#10B981' : isFail ? '#EF4444' : '#64748B';
                            return <Cell key={idx} fill={color} />;
                          })}
                        </Pie>
                        <RechartsTooltip
                          formatter={(value: any, name: any) => [`${value} inspections`, name]}
                          contentStyle={{
                            backgroundColor: '#0F172A',
                            borderColor: '#334155',
                            color: '#FFFFFF',
                            borderRadius: '8px',
                            fontSize: '0.8rem',
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </Box>

                  {/* Status Breakdown Pills */}
                  <Box sx={{ mt: 'auto', pt: 2, borderTop: '1px solid #F1F5F9' }}>
                    <Box display="flex" justifyContent="space-around" alignItems="center">
                      <Box display="flex" alignItems="center" gap={1}>
                        <CheckCircle2 size={16} color="#10B981" />
                        <Typography variant="caption" sx={{ fontWeight: 600, color: '#1E293B' }}>
                          Pass: {passedInspections}
                        </Typography>
                      </Box>
                      <Divider orientation="vertical" flexItem />
                      <Box display="flex" alignItems="center" gap={1}>
                        <XCircle size={16} color="#EF4444" />
                        <Typography variant="caption" sx={{ fontWeight: 600, color: '#1E293B' }}>
                          Fail: {totalPeriodInspections - passedInspections}
                        </Typography>
                      </Box>
                      <Divider orientation="vertical" flexItem />
                      <Chip
                        label={`${passRate}% Pass Rate`}
                        size="small"
                        color={passRate >= 80 ? 'success' : passRate >= 50 ? 'warning' : 'error'}
                        sx={{ fontWeight: 700, fontSize: '0.72rem' }}
                      />
                    </Box>
                  </Box>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Right: Overdue Inspections & Action Required */}
        <Grid item xs={12} lg={8}>
          <Card
            elevation={0}
            sx={{
              height: '100%',
              backgroundColor: '#FFFFFF',
              borderRadius: '12px',
              border: '1px solid #E2E8F0',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Box>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography variant="h6" sx={{ fontWeight: 700, color: '#0F172A', fontSize: '1.05rem' }}>
                      Overdue Inspections Requiring Action
                    </Typography>
                    {overdueData && overdueData.length > 0 && (
                      <Chip
                        label={`${overdueData.length} Overdue`}
                        size="small"
                        color="error"
                        sx={{ fontWeight: 700, fontSize: '0.72rem', height: 20 }}
                      />
                    )}
                  </Box>
                  <Typography variant="caption" sx={{ color: '#64748B' }}>
                    Active plant locations that have missed their scheduled inspection frequency
                  </Typography>
                </Box>

                <Button
                  size="small"
                  endIcon={<ArrowUpRight size={15} />}
                  onClick={() => navigate('/inspections')}
                  sx={{ textTransform: 'none', fontWeight: 600, fontSize: '0.8rem', color: '#1E40AF' }}
                >
                  View All Inspections
                </Button>
              </Box>

              {overdueLoading ? (
                <Box display="flex" alignItems="center" justifyContent="center" height={220}>
                  <CircularProgress size={30} sx={{ color: '#1E40AF' }} />
                </Box>
              ) : !overdueData || overdueData.length === 0 ? (
                <Box
                  display="flex"
                  flexDirection="column"
                  alignItems="center"
                  justifyContent="center"
                  height={220}
                  sx={{ backgroundColor: '#F0FDF4', borderRadius: '8px', p: 3, border: '1px dashed #BBF7D0' }}
                >
                  <CheckCircle2 size={38} color="#16A34A" style={{ marginBottom: 8 }} />
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#166534' }}>
                    All Locations Up to Date
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#15803D', textAlign: 'center' }}>
                    No locations currently have overdue inspections. Excellent compliance record!
                  </Typography>
                </Box>
              ) : (
                <Box sx={{ overflowX: 'auto' }}>
                  <List dense disablePadding>
                    {overdueData.slice(0, 5).map((loc, idx) => (
                      <React.Fragment key={loc.location_id}>
                        <ListItem
                          sx={{
                            px: 1.5,
                            py: 1.25,
                            borderRadius: '8px',
                            '&:hover': { backgroundColor: '#F8FAFC' },
                          }}
                        >
                          <Grid container alignItems="center" spacing={1}>
                            <Grid item xs={12} sm={4}>
                              <Typography variant="body2" sx={{ fontWeight: 600, color: '#0F172A' }}>
                                {loc.location_name}
                              </Typography>
                              <Typography variant="caption" sx={{ color: '#64748B', fontFamily: 'monospace' }}>
                                {loc.location_id}
                              </Typography>
                            </Grid>

                            <Grid item xs={6} sm={3}>
                              <Typography variant="caption" sx={{ color: '#475569', display: 'block' }}>
                                <strong>Dept:</strong> {loc.department || 'General'}
                              </Typography>
                              <Typography variant="caption" sx={{ color: '#64748B' }}>
                                {loc.area || '-'}
                              </Typography>
                            </Grid>

                            <Grid item xs={6} sm={3}>
                              <Typography variant="caption" sx={{ color: '#64748B', display: 'block' }}>
                                Last Inspected:
                              </Typography>
                              <Typography variant="caption" sx={{ fontWeight: 500, color: '#334155' }}>
                                {loc.last_inspection ? loc.last_inspection.split('T')[0] : 'Never inspected'}
                              </Typography>
                            </Grid>

                            <Grid item xs={12} sm={2} textAlign={{ xs: 'left', sm: 'right' }}>
                              <Chip
                                label={loc.days_overdue >= 900 ? 'Not inspected' : `${loc.days_overdue}d overdue`}
                                size="small"
                                sx={{
                                  backgroundColor: '#FEE2E2',
                                  color: '#DC2626',
                                  fontWeight: 700,
                                  fontSize: '0.72rem',
                                }}
                              />
                            </Grid>
                          </Grid>
                        </ListItem>
                        {idx < Math.min(overdueData.length, 5) - 1 && <Divider sx={{ borderColor: '#F1F5F9' }} />}
                      </React.Fragment>
                    ))}
                  </List>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* ─── Charts Row 3: Recent Maintenance & Activity Feed ──────────────── */}
      <Grid container spacing={3}>
        {/* Left: Recent Maintenance Activities */}
        <Grid item xs={12} lg={6}>
          <Card
            elevation={0}
            sx={{
              height: '100%',
              backgroundColor: '#FFFFFF',
              borderRadius: '12px',
              border: '1px solid #E2E8F0',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 700, color: '#0F172A', fontSize: '1.05rem' }}>
                    Recent Maintenance Activities
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#64748B' }}>
                    Latest equipment repair, servicing, and inspection remediation tickets
                  </Typography>
                </Box>

                <Button
                  size="small"
                  endIcon={<ChevronRight size={15} />}
                  onClick={() => navigate('/maintenance')}
                  sx={{ textTransform: 'none', fontWeight: 600, fontSize: '0.8rem', color: '#1E40AF' }}
                >
                  View All
                </Button>
              </Box>

              {maintenanceLoading ? (
                <Box display="flex" alignItems="center" justifyContent="center" height={240}>
                  <CircularProgress size={30} sx={{ color: '#1E40AF' }} />
                </Box>
              ) : !recentMaintenanceData || recentMaintenanceData.length === 0 ? (
                <Box
                  display="flex"
                  flexDirection="column"
                  alignItems="center"
                  justifyContent="center"
                  height={240}
                  sx={{ backgroundColor: '#F8FAFC', borderRadius: '8px', p: 3 }}
                >
                  <Wrench size={36} color="#94A3B8" style={{ marginBottom: 8 }} />
                  <Typography variant="body2" sx={{ fontWeight: 600, color: '#475569' }}>
                    No maintenance tickets found
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    No tickets opened during the selected period.
                  </Typography>
                </Box>
              ) : (
                <List dense disablePadding>
                  {recentMaintenanceData.slice(0, 5).map((item, idx) => {
                    const priorityStyle = getPriorityColor(item.priority);
                    const statusStyle = getStatusBadge(item.status);

                    return (
                      <React.Fragment key={item.maintenance_id}>
                        <ListItem
                          sx={{
                            px: 1.5,
                            py: 1.25,
                            borderRadius: '8px',
                            '&:hover': { backgroundColor: '#F8FAFC' },
                          }}
                        >
                          <Box display="flex" alignItems="center" gap={1.5} width="100%">
                            <Chip
                              label={item.priority || 'NORMAL'}
                              size="small"
                              sx={{
                                backgroundColor: priorityStyle.bg,
                                color: priorityStyle.text,
                                fontWeight: 700,
                                fontSize: '0.7rem',
                                minWidth: 68,
                              }}
                            />

                            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                              <Typography
                                variant="body2"
                                sx={{
                                  fontWeight: 600,
                                  color: '#0F172A',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                }}
                              >
                                {item.issue || `Maintenance Ticket #${item.maintenance_id}`}
                              </Typography>
                              <Typography variant="caption" sx={{ color: '#64748B' }}>
                                Asset: <code>{item.asset_id}</code> • Loc: <code>{item.location_id}</code>
                              </Typography>
                            </Box>

                            <Chip
                              label={item.status}
                              size="small"
                              sx={{
                                backgroundColor: statusStyle.bg,
                                color: statusStyle.text,
                                fontWeight: 600,
                                fontSize: '0.72rem',
                              }}
                            />

                            <Typography
                              variant="caption"
                              color="text.secondary"
                              sx={{ whiteSpace: 'nowrap', display: { xs: 'none', sm: 'block' } }}
                            >
                              {timeAgo(item.opened_date || '')}
                            </Typography>
                          </Box>
                        </ListItem>
                        {idx < Math.min(recentMaintenanceData.length, 5) - 1 && (
                          <Divider sx={{ borderColor: '#F1F5F9' }} />
                        )}
                      </React.Fragment>
                    );
                  })}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Right: Audit Trail / Recent Activity Feed */}
        <Grid item xs={12} lg={6}>
          <Card
            elevation={0}
            sx={{
              height: '100%',
              backgroundColor: '#FFFFFF',
              borderRadius: '12px',
              border: '1px solid #E2E8F0',
              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Box mb={2}>
                <Typography variant="h6" sx={{ fontWeight: 700, color: '#0F172A', fontSize: '1.05rem' }}>
                  System Audit Trail & Live Activity
                </Typography>
                <Typography variant="caption" sx={{ color: '#64748B' }}>
                  Latest operator actions, status adjustments, and inventory updates
                </Typography>
              </Box>

              {activityLoading ? (
                <Box display="flex" alignItems="center" justifyContent="center" height={240}>
                  <CircularProgress size={30} sx={{ color: '#1E40AF' }} />
                </Box>
              ) : activities.length === 0 ? (
                <Box
                  display="flex"
                  flexDirection="column"
                  alignItems="center"
                  justifyContent="center"
                  height={240}
                  sx={{ backgroundColor: '#F8FAFC', borderRadius: '8px', p: 3 }}
                >
                  <Clock size={36} color="#94A3B8" style={{ marginBottom: 8 }} />
                  <Typography variant="body2" sx={{ fontWeight: 600, color: '#475569' }}>
                    No recent activity recorded
                  </Typography>
                </Box>
              ) : (
                <List dense disablePadding>
                  {activities.slice(0, 5).map((item, idx) => (
                    <React.Fragment key={item.id}>
                      <ListItem sx={{ px: 1, py: 1.1 }}>
                        <Box display="flex" alignItems="center" gap={1.5} width="100%">
                          <Chip
                            label={item.action}
                            color={getActionColor(item.action)}
                            size="small"
                            sx={{ minWidth: 80, fontWeight: 700, fontSize: '0.7rem' }}
                          />
                          <ListItemText
                            primary={
                              <Typography variant="body2" sx={{ color: '#1E293B' }}>
                                <strong>{item.user}</strong> {item.action.toLowerCase().replace('_', ' ')} on{' '}
                                <strong>{item.table}</strong> <code>{item.record_id}</code>
                              </Typography>
                            }
                          />
                          <Typography variant="caption" color="text.secondary" whiteSpace="nowrap">
                            <Clock size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: 'middle' }} />
                            {timeAgo(item.timestamp)}
                          </Typography>
                        </Box>
                      </ListItem>
                      {idx < Math.min(activities.length, 5) - 1 && <Divider sx={{ borderColor: '#F1F5F9' }} />}
                    </React.Fragment>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
