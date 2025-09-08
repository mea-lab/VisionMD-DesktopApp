import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    include: [
      '@emotion/react', 
      '@emotion/styled', 
      '@mui/material/Tooltip',
      '@mui/material/Unstable_Grid2'
    ],
  },
  resolve: {
    alias: {
    '@': path.resolve(__dirname, 'src'),
    },
  },
});
