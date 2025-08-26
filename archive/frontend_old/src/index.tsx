import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// Check for required environment variables
if (!process.env.REACT_APP_API_URL) {
  console.warn('REACT_APP_API_URL is not set. Using default: http://localhost:8000');
}

if (!process.env.REACT_APP_WS_URL) {
  console.warn('REACT_APP_WS_URL is not set. Using default: ws://localhost:8000');
}

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Register service worker for PWA support (optional)
if ('serviceWorker' in navigator && process.env.NODE_ENV === 'production') {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/service-worker.js')
      .then((registration) => {
        console.log('SW registered: ', registration);
      })
      .catch((registrationError) => {
        console.log('SW registration failed: ', registrationError);
      });
  });
}

// Performance monitoring disabled for compatibility
// Web vitals can be added back later if needed