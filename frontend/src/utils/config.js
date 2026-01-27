// Application configuration from environment variables

export const config = {
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  cognito: {
    userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || '',
    clientId: import.meta.env.VITE_COGNITO_CLIENT_ID || '',
    domain: import.meta.env.VITE_COGNITO_DOMAIN || '',
    region: import.meta.env.VITE_AWS_REGION || 'us-east-1',
  },
  maxFileSize: 100 * 1024 * 1024, // 100MB
  allowedFileTypes: [
    'image/jpeg',
    'image/png',
    'image/webp',
    'video/mp4',
    'video/webm',
    'audio/mp3',
    'audio/wav',
  ],
};

export default config;
