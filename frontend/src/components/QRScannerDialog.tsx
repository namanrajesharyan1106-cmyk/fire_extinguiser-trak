import React, { useEffect, useRef, useState } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Box, Typography, CircularProgress } from '@mui/material';
import { Html5Qrcode } from 'html5-qrcode';

interface QRScannerDialogProps {
  open: boolean;
  onClose: () => void;
  onScan: (decodedText: string) => void;
}

const QRScannerDialog: React.FC<QRScannerDialogProps> = ({ open, onClose, onScan }) => {
  const [scannerError, setScannerError] = useState('');
  const [isInitializing, setIsInitializing] = useState(false);
  const scannerContainerRef = useRef<HTMLDivElement>(null);
  const lastScanTimeRef = useRef<number>(0);
  const onScanRef = useRef(onScan);

  useEffect(() => {
    onScanRef.current = onScan;
  }, [onScan]);

  useEffect(() => {
    if (!open) return;

    let html5QrCode: Html5Qrcode | null = null;
    let isMounted = true;
    lastScanTimeRef.current = 0; // reset on open

    const initScanner = async () => {
      // Ensure the scanner container is actually in the DOM and has layout dimensions
      if (!scannerContainerRef.current || scannerContainerRef.current.offsetWidth === 0) {
        if (isMounted) setTimeout(initScanner, 100);
        return;
      }

      try {
        setIsInitializing(true);
        setScannerError('');

        // Ensure ID is present on the ref for Html5Qrcode to attach to
        if (!scannerContainerRef.current.id) {
            scannerContainerRef.current.id = `qr-reader-${Math.random().toString(36).substr(2, 9)}`;
        }
        
        html5QrCode = new Html5Qrcode(scannerContainerRef.current.id);
        
        await html5QrCode.start(
          { facingMode: "environment" },
          { fps: 10, qrbox: { width: 250, height: 250 } },
          async (decodedText) => {
            const now = Date.now();
            if (now - lastScanTimeRef.current < 2000) return; // Ignore repeated scans within 2 seconds
            lastScanTimeRef.current = now;

            // Immediately stop camera
            if (html5QrCode && html5QrCode.isScanning) {
              try {
                await html5QrCode.stop();
                html5QrCode.clear();
              } catch (e) {
                console.error("Error stopping scanner", e);
              }
            }
            onScanRef.current(decodedText);
          },
          () => {
            // ignore scan failures
          }
        );
      } catch (err: any) {
        let msg = "Scanner could not be initialized.";
        const errStr = String(err).toLowerCase();
        
        if (errStr.includes("permission") || errStr.includes("not allowed")) {
          msg = "Camera permission denied.";
        } else if (errStr.includes("not found") || errStr.includes("no camera") || errStr.includes("requested device")) {
          msg = "No camera detected.";
        } else if (errStr.includes("not supported")) {
          msg = "This browser does not support QR scanning.";
        }
        
        if (isMounted) setScannerError(msg);
      } finally {
        if (isMounted) setIsInitializing(false);
      }
    };

    initScanner();

    return () => {
      isMounted = false;
      if (html5QrCode) {
        if (html5QrCode.isScanning) {
          html5QrCode.stop().then(() => html5QrCode?.clear()).catch(console.error);
        } else {
          html5QrCode.clear();
        }
      }
    };
  }, [open]);

  return (
    <Dialog 
      open={open} 
      onClose={() => { if (!isInitializing) onClose(); }} 
      maxWidth="xs" 
      fullWidth
      onKeyDown={(e) => {
        if (e.key === 'Escape' && !isInitializing) {
          onClose();
        }
      }}
    >
      <DialogTitle>Scan Asset QR Code</DialogTitle>
      <DialogContent dividers>
        {isInitializing && (
          <Box display="flex" flexDirection="column" alignItems="center" py={4} sx={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', zIndex: 10 }}>
            <CircularProgress size={32} />
            <Typography mt={2} color="text.secondary">Loading Camera...</Typography>
          </Box>
        )}
        
        {scannerError && !isInitializing ? (
          <Box textAlign="center" py={3}>
            <Typography color="error">{scannerError}</Typography>
          </Box>
        ) : (
          <Box 
            ref={scannerContainerRef} 
            sx={{ 
              width: '100%', 
              minHeight: '320px', 
              overflow: 'hidden',
              position: 'relative',
              opacity: isInitializing ? 0.3 : 1,
              transition: 'opacity 0.3s'
            }}
          ></Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={isInitializing}>Cancel</Button>
      </DialogActions>
    </Dialog>
  );
};

export default QRScannerDialog;
