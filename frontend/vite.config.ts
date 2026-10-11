/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      // "prompt": al haber deploy nuevo se avisa con un botón "Actualizar" (`UpdatePrompt`) en vez de
      // recargar solo (podía tirar un formulario a medio llenar) o quedarse con la versión vieja.
      registerType: "prompt",
      // El SW/offline solo importan para el operador (`01-architecture §4`); el shell
      // básico se cachea para toda la app, las features de sync offline llegan en Fase 2.
      includeAssets: ["favicon.svg"],
      manifest: {
        name: "Elogistics Facturación",
        short_name: "Elogistics",
        description: "Captura de viajes y facturación CFDI para Elogistics",
        theme_color: "#E0353B",
        background_color: "#ffffff",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "/icons/pwa-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/pwa-512.png", sizes: "512x512", type: "image/png" },
          {
            src: "/icons/maskable-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,png,ico}"],
        cleanupOutdatedCaches: true,
      },
      devOptions: {
        enabled: false,
      },
    }),
  ],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
