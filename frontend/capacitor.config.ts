import type { CapacitorConfig } from "@capacitor/cli";

/**
 * Capacitor wraps the static Next.js export (`out/`) into native Android/iOS
 * apps. Build the web assets with `npm run build:mobile`, then sync with
 * `npx cap sync`. Native platforms are added on your machine
 * (`npx cap add android` / `npx cap add ios`) — see docs/MOBILE.md.
 */
const config: CapacitorConfig = {
  appId: "ro.asistentmedical.app",
  appName: "Asistent Medical AI",
  webDir: "out",
  backgroundColor: "#ffffff",
  android: {
    // Serve over https:// scheme so secure-context APIs work in the WebView.
    allowMixedContent: false,
  },
  ios: {
    contentInset: "always",
  },
  server: {
    androidScheme: "https",
    iosScheme: "https",
  },
};

export default config;
