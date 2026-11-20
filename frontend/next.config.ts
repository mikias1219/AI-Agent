import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      { source: "/automations", destination: "/routines", permanent: true },
      { source: "/automations/:path*", destination: "/routines/:path*", permanent: true },
    ];
  },
  async rewrites() {
    // On Vercel, frontend/vercel.json proxies /api → Render.
    // Locally, proxy to the Python dashboard.
    if (process.env.VERCEL) {
      return [];
    }
    const backend = process.env.PERSONAL_AGENT_BACKEND_URL || "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
  async headers() {
    // S12: browser-facing security headers on the Next.js app.
    const security = [
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "X-Frame-Options", value: "DENY" },
      {
        key: "Permissions-Policy",
        value: "camera=(), microphone=(), geolocation=()",
      },
      {
        key: "Content-Security-Policy",
        value: [
          "default-src 'self'",
          "script-src 'self' 'unsafe-inline'",
          "style-src 'self' 'unsafe-inline'",
          "img-src 'self' data:",
          "font-src 'self' data:",
          "connect-src 'self'",
          "object-src 'none'",
          "base-uri 'self'",
          "frame-ancestors 'none'",
          "form-action 'self'",
        ].join("; "),
      },
    ];
    if (process.env.VERCEL || process.env.NODE_ENV === "production") {
      security.push({
        key: "Strict-Transport-Security",
        value: "max-age=63072000; includeSubDomains; preload",
      });
    }
    return [{ source: "/:path*", headers: security }];
  },
};

export default nextConfig;
