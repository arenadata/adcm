import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';
import createSvgSpritePlugin from 'vite-plugin-svg-spriter';
import eslintPlugin from 'vite-plugin-eslint';
import svgr from 'vite-plugin-svgr';
//import VitePluginReactRemoveAttributes from 'vite-plugin-react-remove-attributes';

// https://vitejs.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = { ...process.env, ...loadEnv(mode, process.cwd(), '') };
  const withQaAttributes = env.WITH_QA_ATTRIBUTES === 'true';

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
      eslintPlugin({
        exclude: [/virtual:/, /node_modules/],
      }),
      //...(withQaAttributes ? [] : [VitePluginReactRemoveAttributes.default({ attributes: ['data-test'] })]),
    ],
  };
});
