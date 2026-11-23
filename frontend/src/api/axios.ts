import axios from 'axios';

// The backend is called on the same host the page was opened from, port 8000.
// PC (localhost)        -> http://localhost:8000/api
// Phone (192.168.x.x)   -> http://192.168.x.x:8000/api
// VITE_API_URL (if set) always wins, e.g. for production.
const API_URL =
  import.meta.env.VITE_API_URL ||
  `${window.location.protocol}//${window.location.hostname}:8000/api`;

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // A 401 on the login request itself must NOT trigger a page reload,
    // otherwise the "wrong password" message disappears.
    const isLoginRequest = error.config?.url?.includes('/auth/login');
    if (error.response && error.response.status === 401 && !isLoginRequest) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
