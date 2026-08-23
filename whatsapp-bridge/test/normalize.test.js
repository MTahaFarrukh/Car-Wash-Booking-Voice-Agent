import assert from "node:assert/strict";
import test from "node:test";

import {
  jidToPhoneNumber,
  normalizeIncomingMessage,
  resolvePhoneFromMessage,
} from "../src/normalize.js";

test("jidToPhoneNumber extracts digits with leading plus", () => {
  assert.equal(jidToPhoneNumber("923001234567@s.whatsapp.net"), "+923001234567");
  assert.equal(jidToPhoneNumber("923001234567:12@s.whatsapp.net"), "+923001234567");
});

test("jidToPhoneNumber ignores LID JIDs", () => {
  assert.equal(jidToPhoneNumber("179834693148857@lid"), "");
});

test("resolvePhoneFromMessage prefers senderPn over LID remoteJid", () => {
  const phone = resolvePhoneFromMessage({
    key: {
      remoteJid: "179834693148857@lid",
      fromMe: false,
      id: "X1",
      senderPn: "923318307970@s.whatsapp.net",
    },
  });
  assert.equal(phone, "+923318307970");
});

test("resolvePhoneFromMessage uses remoteJidAlt", () => {
  const phone = resolvePhoneFromMessage({
    key: {
      remoteJid: "179834693148857@lid",
      remoteJidAlt: "923001112233@s.whatsapp.net",
      fromMe: false,
      id: "X2",
    },
  });
  assert.equal(phone, "+923001112233");
});

test("resolvePhoneFromMessage does not invent phone from LID digits", () => {
  const phone = resolvePhoneFromMessage({
    key: {
      remoteJid: "179834693148857@lid",
      fromMe: false,
      id: "X3",
    },
  });
  assert.equal(phone, "");
});

test("normalizeIncomingMessage maps text conversation messages", () => {
  const payload = normalizeIncomingMessage({
    key: {
      remoteJid: "923001234567@s.whatsapp.net",
      fromMe: false,
      id: "ABC123",
    },
    pushName: "Taha",
    message: {
      conversation: "Hi there",
    },
    messageTimestamp: 1_700_000_000,
  });

  assert.ok(payload);
  assert.equal(payload.message_id, "ABC123");
  assert.equal(payload.sender_id, "923001234567@s.whatsapp.net");
  assert.equal(payload.phone_number, "+923001234567");
  assert.equal(payload.push_name, "Taha");
  assert.equal(payload.text, "Hi there");
  assert.equal(payload.message_type, "text");
  assert.equal(payload.timestamp, new Date(1_700_000_000 * 1000).toISOString());
});

test("normalizeIncomingMessage ignores outbound messages", () => {
  const payload = normalizeIncomingMessage({
    key: { remoteJid: "923001234567@s.whatsapp.net", fromMe: true, id: "OUT1" },
    message: { conversation: "ignored" },
  });
  assert.equal(payload, null);
});

test("normalizeIncomingMessage classifies unsupported media", () => {
  const payload = normalizeIncomingMessage({
    key: { remoteJid: "923001234567@s.whatsapp.net", fromMe: false, id: "IMG1" },
    message: { imageMessage: { mimetype: "image/jpeg" } },
  });

  assert.ok(payload);
  assert.equal(payload.message_type, "image");
  assert.equal(payload.text, "");
});
