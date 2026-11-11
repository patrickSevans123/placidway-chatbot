import type { NextConfig } from "next";

// The app is served as a folder of static files from FastAPI at `/`, so every
// asset URL must be root-absolute and every route must end in a slash with its
// own index.html. No server runtime, no route handlers, no middleware.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  reactStrictMode: true,
};

export default nextConfig;
