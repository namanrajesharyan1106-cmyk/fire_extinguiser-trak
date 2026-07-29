import React from 'react';
import { Box, Typography, Card, Grid, TextField, FormControlLabel, Switch, Button, CircularProgress } from '@mui/material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/axios';
import { toast } from 'react-toastify';
import { useForm, Controller } from 'react-hook-form';

const Settings: React.FC = () => {
  const queryClient = useQueryClient();
  const { control, handleSubmit, setValue } = useForm({
    defaultValues: {
      location_prefix: 'LOC',
      asset_prefix: 'AST',
      plant_wise_numbering: false,
      reset_yearly: false
    }
  });

  const { isLoading } = useQuery({
    queryKey: ['system_config'],
    queryFn: async () => {
      const res = await api.get('/admin/config');
      const data = res.data;
      data.forEach((item: any) => {
        if (item.key === 'location_prefix') setValue('location_prefix', item.value);
        if (item.key === 'asset_prefix') setValue('asset_prefix', item.value);
        if (item.key === 'plant_wise_numbering') setValue('plant_wise_numbering', item.value === 'true');
        if (item.key === 'reset_yearly') setValue('reset_yearly', item.value === 'true');
      });
      return data;
    }
  });

  const saveMutation = useMutation({
    mutationFn: async (data: any) => {
      const updates = [
        api.put(`/admin/config/location_prefix`, { value: data.location_prefix }),
        api.put(`/admin/config/asset_prefix`, { value: data.asset_prefix }),
        api.put(`/admin/config/plant_wise_numbering`, { value: data.plant_wise_numbering ? 'true' : 'false' }),
        api.put(`/admin/config/reset_yearly`, { value: data.reset_yearly ? 'true' : 'false' }),
      ];
      await Promise.all(updates);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system_config'] });
      toast.success('Settings saved successfully');
    },
    onError: () => {
      toast.error('Failed to save settings');
    }
  });

  const onSubmit = (data: any) => {
    saveMutation.mutate(data);
  };

  if (isLoading) return <CircularProgress />;

  return (
    <Box>
      <Typography variant="h4" fontWeight="bold" mb={3}>System Settings</Typography>

      <Card sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" fontWeight="bold" mb={2}>Numbering Configuration</Typography>
        <Typography variant="body2" color="textSecondary" mb={3}>
          Configure how the system automatically generates IDs for Locations, Assets, etc.
        </Typography>

        <form onSubmit={handleSubmit(onSubmit)}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Controller
                name="location_prefix"
                control={control}
                render={({ field }) => (
                  <TextField {...field} label="Location ID Prefix" fullWidth variant="outlined" />
                )}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Controller
                name="asset_prefix"
                control={control}
                render={({ field }) => (
                  <TextField {...field} label="Asset ID Prefix" fullWidth variant="outlined" />
                )}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Controller
                name="plant_wise_numbering"
                control={control}
                render={({ field }) => (
                  <FormControlLabel
                    control={<Switch checked={field.value} onChange={field.onChange} />}
                    label="Enable Plant-wise Numbering (e.g. PP02-LOC-0001)"
                  />
                )}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Controller
                name="reset_yearly"
                control={control}
                render={({ field }) => (
                  <FormControlLabel
                    control={<Switch checked={field.value} onChange={field.onChange} />}
                    label="Reset Numbering Yearly (e.g. LOC-23-0001)"
                  />
                )}
              />
            </Grid>
            <Grid item xs={12}>
              <Button type="submit" variant="contained" disabled={saveMutation.isPending}>
                {saveMutation.isPending ? 'Saving...' : 'Save Configuration'}
              </Button>
            </Grid>
          </Grid>
        </form>
      </Card>
    </Box>
  );
};

export default Settings;
