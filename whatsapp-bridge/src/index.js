import { startWhatsAppBridge } from "./whatsapp.js";

startWhatsAppBridge().catch((err) => {
  console.error("WhatsApp bridge failed to start:", err);
  process.exit(1);
});
