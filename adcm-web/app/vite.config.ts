import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';
import createSvgSpritePlugin from 'vite-plugin-svg-spriter';
import svgr from 'vite-plugin-svgr';

// https://vitejs.dev/config/
export default defineConfig(() => {
  return {
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
        '/ws': {
          target: 'ws://localhost:8000',
          changeOrigin: false,
          ws: true,
        },
      },
      cors: true,
    },
    envPrefix: 'ADCM_',
    plugins: [
      tsconfigPaths(),
      createSvgSpritePlugin({
        svgFolder: './src/components/uikit/Icon/icons',
      }),
      svgr({
        exclude: [/virtual:/, /node_modules/],
      }),
      react(),
    ],
  };
});
