import { useStore } from "@/store";
import { useAuthStore } from "@/store/auth";
import { logger } from "@/lib/logger";
import { parseResponse } from "@/lib/responseParser";
import { signedFetch } from "@/lib/sigv4";
import { pollSessionState } from "@/lib/statePoller";

// Resolve API URL: build-time env var > runtime config > undefined
let API_URL: string | undefined = import.meta.env.VITE_API_URL as string | undefined;

async function loadRuntimeConfig(): Promise<void> {
  if (API_URL) return;
  try {
    const resp = await fetch("/config.json");
    if (resp.ok) {
      const config = await resp.json();
      if (config.VITE_API_URL) {
        API_URL = config.VITE_API_URL;
        logger.info("Streaming", `Loaded runtime config: ${API_URL}`);
      }
    }
  } catch {
    // config.json not found — fine for local dev
  }
}

let configLoaded = false;

/**
 * Initialize the streaming client by loading runtime config.
 * Sets connection status to "connected" since HTTP doesn't need a persistent connection.
 */
export async function connect(): Promise<void> {
  await loadRuntimeConfig();
  configLoaded = true;
  if (!API_URL) {
    logger.error("Streaming", "VITE_API_URL not configured");
    useStore.getState().setConnectionStatus("disconnected");
    return;
  }
  logger.info("Streaming", `API endpoint: ${API_URL}`);
  useStore.getState().setConnectionStatus("connected");
  useStore.getState().resetReconnect();
}

export function disconnect(): void {
  // No persistent connection to close
  useStore.getState().setConnectionStatus("disconnected");
}

/** Active AbortController for the current request */
let activeController: AbortController | null = null;

/**
 * Send a message to the orchestrator via HTTP POST and stream the response.
 * Handles both raw JSON responses and streamed text.
 */
export async function sendMessage(message: string): Promise<void> {
  if (!configLoaded) await connect();
  if (!API_URL) {
    logger.error("Streaming", "Cannot send — API URL not configured");
    useStore.getState().addErrorMessage("API endpoint not configured.");
    return;
  }

  const store = useStore.getState();
  const sessionId = store.session.sessionId;
  const messageId = crypto.randomUUID();

  // Show typing indicator
  store.appendStreamToken(messageId, "", false);

  activeController = new AbortController();

  try {
    // Get AWS credentials for SigV4 signing
    let credentials = useAuthStore.getState().credentials;
    let retried = false;
    if (!credentials) {
      credentials = await useAuthStore.getState().refreshCredentials();
    }

    let resp = await signedFetch(
      API_URL,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          sessionId: sessionId || undefined,
          plant: useStore.getState().planner?.plant || useStore.getState().disruption?.plant || undefined,
          currentPhase: useStore.getState().disruption?.phase || undefined,
        }),
        signal: activeController.signal,
      },
      credentials
    );

    // Capture session ID from header
    const respSessionId = resp.headers.get("X-Session-Id");
    if (respSessionId && !sessionId) {
      store.setSessionId(respSessionId);
    }

    if (!resp.ok) {
      // Retry once on 502/503 (transient AgentCore errors)
      if ((resp.status === 502 || resp.status === 503 || resp.status === 403) && !retried) {
        logger.info("Streaming", `HTTP ${resp.status} — retrying in 3s...`);
        store.appendStreamToken(messageId, "", false); // keep typing indicator
        await new Promise((r) => setTimeout(r, 3000));
        retried = true;

        credentials = await useAuthStore.getState().refreshCredentials();
        resp = await signedFetch(
          API_URL,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              message,
              sessionId: store.session.sessionId || sessionId || undefined,
              plant: useStore.getState().planner?.plant || useStore.getState().disruption?.plant || undefined,
              currentPhase: useStore.getState().disruption?.phase || undefined,
            }),
            signal: activeController!.signal,
          },
          credentials
        );

        if (!resp.ok) {
          const errText = await resp.text();
          logger.error("Streaming", `Retry failed: HTTP ${resp.status}: ${errText}`);
          store.appendStreamToken(messageId, `Error: ${resp.status} (retry failed)`, true);
          return;
        }
      } else {
        const errText = await resp.text();
        logger.error("Streaming", `HTTP ${resp.status}: ${errText}`);
        store.appendStreamToken(messageId, `Error: ${resp.status}`, true);
        return;
      }
    }

    if (!resp.body) {
      const text = await resp.text();
      handleCompleteResponse(messageId, text);
      return;
    }

    // Stream the response body
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
    }

    // Flush remaining
    buffer += decoder.decode();

    handleCompleteResponse(messageId, buffer);
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === "AbortError") {
      logger.info("Streaming", "Request aborted");
      store.appendStreamToken(messageId, "\n\n[Cancelled]", true);
    } else {
      logger.error("Streaming", `Request failed: ${err}`);
      store.appendStreamToken(messageId, `Error: ${String(err)}`, true);
    }
  } finally {
    activeController = null;
  }
}

/**
 * Handle a complete response buffer from the streaming proxy.
 * Extracts the `ui` field from the JSON envelope for structured UI data.
 */
function handleCompleteResponse(messageId: string, raw: string): void {
  const store = useStore.getState();
  const trimmed = raw.trim();

  if (!trimmed) {
    store.appendStreamToken(messageId, "No response received.", true);
    return;
  }

  let content = trimmed;
  let uiData: Record<string, unknown> | null = null;

  // Debug: log raw response shape (length only, no content)
  logger.info("Streaming", `Raw response length=${trimmed.length}`);

  try {
    const parsed = JSON.parse(trimmed);

    // Handle Lambda Function URL envelope: {statusCode, headers, body}
    // The streaming proxy returns this wrapper when using awslambda.streamifyResponse
    let envelope = parsed;
    if (parsed.statusCode && parsed.body) {
      try {
        envelope = typeof parsed.body === "string" ? JSON.parse(parsed.body) : parsed.body;
      } catch {
        envelope = parsed;
      }
    }

    // Extract session ID
    if (envelope.session_id || envelope.sessionId) {
      store.setSessionId(envelope.session_id || envelope.sessionId);
    }
    // Extract display text and ui field from the JSON envelope
    content = String(envelope.result || envelope.message || envelope.response || trimmed);
    if (envelope.ui && typeof envelope.ui === "object" && Object.keys(envelope.ui).length > 0) {
      uiData = envelope.ui as Record<string, unknown>;
      logger.info("Streaming", `UI data present in envelope`);
    }
  } catch {
    // Not JSON — display as raw text (no extraction fallback)
    logger.info("Streaming", "Response is not JSON, displaying as text");
  }

  // Show display text in chat
  store.appendStreamToken(messageId, content, true);

  // Attach uiData to the message for component consumption
  if (uiData) {
    const freshState = useStore.getState();
    const currentPhase = freshState.disruption?.phase ?? null;
    const msgs = freshState.chat.messages.map((m) =>
      m.id === messageId ? { ...m, uiData, disruptionPhase: (uiData as Record<string, unknown>).phase as string ?? currentPhase } : m,
    );
    useStore.setState({ chat: { ...freshState.chat, messages: msgs } });
  }

  // Parse response with structured data (legacy path — kept for backward compat)
  parseResponse(content, uiData);

  // Poll DynamoDB for authoritative session state
  pollSessionState().catch(() => {});
}

/**
 * Send an order decision via HTTP POST.
 */
export async function sendDecision(payload: Record<string, unknown>): Promise<void> {
  if (!API_URL) {
    logger.error("Streaming", "Cannot send decision — API URL not configured");
    return;
  }

  const store = useStore.getState();
  const sessionId = store.session.sessionId;
  const messageId = crypto.randomUUID();

  // Format the decision as a message to the orchestrator
  const decision = payload as {
    orderId: string;
    decision: string;
    reason: string | null;
  };
  const message = `Order decision for ${decision.orderId}: ${decision.decision}${decision.reason ? ` — ${decision.reason}` : ""}`;

  store.addUserMessage(crypto.randomUUID(), message);
  store.appendStreamToken(messageId, "", false);

  try {
    // Get AWS credentials for SigV4 signing
    let credentials = useAuthStore.getState().credentials;
    if (!credentials) {
      credentials = await useAuthStore.getState().refreshCredentials();
    }

    const resp = await signedFetch(
      API_URL,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          sessionId: sessionId || undefined,
          plant: useStore.getState().planner?.plant || useStore.getState().disruption?.plant || undefined,
          currentPhase: useStore.getState().disruption?.phase || undefined,
        }),
      },
      credentials
    );

    if (!resp.ok) {
      const errText = await resp.text();
      store.appendStreamToken(messageId, `Error: ${resp.status} ${errText}`, true);
      return;
    }

    const buffer = await resp.text();
    handleCompleteResponse(messageId, buffer);
  } catch (err) {
    store.appendStreamToken(messageId, `Error: ${String(err)}`, true);
  }

  // Clear pending decision
  store.setPendingDecision(null);
}

/**
 * Send a transfer accept/reject decision via HTTP POST.
 */
export async function sendTransferDecision(
  _transferId: string,
  orderId: string,
  decision: "accept" | "reject",
  reason?: string,
): Promise<void> {
  const message = `Transfer decision for ${orderId}: ${decision}${reason ? ` — ${reason}` : ""}`;
  await sendMessage(message);
}

/**
 * Compatibility shim: send() for components that still use the old WebSocket API.
 * Routes to appropriate handler based on message type.
 */
export function send(data: Record<string, unknown>): void {
  if (data.action === "sendMessage" || data.type === "user_message") {
    const message = (data.data as string) || (data.payload as { message?: string })?.message || "";
    if (message) sendMessage(message);
  } else if (data.type === "order_decision") {
    const payload = data.payload as Record<string, unknown>;
    sendDecision(payload);
  } else {
    // Generic: send as message
    const message = (data.data as string) || JSON.stringify(data);
    sendMessage(message);
  }
}
