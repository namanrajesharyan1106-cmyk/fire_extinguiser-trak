import React from 'react';
import {
  Box, Typography, Grid, Card, CardContent, CircularProgress,
  Divider, List, ListItem, ListItemText, Chip, Skeleton,
} from '@mui/material';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';
import {
  ShieldAlert, CheckCircle, Wrench, AlertTriangle,
  MapPin, Clock, TrendingUp,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import api from '../api/axios';

// ─── Types ───────────────────────────────────────────────────────────────────
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

// ─── Stat Card Component ──────────────────────────────────────────────────────
interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  bgColor: string;
  subtitle?: string;
  loading?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, bgColor, subtitle, loading }) => (
  <Card sx={{ height: '100%' }}>
    <CardContent sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', py: 2.5 }}>
      <Box>
        <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600, mb: 0.5 }}>
          {title}
        </Typography>
        {loading ? (
          <Skeleton width={80} height={44} />
        ) : (
          <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#172B4D' }}>
            {value}
          </Typography>
        )}
        {subtitle && (
          <Typography variant="caption" color="text.secondary">{subtitle}</Typography>
        )}
      </Box>
      <Box sx={{ p: 1.5, borderRadius: 2, backgroundColor: bgColor }}>
        {icon}
      </Box>
    </CardContent>
  </Card>
);

// ─── Action badge helper ──────────────────────────────────────────────────────
const getActionColor = (action: string): 'default' | 'primary' | 'success' | 'warning' | 'error' => {
  if (action === 'CREATE') return 'success';
  if (action === 'UPDATE' || action === 'ASSIGN') return 'primary';
  if (action === 'DELETE' || action === 'UNLINK') return 'error';
  if (action === 'STATUS_CHANGE') return 'warning';
  return 'default';
};

const timeAgo = (timestamp: string) => {
  const diff = Date.now() - new Date(timestamp).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
};

const PIE_COLORS = ['#0052cc', '#36B37E', '#FFAB00', '#FF5630', '#6554C0'];

// ─── Dashboard Component ──────────────────────────────────────────────────────
const Dashboard: React.FC = () => {
  const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const res = await api.get('/dashboard/stats');
      return res.data?.data || res.data;
    },
    refetchInterval: 60_000, // Refresh every minute
  });

  const { data: trend, isLoading: trendLoading } = useQuery<MonthlyTrend[]>({
    queryKey: ['dashboard-trend'],
    queryFn: async () => {
      const res = await api.get('/dashboard/monthly-trend', { params: { months: 7 } });
      return Array.isArray(res.data?.data) ? res.data.data : [];
    },
  });

  const { data: activityData } = useQuery<{ activity: ActivityItem[] }>({
    queryKey: ['dashboard-activity'],
    queryFn: async () => {
      const res = await api.get('/dashboard/recent-activity', { params: { limit: 10 } });
      return res.data?.data || res.data;
    },
    refetchInterval: 30_000,
  });

  const { data: assetTypeData } = useQuery<{ asset_type: string; count: number }[]>({
    queryKey: ['dashboard-asset-types'],
    queryFn: async () => {
      const res = await api.get('/dashboard/asset-type-distribution');
      return Array.isArray(res.data?.data) ? res.data.data : [];
    },
  });

  const activities = activityData?.activity ?? [];

  const statCards = [
    {
      title: 'Total Assets',
      value: stats?.total_assets ?? 0,
      icon: <CheckCircle color="#36B37E" size={28} />,
      bgColor: '#e3fcef',
      subtitle: `${stats?.installed_assets ?? 0} installed`,
    },
    {
      title: 'Inspections Due',
      value: stats?.inspection_due_today ?? 0,
      icon: <AlertTriangle color="#FFAB00" size={28} />,
      bgColor: '#fff0b3',
      subtitle: `${stats?.overdue_inspections ?? 0} overdue`,
    },
    {
      title: 'Open Maintenance',
      value: stats?.open_maintenance ?? 0,
      icon: <Wrench color="#FF5630" size={28} />,
      bgColor: '#ffebe6',
      subtitle: 'Open tickets',
    },
    {
      title: 'Expired Assets',
      value: stats?.expired_assets ?? 0,
      icon: <ShieldAlert color="#FF5630" size={28} />,
      bgColor: '#ffebe6',
      subtitle: `${stats?.refill_due ?? 0} refill due`,
    },
    {
      title: 'Total Locations',
      value: stats?.total_locations ?? 0,
      icon: <MapPin color="#0052cc" size={28} />,
      bgColor: '#deebff',
      subtitle: `${Math.round(stats?.compliance_percent ?? 0)}% compliance`,
    },
    {
      title: 'Compliance',
      value: `${Math.round(stats?.compliance_percent ?? 0)}%`,
      icon: <TrendingUp color="#6554C0" size={28} />,
      bgColor: '#EAE6FF',
      subtitle: `${stats?.installed_assets ?? 0} / ${stats?.total_locations ?? 0} locations`,
    },
  ];

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
          Dashboard Overview
        </Typography>
        {statsLoading && <CircularProgress size={24} />}
      </Box>

      {/* KPI Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {statCards.map((stat, idx) => (
          <Grid item xs={12} sm={6} md={4} lg={2} key={idx}>
            <StatCard {...stat} loading={statsLoading} />
          </Grid>
        ))}
      </Grid>

      {/* Charts Row */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Bar Chart — Monthly Trend */}
        <Grid item xs={12} md={8}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 3, fontWeight: 'bold' }}>
                Inspection vs Maintenance Trends (7 months)
              </Typography>
              <Box sx={{ height: 300 }}>
                {trendLoading ? (
                  <Box display="flex" alignItems="center" justifyContent="center" height="100%">
                    <CircularProgress />
                  </Box>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={trend ?? []}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                      <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 12 }} />
                      <YAxis axisLine={false} tickLine={false} />
                      <Tooltip cursor={{ fill: '#F4F5F7' }} />
                      <Legend />
                      <Bar dataKey="inspections" fill="#0052cc" radius={[4, 4, 0, 0]} name="Inspections" />
                      <Bar dataKey="maintenance" fill="#FFAB00" radius={[4, 4, 0, 0]} name="Maintenance" />
                      <Bar dataKey="passed" fill="#36B37E" radius={[4, 4, 0, 0]} name="Passed" />
                      <Bar dataKey="failed" fill="#FF5630" radius={[4, 4, 0, 0]} name="Failed" />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Pie Chart — Asset Type Distribution */}
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>
                Asset Type Distribution
              </Typography>
              {!assetTypeData || assetTypeData.length === 0 ? (
                <Box display="flex" alignItems="center" justifyContent="center" height={260}>
                  <Typography color="text.secondary">No asset data</Typography>
                </Box>
              ) : (
                <Box sx={{ height: 280 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={assetTypeData}
                        dataKey="count"
                        nameKey="asset_type"
                        cx="50%"
                        cy="45%"
                        outerRadius={80}
                        label={({ asset_type, percent }) =>
                          `${asset_type} ${(percent * 100).toFixed(0)}%`
                        }
                        labelLine={false}
                      >
                        {assetTypeData.map((_, idx) => (
                          <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(val, name) => [val, name]} />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Activity Feed */}
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>
                Recent Activity
              </Typography>
              {activities.length === 0 ? (
                <Typography color="text.secondary" sx={{ py: 2 }}>No recent activity.</Typography>
              ) : (
                <List dense disablePadding>
                  {activities.map((item, idx) => (
                    <React.Fragment key={item.id}>
                      <ListItem sx={{ px: 0, py: 1 }}>
                        <Box display="flex" alignItems="center" gap={2} width="100%">
                          <Chip
                            label={item.action}
                            color={getActionColor(item.action)}
                            size="small"
                            sx={{ minWidth: 90, fontWeight: 600 }}
                          />
                          <ListItemText
                            primary={
                              <Typography variant="body2">
                                <strong>{item.user}</strong> {item.action.toLowerCase().replace('_', ' ')} on{' '}
                                <strong>{item.table}</strong> record <code>{item.record_id}</code>
                              </Typography>
                            }
                          />
                          <Typography variant="caption" color="text.secondary" whiteSpace="nowrap">
                            <Clock size={12} style={{ display: 'inline', marginRight: 4 }} />
                            {timeAgo(item.timestamp)}
                          </Typography>
                        </Box>
                      </ListItem>
                      {idx < activities.length - 1 && <Divider />}
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
