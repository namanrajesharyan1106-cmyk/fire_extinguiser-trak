import React, { useEffect, useState } from 'react';
import api from '../api/axios';
import { Box, CircularProgress } from '@mui/material';

interface AuthImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  src: string;
  fallback?: React.ReactNode;
}

export const AuthImage: React.FC<AuthImageProps> = ({
  src,
  alt = 'Image',
  fallback = null,
  style,
  className,
  ...props
}) => {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<boolean>(false);

  useEffect(() => {
    if (!src) {
      setLoading(false);
      setError(true);
      return;
    }

    // Convert relative upload paths to /files endpoint
    let fetchPath = src;
    if (fetchPath.startsWith('uploads/')) {
      fetchPath = fetchPath.replace('uploads/', '/files/');
    } else if (fetchPath.startsWith('/uploads/')) {
      fetchPath = fetchPath.replace('/uploads/', '/files/');
    }

    let isMounted = true;
    let currentObjectUrl: string | null = null;

    setLoading(true);
    setError(false);

    api
      .get(fetchPath, { responseType: 'blob' })
      .then((response) => {
        if (!isMounted) return;
        currentObjectUrl = URL.createObjectURL(response.data);
        setBlobUrl(currentObjectUrl);
        setLoading(false);
      })
      .catch(() => {
        if (!isMounted) return;
        setError(true);
        setLoading(false);
      });

    return () => {
      isMounted = false;
      if (currentObjectUrl) {
        URL.revokeObjectURL(currentObjectUrl);
      }
    };
  }, [src]);

  if (loading) {
    return (
      <Box display="inline-flex" alignItems="center" justifyContent="center" p={1}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (error || !blobUrl) {
    return <>{fallback}</>;
  }

  return <img src={blobUrl} alt={alt} style={style} className={className} {...props} />;
};

export default AuthImage;
