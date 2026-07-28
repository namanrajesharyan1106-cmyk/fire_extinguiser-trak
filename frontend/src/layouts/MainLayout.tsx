import React from 'react';
import { Box } from '@mui/material';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Header from '../components/Header';

const MainLayout: React.FC = () => {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Header />
      <Sidebar />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          backgroundColor: '#F4F5F7',
          marginTop: '64px', // height of AppBar
          width: `calc(100% - 260px)`
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
};

export default MainLayout;
