import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // "/" for Vercel/Netlify/local; the GitHub Pages workflow sets VITE_BASE=/crux-lab/.
  base: process.env.VITE_BASE || "/",
});
