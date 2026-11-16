import React from 'react';
import { Box } from '@mui/material';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Header from '../components/Header';
import { SidebarProvider, useSidebar } from '../context/SidebarContext';

const LayoutContent: React.FC = () => {
  const { isMobile, desktopCollapsed } = useSidebar();
  const sidebarWidth = isMobile ? 0 : desktopCollapsed ? 72 : 260;

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', backgroundColor: '#F5F7FA' }}>
      <Header />
      <Sidebar />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: { xs: 2, sm: 3, md: 3.5 },
          backgroundColor: '#F5F7FA',
          marginTop: '64px',
          width: isMobile ? '100%' : `calc(100% - ${sidebarWidth}px)`,
          ml: isMobile ? 0 : `${sidebarWidth}px`,
          transition: (theme) =>
            theme.transitions.create(['width', 'margin'], {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
          overflowX: 'hidden',
          minWidth: 0,
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
};

const MainLayout: React.FC = () => {
  return (
    <SidebarProvider>
      <LayoutContent />
    </SidebarProvider>
  );
};

export default MainLayout;
