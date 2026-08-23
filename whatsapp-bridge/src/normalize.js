/**
 * Normalize a Baileys message event into a backend-friendly payload.
 * @param {import("@whiskeysockets/baileys").proto.IWebMessageInfo} message
 * @returns {{ message_id: string, sender_id: string, phone_number: string, push_name: string | null, text: string, timestamp: string | null, message_type: string } | null}
 */
export function normalizeIncomingMessage(message) {
  if (!message?.key?.remoteJid || message.key.fromMe) {
    return null;
  }

  const senderId = message.key.remoteJid;
  const messageId = message.key.id;
  if (!messageId) {
    return null;
  }

  const content = message.message;
  if (!content) {
    return null;
  }

  let text = null;
  let messageType = "unknown";

  if (content.conversation) {
    text = content.conversation;
    messageType = "text";
  } else if (content.extendedTextMessage?.text) {
    text = content.extendedTextMessage.text;
    messageType = "text";
  } else if (content.imageMessage) {
    messageType = "image";
  } else if (content.audioMessage) {
    messageType = "audio";
  } else if (content.videoMessage) {
    messageType = "video";
  } else if (content.documentMessage) {
    messageType = "document";
  } else if (content.stickerMessage) {
    messageType = "sticker";
  }

  const phoneNumber = resolvePhoneFromMessage(message);
  const pushName =
    typeof message.pushName === "string" && message.pushName.trim()
      ? message.pushName.trim()
      : null;
  const timestamp =
    typeof message.messageTimestamp === "number"
      ? new Date(Number(message.messageTimestamp) * 1000).toISOString()
      : message.messageTimestamp
        ? new Date(Number(message.messageTimestamp)).toISOString()
        : null;

  return {
    message_id: messageId,
    sender_id: senderId,
    phone_number: phoneNumber,
    push_name: pushName,
    text: text ?? "",
    timestamp,
    message_type: messageType,
  };
}

/**
 * Prefer real @s.whatsapp.net JIDs. Never treat @lid digits as a phone number.
 * @param {import("@whiskeysockets/baileys").proto.IWebMessageInfo} message
 * @returns {string} E.164-ish "+digits", or "" when unresolved
 */
export function resolvePhoneFromMessage(message) {
  const key = message?.key || {};
  const candidates = [
    key.senderPn,
    key.remoteJidAlt,
    key.participantPn,
    key.participantAlt,
    key.participant,
    key.remoteJid,
  ];

  for (const candidate of candidates) {
    if (!candidate || typeof candidate !== "string") {
      continue;
    }
    if (candidate.endsWith("@lid")) {
      continue;
    }
    if (candidate.includes("@s.whatsapp.net") || candidate.includes("@c.us")) {
      const phone = jidToPhoneNumber(candidate);
      if (phone) {
        return phone;
      }
    }
  }

  return "";
}

/**
 * Extract a normalized phone number from a WhatsApp PN JID.
 * @param {string} jid
 * @returns {string}
 */
export function jidToPhoneNumber(jid) {
  if (!jid || typeof jid !== "string") {
    return "";
  }
  if (jid.endsWith("@lid")) {
    return "";
  }
  const userPart = jid.split("@")[0]?.split(":")[0] ?? "";
  const digits = userPart.replace(/\D/g, "");
  // Real mobile numbers are typically 10–15 digits; LID ids are often longer.
  if (digits.length < 10 || digits.length > 15) {
    return "";
  }
  return `+${digits}`;
}
