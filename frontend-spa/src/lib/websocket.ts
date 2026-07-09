import { useStore } from "@/store";
import { logger } from "@/lib/logger";
import type { ServerMessage, ServerMessageType } from "@/types";

// Resolve WebSocket URL: build-time env var > runtime config > undefined
let WS_URL: string | undefined = import.meta.env.VITE_WS_URL as string | undefined;

// Support runtime configuration via /config.json (for CloudFront deployments)
async function loadRuntimeConfig(): Promise<void> {
  if (WS_URL) return; // Already configured at build time
  try {
    const resp = await fetch("/config.json");
    if (resp.ok) {
      const config = await resp.json();
      if (config.VITE_WS_URL) {
        WS_URL = config.VITE_WS_URL;
        logger.info("WebSocket", `Loaded runtime config: ${WS_URL}`);
      }
    }
  } catch {
    // config.json not found — that's fine for local dev
  }
}

const MAX_DELAY = 30_000;

let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

function getDelay(attempt: number): number {
  return Math.min(1000 * Math.pow(2, attempt), MAX_DELAY);
}

function dispatch(msg: ServerMessage): void {
  const store = useStore.getState();
  const handlers: Record<ServerMessageType, () => void> = {
    stream_token: () => {
      const p = msg.payload as {
        messageId: string;
        token: string;
        done: boolean;
      };
      store.appendStreamToken(p.messageId, p.token, p.done);
    },
    structured_data: () => {
      const p = msg.payload as {
        messageId: string;
        data: { type: string; title: string; data: Record<string, unknown> };
      };
      store.attachStructuredData(p.messageId, p.data as never);
    },
    order_decision_request: () => {
      store.setPendingDecision(msg.payload as never);
    },
    phase_update: () => {
      store.setPhase((msg.payload as { phase: string }).phase as never);
    },
    capacity_update: () => {
      store.updateCapacity(msg.payload as never);
    },
    agent_switch: () => {
      store.setActiveAgent(
        (msg.payload as { agent: string | null }).agent,
      );
      const agentName = (msg.payload as { agent: string | null }).agent;
      if (agentName) {
        store.updateSubAgent({
          name: agentName,
          status: "running",
          startedAt: new Date().toISOString(),
          completedAt: null,
          summary: null,
        });
      }
    },
    error: () => {
      const text =
        (msg.payload as { message?: string }).message ??
        "Something went wrong. Please try again.";
      store.addErrorMessage(text);
    },
  };
  if (Object.prototype.hasOwnProperty.call(handlers, msg.type)) {
    handlers[msg.type]();
  }
}

function scheduleReconnect(): void {
  const store = useStore.getState();
  store.setConnectionStatus("reconnecting");
  store.incrementReconnect();
  const delay = getDelay(store.connection.reconnectAttempt);
  logger.warn("WebSocket", `Reconnecting in ${delay}ms (attempt ${store.connection.reconnectAttempt})`);
  reconnectTimer = setTimeout(() => connect(), delay);
}

export async function connect(): Promise<void> {
  await loadRuntimeConfig();
  if (!WS_URL) {
    logger.error("WebSocket", "VITE_WS_URL not configured");
    useStore.getState().setConnectionStatus("disconnected");
    return;
  }

  const store = useStore.getState();
  store.setConnectionStatus("connecting");

  try {
    ws = new WebSocket(WS_URL);
  } catch {
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    logger.info("WebSocket", `Connected to ${WS_URL}`);
    const s = useStore.getState();
    s.setConnectionStatus("connected");
    s.resetReconnect();
  };

  ws.onclose = () => {
    logger.warn("WebSocket", "Disconnected");
    ws = null;
    scheduleReconnect();
  };

  ws.onerror = () => {
    logger.error("WebSocket", "Connection error");
    ws?.close();
  };

  ws.onmessage = (event: MessageEvent) => {
    try {
      const raw = JSON.parse(event.data as string);

      // Normalize backend messages into ServerMessage format.
      // The Lambda may send either:
      //   a) {type: "stream_token", payload: {...}}  (new streaming format)
      //   b) {type: "agent_response", data: "..."}   (legacy single-response)
      //   c) {type: "error", data: "..."}             (legacy error)
      let msg: ServerMessage;

      if (raw.type === "agent_response") {
        // Legacy: convert to a single done stream_token
        msg = {
          type: "stream_token",
          sessionId: raw.sessionId ?? "",
          payload: {
            messageId: crypto.randomUUID(),
            token: raw.data ?? "",
            done: true,
          },
        };
      } else if (raw.type === "error" && typeof raw.data === "string") {
        // Legacy error format
        msg = {
          type: "error",
          sessionId: raw.sessionId ?? "",
          payload: { message: raw.data },
        };
      } else if (raw.payload) {
        // Already in ServerMessage format
        msg = raw as ServerMessage;
      } else {
        logger.warn("WebSocket", `Unknown message format: ${raw.type}`);
        return;
      }

      dispatch(msg);
    } catch {
      logger.error("WebSocket", "Failed to parse message");
    }
  };
}

export function send(data: Record<string, unknown>): void {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data));
  } else {
    logger.warn("WebSocket", "Cannot send — not connected");
  }
}

export function disconnect(): void {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  ws?.close();
  ws = null;
}
