import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Face recognition runs a heavy AI model on first call — allow up to 2 min
  serverExternalPackages: [],
  experimental: {
    // Allow route handlers to run for up to 120 seconds
  },
};

export default nextConfig;
