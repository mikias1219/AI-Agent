import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // On Vercel, frontend/vercel.json proxies /api → Render.
    // Locally, proxy to the Python dashboard.
    if (process.env.VERCEL) {
      return [];
    }
    const backend = process.env.PERSONAL_AGENT_BACKEND_URL || "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
