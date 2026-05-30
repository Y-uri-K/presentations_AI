import type { NextConfig } from "next";

const nextConfig: NextConfig = {};

// В Docker на Windows (WATCHPACK_POLLING=true) — webpack + polling надёжнее Turbopack
if (process.env.WATCHPACK_POLLING === "true") {
  nextConfig.webpack = (config, { dev }) => {
    if (dev) {
      config.watchOptions = {
        poll: Number(process.env.CHOKIDAR_INTERVAL) || 1000,
        aggregateTimeout: 300,
      };
    }
    return config;
  };
}

export default nextConfig;
