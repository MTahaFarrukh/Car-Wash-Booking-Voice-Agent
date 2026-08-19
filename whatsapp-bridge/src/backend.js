import { config } from "./config.js";

/**
 * Forward a normalized WhatsApp message to FastAPI and return the reply payload.
 * @param {ReturnType<import("./normalize.js").normalizeIncomingMessage>} payload
 * @returns {Promise<{ success: boolean, message: string, recipient: string }>}
 */
export async function forwardMessageToBackend(payload) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), config.backendTimeoutMs);

  try {
    const response = await fetch(`${config.backendUrl}/api/whatsapp/messages`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-WhatsApp-Bridge-Secret": config.bridgeSecret,
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    const body = await response.json().catch(() => ({}));

    if (!response.ok) {
      const detail = body.detail || body.message || response.statusText;
      throw new Error(`Backend responded with ${response.status}: ${detail}`);
    }

    return body;
  } finally {
    clearTimeout(timeout);
  }
}
