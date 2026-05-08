import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow development access from EC2 public IP/domain to prevent
  // blocked dev-origin requests (HMR/client behaviors over remote host).
  allowedDevOrigins: [
    "localhost",
    "127.0.0.1",
    "54.198.229.54",
  ],
};

export default nextConfig;
