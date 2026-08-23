import makeWASocket, {
  DisconnectReason,
  fetchLatestBaileysVersion,
  useMultiFileAuthState,
} from "@whiskeysockets/baileys";
import qrcode from "qrcode-terminal";
import pino from "pino";

import { config } from "./config.js";
import { forwardMessageToBackend } from "./backend.js";
import { jidToPhoneNumber, normalizeIncomingMessage } from "./normalize.js";

const logger = pino({ level: config.logLevel });

/**
 * Best-effort LID → phone JID lookup from Baileys session mapping.
 * @param {Awaited<ReturnType<typeof makeWASocket>>} sock
 * @param {string} lidJid
 * @returns {Promise<string>}
 */
async function resolveLidPhone(sock, lidJid) {
  try {
    const mapping = sock?.signalRepository?.lidMapping;
    if (!mapping?.getPNForLID) {
      return "";
    }
    const pnJid = await mapping.getPNForLID(lidJid);
    return jidToPhoneNumber(pnJid || "");
  } catch (err) {
    logger.debug({ err, lidJid }, "LID phone lookup failed");
    return "";
  }
}

/**
 * Start the Baileys WhatsApp connection and wire message handling.
 * @returns {Promise<void>}
 */
export async function startWhatsAppBridge() {
  if (!config.bridgeSecret) {
    logger.warn("WHATSAPP_BRIDGE_SECRET is empty — backend requests may be rejected");
  }

  const { state, saveCreds } = await useMultiFileAuthState(config.sessionPath);
  const { version } = await fetchLatestBaileysVersion();

  const connect = async () => {
    const sock = makeWASocket({
      version,
      auth: state,
      logger: pino({ level: "silent" }),
      printQRInTerminal: false,
      syncFullHistory: false,
      markOnlineOnConnect: false,
    });

    sock.ev.on("creds.update", saveCreds);

    sock.ev.on("connection.update", (update) => {
      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        logger.info("Scan this QR code with WhatsApp to pair the business account:");
        qrcode.generate(qr, { small: true });
      }

      if (connection === "open") {
        logger.info("WhatsApp connection established");
      }

      if (connection === "close") {
        const statusCode = lastDisconnect?.error?.output?.statusCode;
        const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
        logger.warn({ statusCode }, "WhatsApp connection closed");

        if (shouldReconnect) {
          logger.info("Reconnecting to WhatsApp...");
          connect().catch((err) => logger.error({ err }, "Reconnect failed"));
        } else {
          logger.error("Logged out — delete auth_info and scan QR again to re-pair");
        }
      }
    });

    sock.ev.on("messages.upsert", async ({ messages, type }) => {
      if (type !== "notify") {
        return;
      }

      for (const message of messages) {
        const normalized = normalizeIncomingMessage(message);
        if (!normalized) {
          continue;
        }

        if (!normalized.phone_number && normalized.sender_id.endsWith("@lid")) {
          normalized.phone_number = await resolveLidPhone(sock, normalized.sender_id);
        }

        logger.info(
          {
            messageId: normalized.message_id,
            sender: normalized.sender_id,
            phone: normalized.phone_number || null,
            pushName: normalized.push_name || null,
          },
          "Incoming WhatsApp message"
        );

        try {
          const reply = await forwardMessageToBackend(normalized);
          const text = reply?.message;
          if (!text) {
            logger.warn({ messageId: normalized.message_id }, "Backend returned empty message");
            continue;
          }

          await sock.sendMessage(normalized.sender_id, { text });
          logger.info({ messageId: normalized.message_id }, "Reply sent");
        } catch (err) {
          logger.error({ err, messageId: normalized.message_id }, "Failed to process message");
          try {
            await sock.sendMessage(normalized.sender_id, {
              text: "Sorry, I'm having trouble reaching our booking system right now. Please try again in a moment.",
            });
          } catch (sendErr) {
            logger.error({ err: sendErr }, "Failed to send fallback reply");
          }
        }
      }
    });

    return sock;
  };

  await connect();
}
