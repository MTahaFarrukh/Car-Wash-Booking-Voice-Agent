import { useMemo, useState } from "react";
import { UpliftAIRoom, DisconnectButton } from "@upliftai/assistants-react";

const DEFAULT_API_URL = "http://localhost:8000";

function extractToolArgs(payload) {
  const argumentsData = payload?.arguments || {};
  return (
    argumentsData.raw_arguments ||
    argumentsData.parsed_arguments ||
    argumentsData ||
    {}
  );
}

function buildSaveBookingTool(apiUrl) {
  return {
    name: "save_booking",
    description:
      "Save a confirmed car wash booking. Only call after the customer confirms all details.",
    parameters: {
      type: "object",
      properties: {
        name: { type: "string", description: "Customer full name" },
        vehicle: { type: "string", description: "Vehicle type or model" },
        date: { type: "string", description: "Preferred booking date" },
        time: { type: "string", description: "Preferred booking time" },
        phone: { type: "string", description: "Customer phone number" },
      },
      required: ["name", "vehicle", "date", "time", "phone"],
    },
    timeout: 10,
    handler: async (data) => {
      try {
        const payload = JSON.parse(data.payload);
        const args = extractToolArgs(payload);

        console.log("[save_booking] args:", args);

        const response = await fetch(`${apiUrl.replace(/\/$/, "")}/booking`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: args.name || "",
            vehicle: args.vehicle || "",
            date: args.date || "",
            time: args.time || "",
            phone: args.phone || "",
          }),
        });

        if (!response.ok) {
          const message = await response.text();
          console.error("[save_booking] backend error:", response.status, message);
          return JSON.stringify({
            error: `Backend returned ${response.status}`,
            presentationInstructions:
              "Sorry, the booking could not be saved because the server is not reachable. Please make sure python app.py is running.",
          });
        }

        const result = await response.json();
        console.log("[save_booking] saved:", result);

        return JSON.stringify({
          result,
          presentationInstructions:
            "Your booking is confirmed. We look forward to seeing you at Sparkle Car Wash.",
        });
      } catch (error) {
        console.error("[save_booking] failed:", error);
        return JSON.stringify({
          error: String(error),
          presentationInstructions:
            "Sorry, the booking could not be saved due to a system error. Please make sure python app.py is running on port 8000.",
        });
      }
    },
  };
}

export default function App() {
  const [assistantId, setAssistantId] = useState("");
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [sessionData, setSessionData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const tools = useMemo(() => [buildSaveBookingTool(apiUrl)], [apiUrl]);

  async function connect() {
    if (!assistantId.trim()) {
      setError("Please enter your Uplift Assistant ID.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `https://api.upliftai.org/v1/realtime-assistants/${assistantId}/createPublicSession`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ participantName: "Car Wash Customer" }),
        }
      );

      if (!response.ok) {
        throw new Error(
          `Could not create session. Is the assistant public? HTTP ${response.status}`
        );
      }

      setSessionData(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (!sessionData) {
    return (
      <div style={styles.page}>
        <h1 style={styles.title}>Sparkle Car Wash Voice Agent</h1>
        <p>Use this page to test Uplift voice bookings with save_booking.</p>

        <label style={styles.label}>Uplift Assistant ID</label>
        <input
          style={styles.input}
          value={assistantId}
          onChange={(e) => setAssistantId(e.target.value)}
          placeholder="Paste assistant ID"
        />

        <label style={styles.label}>Backend API URL</label>
        <input
          style={styles.input}
          value={apiUrl}
          onChange={(e) => setApiUrl(e.target.value)}
        />

        <button style={styles.button} onClick={connect} disabled={loading}>
          {loading ? "Connecting..." : "Start Voice Call"}
        </button>

        {error ? <p style={styles.error}>{error}</p> : null}

        <div style={styles.note}>
          <strong>Before testing:</strong>
          <ol>
            <li>Run <code>python app.py</code> in the project folder.</li>
            <li>Assistant must be <strong>Public</strong> on Uplift.</li>
            <li>Allow microphone access in the browser.</li>
            <li>After confirming, check <code>bookings.csv</code>.</li>
          </ol>
        </div>
      </div>
    );
  }

  return (
    <UpliftAIRoom
      token={sessionData.token}
      serverUrl={sessionData.wsUrl}
      connect={true}
      audio={true}
      video={false}
      tools={tools}
    >
      <div style={styles.page}>
        <h1 style={styles.title}>Connected</h1>
        <p>Speak to complete a booking. Confirm when asked.</p>
        <p>
          Watch Terminal 1 for: <code>[Uplift/booking] saved:</code>
        </p>
        <DisconnectButton>End Call</DisconnectButton>
      </div>
    </UpliftAIRoom>
  );
}

const styles = {
  page: {
    fontFamily: "Arial, sans-serif",
    maxWidth: 720,
    margin: "40px auto",
    padding: "0 20px",
  },
  title: { color: "#1a5f2a" },
  label: { display: "block", marginTop: 12, fontWeight: "bold" },
  input: {
    width: "100%",
    padding: 8,
    marginTop: 4,
    boxSizing: "border-box",
  },
  button: {
    marginTop: 16,
    padding: "10px 20px",
    background: "#1a5f2a",
    color: "white",
    border: "none",
    cursor: "pointer",
  },
  error: { color: "#b91c1c" },
  note: {
    background: "#f0f7f1",
    padding: 12,
    borderRadius: 6,
    marginTop: 20,
    fontSize: 14,
  },
};
