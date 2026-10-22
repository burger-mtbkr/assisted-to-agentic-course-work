import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// `npm run dev` serves the UI with hot reload and forwards the API to a running agent-hub.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8765' } },
  // One bundle served from localhost; splitting it would not make the app load faster.
  build: { chunkSizeWarningLimit: 1000 },
});
