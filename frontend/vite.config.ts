// frontend/vite.config.ts
import { defineConfig } from "vite";

export default defineConfig({
  // This tells Vite to prepend your GitHub repository name to all asset links
  base: "/chess-multiplayer/",
  server: {
    port: 5173,
    strictPort: true, // fail if port is in use instead of auto-incrementing
    host: true, // Allows testing across local network devices if needed
  },
});
