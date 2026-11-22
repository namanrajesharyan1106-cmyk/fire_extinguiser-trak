import React from 'react';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Divider,
  Box,
  Typography,
  Tooltip,
} from '@mui/material';
import {
  LayoutDashboard,
  MapPin,
  Shield,
  QrCode,
  ClipboardCheck,
  Wrench,
  FileText,
  Settings,
  Users,
  Database,
  Flame,
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useSidebar } from '../context/SidebarContext';
import { useAuth } from '../context/AuthContext';

const EXPANDED_WIDTH = 260;
const COLLAPSED_WIDTH = 72;

const menuItems = [
  { text: 'Dashboard', icon: <LayoutDashboard size={20} />, path: '/', permission: 'view_dashboard' },
  { text: 'Locations', icon: <MapPin size={20} />, path: '/locations', permission: 'view_locations' },
  { text: 'Assets', icon: <Shield size={20} />, path: '/assets', permission: 'view_assets' },
  { text: 'QR Codes', icon: <QrCode size={20} />, path: '/qrcodes', permission: 'view_locations' },
  { text: 'Inspections', icon: <ClipboardCheck size={20} />, path: '/inspections', permission: 'view_inspections' },
  { text: 'Maintenance', icon: <Wrench size={20} />, path: '/maintenance', permission: 'view_maintenance' },
  { text: 'Reports', icon: <FileText size={20} />, path: '/reports', permission: 'view_reports' },
];

const adminItems = [
  { text: 'Master Data', icon: <Database size={20} />, path: '/master-data', permission: 'manage_system_config' },
  { text: 'Users', icon: <Users size={20} />, path: '/users', permission: 'view_users' },
  { text: 'Settings', icon: <Settings size={20} />, path: '/settings', permission: 'manage_system_config' },
];

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isMobile, mobileOpen, closeSidebar, desktopCollapsed } = useSidebar();
  const { hasPermission } = useAuth();

  const visibleMenuItems = menuItems.filter((item) => hasPermission(item.permission));
  const visibleAdminItems = adminItems.filter((item) => hasPermission(item.permission));

  const currentWidth = isMobile ? EXPANDED_WIDTH : desktopCollapsed ? COLLAPSED_WIDTH : EXPANDED_WIDTH;
  const isCollapsed = !isMobile && desktopCollapsed;

  const handleNavClick = (path: string) => {
    navigate(path);
    if (isMobile) {
      closeSidebar();
    }
  };

  const renderNavList = (items: typeof menuItems, sectionTitle?: string) => (
    <>
      {sectionTitle && !isCollapsed && (
        <Typography
          variant="caption"
          sx={{
            px: 3,
            py: 1,
            display: 'block',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: '#64748B',
            fontSize: '0.7rem',
          }}
        >
          {sectionTitle}
        </Typography>
      )}
      <List sx={{ px: isCollapsed ? 1 : 1.5, py: 0.5 }}>
        {items.map((item) => {
          const isSelected = location.pathname === item.path;

          const buttonContent = (
            <ListItemButton
              selected={isSelected}
              onClick={() => handleNavClick(item.path)}
              sx={{
                minHeight: 46,
                borderRadius: '8px',
                mb: 0.5,
                justifyContent: isCollapsed ? 'center' : 'initial',
                px: isCollapsed ? 1.5 : 2,
                transition: 'all 0.2s ease',
                '&.Mui-selected': {
                  backgroundColor: 'rgba(59, 130, 246, 0.15)',
                  borderLeft: isCollapsed ? 'none' : '4px solid #3b82f6',
                  '&:hover': {
                    backgroundColor: 'rgba(59, 130, 246, 0.22)',
                  },
                },
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.06)',
                },
              }}
            >
              <ListItemIcon
                sx={{
                  minWidth: 0,
                  mr: isCollapsed ? 0 : 2,
                  justifyContent: 'center',
                  color: isSelected ? '#38BDF8' : '#94A3B8',
                  transition: 'color 0.2s ease',
                }}
              >
                {item.icon}
              </ListItemIcon>
              {!isCollapsed && (
                <ListItemText
                  primary={item.text}
                  primaryTypographyProps={{
                    fontSize: '0.88rem',
                    fontWeight: isSelected ? 600 : 500,
                    color: isSelected ? '#FFFFFF' : '#CBD5E1',
                  }}
                />
              )}
            </ListItemButton>
          );

          return (
            <ListItem key={item.text} disablePadding sx={{ display: 'block' }}>
              {isCollapsed ? (
                <Tooltip title={item.text} placement="right" arrow>
                  {buttonContent}
                </Tooltip>
              ) : (
                buttonContent
              )}
            </ListItem>
          );
        })}
      </List>
    </>
  );

  const sidebarContent = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Sidebar Header / Brand */}
      <Toolbar
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: isCollapsed ? 'center' : 'flex-start',
          px: isCollapsed ? 1 : 2.5,
          minHeight: '64px !important',
          backgroundColor: '#0F172A',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 36,
            height: 36,
            borderRadius: '8px',
            backgroundColor: '#DC2626',
            color: '#FFFFFF',
            flexShrink: 0,
            boxShadow: '0 2px 8px rgba(220, 38, 38, 0.4)',
          }}
        >
          <Flame size={22} />
        </Box>
        {!isCollapsed && (
          <Box sx={{ ml: 1.5, overflow: 'hidden' }}>
            <Typography
              variant="h6"
              sx={{
                fontWeight: 700,
                color: '#FFFFFF',
                fontSize: '1.05rem',
                letterSpacing: '-0.02em',
                lineHeight: 1.2,
                whiteSpace: 'nowrap',
              }}
            >
              FireSafety <span style={{ color: '#38BDF8', fontWeight: 600 }}>Pro</span>
            </Typography>
            <Typography
              variant="caption"
              sx={{
                color: '#64748B',
                fontSize: '0.68rem',
                display: 'block',
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
                fontWeight: 600,
              }}
            >
              Asset Management
            </Typography>
          </Box>
        )}
      </Toolbar>

      {/* Navigation items */}
      <Box sx={{ flexGrow: 1, overflowY: 'auto', overflowX: 'hidden', py: 1.5 }}>
        {renderNavList(visibleMenuItems)}

        {visibleAdminItems.length > 0 && (
          <>
            <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.08)', my: 1.5, mx: 2 }} />
            {renderNavList(visibleAdminItems, 'Administration')}
          </>
        )}
      </Box>

      {/* Footer / Version */}
      {!isCollapsed && (
        <Box
          sx={{
            p: 2,
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            backgroundColor: '#0F172A',
          }}
        >
          <Typography variant="caption" sx={{ color: '#64748B', display: 'block', textAlign: 'center', fontSize: '0.72rem' }}>
            Enterprise Safety v2.0
          </Typography>
        </Box>
      )}
    </Box>
  );

  if (isMobile) {
    return (
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={closeSidebar}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': {
            width: EXPANDED_WIDTH,
            boxSizing: 'border-box',
            backgroundColor: '#1E293B',
            color: '#FFFFFF',
            borderRight: '1px solid rgba(255,255,255,0.08)',
          },
        }}
      >
        {sidebarContent}
      </Drawer>
    );
  }

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: currentWidth,
        flexShrink: 0,
        whiteSpace: 'nowrap',
        transition: (theme) =>
          theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
        '& .MuiDrawer-paper': {
          width: currentWidth,
          boxSizing: 'border-box',
          backgroundColor: '#1E293B',
          color: '#FFFFFF',
          borderRight: '1px solid rgba(255, 255, 255, 0.08)',
          overflowX: 'hidden',
          transition: (theme) =>
            theme.transitions.create('width', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
        },
      }}
    >
      {sidebarContent}
    </Drawer>
  );
};

export default Sidebar;
