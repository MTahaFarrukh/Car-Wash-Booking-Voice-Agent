/**
 * Normalize a Baileys message event into a backend-friendly payload.
 * @param {import("@whiskeysockets/baileys").proto.IWebMessageInfo} message
 * @returns {{ message_id: string, sender_id: string, phone_number: string, text: string, timestamp: string | null, message_type: string } | null}
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

  const phoneNumber = jidToPhoneNumber(senderId);
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
    text: text ?? "",
    timestamp,
    message_type: messageType,
  };
}

/**
 * Extract a normalized phone number from a WhatsApp JID.
 * @param {string} jid
 * @returns {string}
 */
export function jidToPhoneNumber(jid) {
  const userPart = jid.split("@")[0]?.split(":")[0] ?? "";
  const digits = userPart.replace(/\D/g, "");
  return digits ? `+${digits}` : "";
}
