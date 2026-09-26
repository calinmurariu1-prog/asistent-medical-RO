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
    : {
        async rewrites() {
          const backend = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
          return [{ source: "/api/:path*", destination: `${backend.replace(/\/$/, "")}/api/:path*` }];
        },
      }),
};

export default nextConfig;
