import axios from 'axios';

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({ baseURL: BASE });

export const uploadFiles = (formData: FormData) =>
  api.post('/api/v1/upload', formData);

export const getBatch = (id: number) =>
  api.get(`/api/v1/batch/${id}`);

export const getBatchReport = (id: number) =>
  api.get(`/api/v1/batch/${id}/report`);

export const getBatchDisputes = (id: number) =>
  api.get(`/api/v1/batch/${id}/disputes`);

export const getDisputeLetter = (id: number) =>
  api.get(`/api/v1/batch/${id}/dispute-letter`, { responseType: 'text' });

export const downloadCSV = (id: number, type: string) =>
  api.get(`/api/v1/batch/${id}/download/${type}`, { responseType: 'blob' });

export const updateDispute = (discId: number, payload: { dispute_status: string; dispute_notes?: string }) =>
  api.patch(`/api/v1/discrepancy/${discId}/dispute`, payload);

export const bulkRaiseDisputes = (batchId: number) =>
  api.patch(`/api/v1/batch/${batchId}/disputes/bulk`);

export const deleteBatch = (id: number) =>
  api.delete(`/api/v1/batch/${id}`);

export const listBatches = () =>
  api.get('/api/v1/batches');

export const getAnalytics = () =>
  api.get('/api/v1/analytics');

export const getAlerts = () =>
  api.get('/api/v1/alerts');

export const getAlertCount = () =>
  api.get('/api/v1/alerts/count');

export const markAlertRead = (id: number) =>
  api.patch(`/api/v1/alerts/${id}/read`);

export const markAllAlertsRead = () =>
  api.patch('/api/v1/alerts/read-all');

export const getContracts = () =>
  api.get('/api/v1/contracts');

export const deleteContract = (id: number) =>
  api.delete(`/api/v1/contracts/${id}`);

export const formatINR = (amount: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 2 }).format(amount);
