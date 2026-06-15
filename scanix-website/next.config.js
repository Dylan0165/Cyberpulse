const createNextIntlPlugin = require("next-intl/plugin");

const withNextIntl = createNextIntlPlugin("./src/lib/i18n.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Self-contained server bundle for a small production Docker image.
  output: "standalone",
};

module.exports = withNextIntl(nextConfig);
