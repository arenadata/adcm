import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';
import createSvgSpritePlugin from 'vite-plugin-svg-spriter';
import svgr from 'vite-plugin-svgr';

// const STRICT_CSP = `default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; connect-src 'self'`;

// https://vitejs.dev/config/
export default defineConfig(() => {
  return {
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: false,
        },
        '/ws': {
          target: 'ws://localhost:8000',
          changeOrigin: false,
          ws: true,
        },
      },
      cors: true,
    },
    // for testing CSP headers
    // preview: {
    //   port: 4173,
    //   headers: {
    //     'Content-Security-Policy': STRICT_CSP,
    //   },
    // },
    // build: {
    //   sourcemap: true,
    // },
    envPrefix: 'ADCM_',
    css: {
      preprocessorOptions: {
        scss: {
          // Vite 5 defaults to Sass legacy JS API; sass@1.79+ warns on every file.
          api: 'modern',
        },
      },
    },
    plugins: [
      tsconfigPaths(),
      createSvgSpritePlugin({
        svgFolder: './src/components/uikit/Icon/icons',
      }),
      // CSP: replace inline style on SVG sprite wrapper with class (style in svg-sprite.scss)
      {
        name: 'svg-sprite-csp-no-inline-style',
        transformIndexHtml(html) {
          return html.replace(
            /<svg([^>]*)\s+style=["']position:\s*absolute["']([^>]*)>/,
            '<svg$1 class="svg-sprite-container" aria-hidden="true"$2>',
          );
        },
      },
      svgr({
        exclude: [/virtual:/, /node_modules/],
      }),
      react(),
    ],
  };
});
