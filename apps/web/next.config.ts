import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  agentRules: false,
  typedRoutes: true,
  output: "standalone",
  outputFileTracingRoot: resolve(dirname(fileURLToPath(import.meta.url)), "../.."),
};

export default config;
