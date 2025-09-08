// electron.vite.config.js
import { defineConfig } from 'electron-vite';
import react from '@vitejs/plugin-react';
import { join } from 'path';

export default defineConfig({
  main: {
    entry: 'src/main/index.js'
  },

  preload: {
    entry: 'src/preload/index.js'
  },

  renderer: {
    root: join(__dirname, 'src/renderer'),
    plugins: [react()],
    resolve: {
      alias: {
        '@': join(__dirname, 'src/renderer/src')
      }
    },
  }
});
