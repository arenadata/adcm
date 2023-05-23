import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';
import createSvgSpritePlugin from 'vite-plugin-svg-sprite';
import eslintPlugin from 'vite-plugin-eslint';

// https://vitejs.dev/config/
export default defineConfig({
  envPrefix: 'ADCM_',
  plugins: [
    tsconfigPaths(),
    createSvgSpritePlugin({
      include: '**/icons/*.svg',
      symbolId: 'icon-[name]',
    }),
    react(),
    eslintPlugin({
      exclude: [/virtual:/, /node_modules/],
    }),
  ],
});
