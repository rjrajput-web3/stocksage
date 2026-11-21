/** @type {import('next').NextConfig} */
const nextConfig = {
  // Fully static export: the page renders entirely from data baked in at
  // build time (src/data/dashboard.json), so it works on any static host
  // and never depends on the live API at view time.
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
