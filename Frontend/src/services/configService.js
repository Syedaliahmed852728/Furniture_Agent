// Automatic domain detection
const getApiBaseUrl = () => {
  const { hostname } = window.location;
  
  if (hostname === 'ai.iconnectgroup.com' || hostname.endsWith('.iconnectgroup.com')) {
    return 'https://apiai.iconnectgroup.com';  // ← FORCE HTTPS
  }
  
  return '/api';
};

export const BASE_URL = getApiBaseUrl();
export const IS_PRODUCTION = BASE_URL.includes('iconnectgroup.com');

// Debug output
if (!IS_PRODUCTION) {
  console.log(`[DEV] Frontend: ${window.location.origin}`);
  console.log(`[DEV] Backend: ${BASE_URL}`);
}