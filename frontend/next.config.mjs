/** @type {import('next').NextConfig} */

// When building the mobile app (Capacitor), Next produces a fully static export
// in `out/` that gets bundled into the native shell. The web deploy (Render)
// keeps the default server build — do NOT set `output: 'export'` there.
const isMobile = process.env.MOBILE_BUILD === "1";

const nextConfig = {
  reactStrictMode: true,
  ...(isMobile
    ? {
        output: "export",
        images: { unoptimized: true },
      }
    : {}),
};

export default nextConfig;
