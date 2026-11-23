import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Box,
  Avatar,
  InputBase,
  Badge,
  Tooltip,
} from '@mui/material';
import { Search, Bell, LogOut, Menu as MenuIcon } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/axios';
import { Menu, MenuItem, ListItemText, CircularProgress, Divider, Popover, List, ListItem, Typography as MuiTypography, Button, Select } from '@mui/material';
import { useSidebar } from '../context/SidebarContext';
import { useAuth } from '../context/AuthContext';

const Header: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isMobile, desktopCollapsed, toggleSidebar } = useSidebar();
  const { user, logout, plants, selectedPlant, setSelectedPlant } = useAuth();
  const sidebarWidth = isMobile ? 0 : desktopCollapsed ? 72 : 260;
  
  const [searchQuery, setSearchQuery] = React.useState('');
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  
  const [notifAnchorEl, setNotifAnchorEl] = React.useState<null | HTMLElement>(null);

  const { data: searchResults, isFetching } = useQuery({
    queryKey: ['globalSearch', searchQuery],
    queryFn: async () => {
      if (searchQuery.length < 2) return [];
      const res = await api.get('/search/', { params: { q: searchQuery } });
      return res.data?.data || [];
    },
    enabled: searchQuery.length >= 2,
  });

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setAnchorEl(e.currentTarget);
  };

  const handleCloseSearch = () => {
    setAnchorEl(null);
  };

  const { data: notifData } = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => {
      const res = await api.get('/notifications/');
      return res.data?.data || [];
    },
    refetchInterval: 30000,
  });

  const { data: unreadCountData } = useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: async () => {
      const res = await api.get('/notifications/unread-count');
      return res.data?.unread_count || 0;
    },
    refetchInterval: 30000,
  });

  const markAsRead = useMutation({
    mutationFn: async (id: number) => {
      await api.put(`/notifications/${id}/read`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  const markAllRead = useMutation({
    mutationFn: async () => {
      await api.put('/notifications/mark-all-read');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <AppBar
      position="fixed"
      sx={{
        width: isMobile ? '100%' : `calc(100% - ${sidebarWidth}px)`,
        ml: isMobile ? 0 : `${sidebarWidth}px`,
        transition: (theme) =>
          theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
        backgroundColor: '#ffffff',
        color: '#172B4D',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
        borderBottom: '1px solid #E2E8F0',
      }}
    >
      <Toolbar sx={{ px: { xs: 2, sm: 3 }, minHeight: '64px !important' }}>
        <Tooltip title={isMobile ? 'Open navigation' : desktopCollapsed ? 'Expand sidebar' : 'Collapse sidebar'} arrow>
          <IconButton
            color="inherit"
            aria-label="Toggle navigation"
            onClick={toggleSidebar}
            edge="start"
            sx={{
              mr: 2,
              color: '#334155',
              p: 1,
              borderRadius: '8px',
              '&:hover': { backgroundColor: '#F1F5F9' },
            }}
          >
            <MenuIcon size={22} />
          </IconButton>
        </Tooltip>

        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            backgroundColor: '#F4F5F7',
            borderRadius: 1,
            px: 2,
            py: 0.5,
            flexGrow: 1,
            maxWidth: 400,
            ml: 2,
          }}
        >
          <Search size={20} color="#5E6C84" />

          <InputBase
            placeholder="Search assets, locations, tickets..."
            sx={{ ml: 1, flex: 1 }}
            value={searchQuery}
            onChange={handleSearchChange}
          />
        </Box>

        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl) && searchQuery.length >= 2}
          onClose={handleCloseSearch}
          PaperProps={{ style: { maxHeight: 400, width: 400 } }}
          autoFocus={false}
          disableAutoFocusItem
        >
          {isFetching ? (
            <MenuItem disabled>
              <CircularProgress size={20} sx={{ mr: 2 }} /> Searching...
            </MenuItem>
          ) : searchResults && searchResults.length > 0 ? (
            searchResults.map((result: any, index: number) => (
              <MenuItem
                key={`${result.type}-${result.id}-${index}`}
                onClick={() => {
                  navigate(result.url);
                  handleCloseSearch();
                  setSearchQuery('');
                }}
              >
                <ListItemText
                  primary={result.title}
                  secondary={`${result.type.toUpperCase()} - ${result.subtitle}`}
                />
              </MenuItem>
            ))
          ) : (
            <MenuItem disabled>No results found</MenuItem>
          )}
        </Menu>

        <Box sx={{ flexGrow: 1 }} />

        {/* Plant Switcher: shows user's assigned plants or all for Admin */}
        {(user?.role === 'ADMIN' || (plants && plants.length > 0)) && (
          <Box sx={{ minWidth: 160, mr: 2 }}>
            <Select
              size="small"
              value={selectedPlant || ''}
              onChange={(e) => setSelectedPlant(e.target.value ? String(e.target.value) : null)}
              displayEmpty
              sx={{
                fontSize: '0.85rem',
                bgcolor: '#F8FAFC',
                borderRadius: '8px',
                height: 36,
                '& .MuiSelect-select': { py: 0.5, px: 1.5 },
              }}
            >
              <MenuItem value="">
                <em>{user?.role === 'ADMIN' ? 'All Plants' : 'Select Plant'}</em>
              </MenuItem>
              {plants && plants.map((p) => (
                <MenuItem key={p} value={p}>
                  {p}
                </MenuItem>
              ))}
            </Select>
          </Box>
        )}

        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 2,
          }}
        >
          <IconButton onClick={(e) => setNotifAnchorEl(e.currentTarget)}>
            <Badge badgeContent={unreadCountData || 0} color="error">
              <Bell size={20} />
            </Badge>
          </IconButton>

          <Popover
            open={Boolean(notifAnchorEl)}
            anchorEl={notifAnchorEl}
            onClose={() => setNotifAnchorEl(null)}
            anchorOrigin={{
              vertical: 'bottom',
              horizontal: 'right',
            }}
            transformOrigin={{
              vertical: 'top',
              horizontal: 'right',
            }}
            PaperProps={{ sx: { width: 320, maxHeight: 400 } }}
          >
            <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <MuiTypography variant="subtitle1" fontWeight={600}>Notifications</MuiTypography>
              {unreadCountData > 0 && (
                <Button size="small" onClick={() => markAllRead.mutate()}>Mark all read</Button>
              )}
            </Box>
            <Divider />
            <List sx={{ p: 0 }}>
              {notifData?.length > 0 ? (
                notifData.map((n: any) => (
                  <ListItem
                    key={n.id}
                    sx={{
                      bgcolor: n.is_read ? 'transparent' : '#e3f2fd',
                      borderBottom: '1px solid #f0f0f0',
                      cursor: 'pointer'
                    }}
                    onClick={() => {
                      if (!n.is_read) markAsRead.mutate(n.id);
                      setNotifAnchorEl(null);
                    }}
                  >
                    <ListItemText
                      primary={n.title}
                      secondary={n.message}
                      primaryTypographyProps={{ variant: 'body2', fontWeight: n.is_read ? 400 : 600 }}
                      secondaryTypographyProps={{ variant: 'caption' }}
                    />
                  </ListItem>
                ))
              ) : (
                <ListItem>
                  <ListItemText secondary="No notifications" />
                </ListItem>
              )}
            </List>
          </Popover>

          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
            }}
          >
            <Avatar
              sx={{
                width: 32,
                height: 32,
                bgcolor: '#0052cc',
              }}
            >
              {user?.name?.charAt?.(0) || 'U'}
            </Avatar>

            <Typography
              variant="body2"
              sx={{ fontWeight: 500 }}
            >
              {user?.name || 'User'}
            </Typography>
          </Box>

          <IconButton
            onClick={handleLogout}
            color="error"
            title="Logout"
          >
            <LogOut size={20} />
          </IconButton>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Header;