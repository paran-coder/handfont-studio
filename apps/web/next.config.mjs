/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: { optimizePackageImports: ['@vercel/blob'] },
};
export default nextConfig;
