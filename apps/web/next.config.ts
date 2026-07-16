import type { NextConfig } from "next";

const developmentApiOrigin = process.env.OPSTWIN_DEV_API_ORIGIN;

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async rewrites() {
    return developmentApiOrigin
      ? [{ source: "/api/simulation/:path*", destination: `${developmentApiOrigin}/api/simulation/:path*` }]
      : [];
  },
};

export default nextConfig;
