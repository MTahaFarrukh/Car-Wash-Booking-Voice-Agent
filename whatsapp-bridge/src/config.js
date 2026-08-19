import dotenv from "dotenv";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.resolve(__dirname, "..", ".env") });

export const config = {
  backendUrl: process.env.BACKEND_URL || "http://127.0.0.1:8000",
  bridgeSecret: process.env.WHATSAPP_BRIDGE_SECRET || "",
  sessionPath: process.env.WHATSAPP_SESSION_PATH || path.resolve(__dirname, "..", "auth_info"),
  logLevel: process.env.LOG_LEVEL || "info",
  backendTimeoutMs: Number(process.env.BACKEND_TIMEOUT_MS || 30000),
};
