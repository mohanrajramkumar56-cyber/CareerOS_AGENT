/** @type {import('next').NextConfig} */
const nextConfig = {
  // Produces a self-contained build in .next/standalone
  // Required for the production Docker image (no node_modules needed at runtime)
  output: "standalone",
};

export default nextConfig;
