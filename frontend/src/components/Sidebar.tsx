import React from 'react';
import { 
  Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, 
  Toolbar, Divider, Box, Typography 
} from '@mui/material';
import { 
  LayoutDashboard, MapPin, Shield, QrCode, 
  ClipboardCheck, Wrench, FileText, Settings, Users
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';

const drawerWidth = 260;

const menuItems = [
  { text: 'Dashboard', icon: <LayoutDashboard />, path: '/' },
  { text: 'Locations', icon: <MapPin />, path: '/locations' },
  { text: 'Assets', icon: <Shield />, path: '/assets' },
  { text: 'QR Codes', icon: <QrCode />, path: '/qrcodes' },
  { text: 'Inspections', icon: <ClipboardCheck />, path: '/inspections' },
  { text: 'Maintenance', icon: <Wrench />, path: '/maintenance' },
  { text: 'Reports', icon: <FileText />, path: '/reports' },
];

const adminItems = [
  { text: 'Users', icon: <Users />, path: '/users' },
  { text: 'Settings', icon: <Settings />, path: '/settings' },
];

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box', backgroundColor: '#1E293B', color: '#fff' },
      }}
    >
      <Toolbar>
        <Typography variant="h6" sx={{ fontWeight: 'bold', color: '#fff' }}>
          FireSafety Pro
        </Typography>
      </Toolbar>
      <Divider sx={{ borderColor: 'rgba(255,255,255,0.1)' }} />
      
      <Box sx={{ overflow: 'auto', mt: 2 }}>
        <List>
          {menuItems.map((item) => (
            <ListItem key={item.text} disablePadding>
              <ListItemButton 
                selected={location.pathname === item.path}
                onClick={() => navigate(item.path)}
                sx={{
                  '&.Mui-selected': {
                    backgroundColor: 'rgba(255,255,255,0.1)',
                    borderLeft: '4px solid #3b82f6'
                  },
                  '&:hover': {
                    backgroundColor: 'rgba(255,255,255,0.05)'
                  }
                }}
              >
                <ListItemIcon sx={{ color: location.pathname === item.path ? '#3b82f6' : '#94a3b8' }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.text} sx={{ color: location.pathname === item.path ? '#fff' : '#cbd5e1' }} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
        <Divider sx={{ borderColor: 'rgba(255,255,255,0.1)', my: 2 }} />
        <List>
          {adminItems.map((item) => (
            <ListItem key={item.text} disablePadding>
              <ListItemButton 
                selected={location.pathname === item.path}
                onClick={() => navigate(item.path)}
                sx={{
                  '&.Mui-selected': {
                    backgroundColor: 'rgba(255,255,255,0.1)',
                    borderLeft: '4px solid #3b82f6'
                  }
                }}
              >
                <ListItemIcon sx={{ color: '#94a3b8' }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.text} sx={{ color: '#cbd5e1' }} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Box>
    </Drawer>
  );
};

export default Sidebar;
