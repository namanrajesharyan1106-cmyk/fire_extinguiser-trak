import axios from 'axios';

// Where the API lives:
// - VITE_API_URL (if set) always wins, e.g. for production.
// - Page opened over https (npm run dev:https) -> "/api" (Vite proxies it to the
//   backend, so the browser never makes an insecure http call).
// - Page opened over plain http -> same host, port 8000 (unchanged behaviour):
//     PC (localhost)       -> http://localhost:8000/api
//     Phone (192.168.x.x)  -> http://192.168.x.x:8000/api
const API_URL =
  import.meta.env.VITE_API_URL ||
  (window.location.protocol === 'https:'
    ? '/api'
    : `${window.location.protocol}//${window.location.hostname}:8000/api`);

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
