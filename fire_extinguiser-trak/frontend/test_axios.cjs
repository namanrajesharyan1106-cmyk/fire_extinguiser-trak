const axios = require('axios');

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
});

console.log(api.getUri({ url: '/maintenance' }));
console.log(api.getUri({ url: 'maintenance' }));
