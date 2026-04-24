import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactCompiler: true,
  turbopack: {
    // Explicitly set workspace root to web/ so Turbopack doesn't pick up
    // the parent package-lock.json and use the repo root for resolution.
    root: ".",
  },
  webpack: (config, { dir }) => {
    // Ensure webpack resolves node_modules from the web/ directory even
    // when a package.json exists at the repository root.
    config.resolve.modules = [
      path.resolve(dir, "node_modules"),
      "node_modules",
    ];
    return config;
  },
};

export default nextConfig;
