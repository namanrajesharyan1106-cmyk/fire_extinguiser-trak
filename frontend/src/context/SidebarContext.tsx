import React, { createContext, useContext, useState, useEffect } from 'react';
import { useTheme, useMediaQuery } from '@mui/material';

interface SidebarContextType {
  isMobile: boolean;
  mobileOpen: boolean;
  desktopCollapsed: boolean;
  toggleSidebar: () => void;
  closeSidebar: () => void;
  setDesktopCollapsed: (collapsed: boolean) => void;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

export const SidebarProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [mobileOpen, setMobileOpen] = useState(false);
  const [desktopCollapsed, setDesktopCollapsedState] = useState<boolean>(() => {
    try {
      return localStorage.getItem('firesafety_sidebar_collapsed') === 'true';
    } catch {
      return false;
    }
  });

  const setDesktopCollapsed = (collapsed: boolean) => {
    setDesktopCollapsedState(collapsed);
    try {
      localStorage.setItem('firesafety_sidebar_collapsed', String(collapsed));
    } catch {
      // ignore
    }
  };

  const toggleSidebar = () => {
    if (isMobile) {
      setMobileOpen((prev) => !prev);
    } else {
      setDesktopCollapsed(!desktopCollapsed);
    }
  };

  const closeSidebar = () => {
    if (isMobile) {
      setMobileOpen(false);
    }
  };

  // Close mobile drawer on resize to desktop
  useEffect(() => {
    if (!isMobile) {
      setMobileOpen(false);
    }
  }, [isMobile]);

  return (
    <SidebarContext.Provider
      value={{
        isMobile,
        mobileOpen,
        desktopCollapsed,
        toggleSidebar,
        closeSidebar,
        setDesktopCollapsed,
      }}
    >
      {children}
    </SidebarContext.Provider>
  );
};

export const useSidebar = (): SidebarContextType => {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error('useSidebar must be used within a SidebarProvider');
  }
  return context;
};
