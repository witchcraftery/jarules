import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// https://vitejs.dev/config/
export default defineConfig({
  base: './', // Ensure correct asset paths for Electron build
  plugins: [vue()],
});
