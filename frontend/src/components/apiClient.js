import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 5000000,
  headers: {
    'Content-Type': 'multipart/form-data',
    'Accept': 'multipart/form-data'
  }
});

// Request interceptor
apiClient.interceptors.request.use(config => {
  console.log('Making request to:', config.url);
  return config;
});

// Response interceptor
apiClient.interceptors.response.use(
  response => {
    console.log('Response from:', response.config.url);
    return response;
  },
  error => {
    console.error('API Error:', error.message);
    if (error.response) {
      console.error('Status:', error.response.status);
      console.error('Data:', error.response.data);
    }
    return Promise.reject(error);
  }
);

export default apiClient;
