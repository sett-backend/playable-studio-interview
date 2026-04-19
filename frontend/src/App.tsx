import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { PlayablePreview } from "./PlayablePreview";

type Role = "user" | "assistant";

type ActivityEvent =
  | { kind: "tool_use"; name: string; input: unknown }
  | { kind: "tool_result"; content: string };

interface Message {
  role: Role;
  text: string;
  cost?: number | null;
  activity?: ActivityEvent[];
}

interface HistoryEntry {
  chat_id: string;
  role: "user" | "agent";
  message: string;
  activity?: ActivityEvent[];
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/history");
        if (!res.ok) return;
        const data: { messages: HistoryEntry[] } = await res.json();
        setMessages(
          (data.messages || []).map((m) => ({
            role: m.role === "agent" ? "assistant" : "user",
            text: m.message,
            activity: m.activity,
          })),
        );
      } catch (e) {
        console.error("History load failed:", e);
      }
    })();
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const autoResize = () => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  };

  const send = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setInput("");
    setTimeout(autoResize, 0);
    setSending(true);
    setMessages((prev) => [
      ...prev,
      { role: "user", text },
      { role: "assistant", text: "", activity: [] },
    ]);

    const updateLast = (mut: (m: Message) => Message) => {
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = mut(next[next.length - 1]);
        return next;
      });
    };

    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let sepIdx: number;
        while ((sepIdx = buffer.indexOf("\n\n")) !== -1) {
          const block = buffer.slice(0, sepIdx);
          buffer = buffer.slice(sepIdx + 2);
          handleSse(block, updateLast);
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      updateLast((m) => ({ ...m, text: `Error: ${msg}` }));
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="app-grid">
      <section className="chat-pane">
        <header>
          <h1>Sett Playable Editor</h1>
        </header>

        <div id="messages" ref={scrollRef}>
          {messages.map((m, i) => (
            <MessageBubble key={i} message={m} streaming={sending && i === messages.length - 1} />
          ))}
        </div>

        <div id="input-area">
          <textarea
            ref={inputRef}
            rows={1}
            placeholder="Send a message..."
            autoFocus
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              autoResize();
            }}
            onKeyDown={onKeyDown}
            disabled={sending}
          />
          <button onClick={send} disabled={sending}>
            Send
          </button>
        </div>
      </section>

      <section className="preview-pane">
        <PlayablePreview />
      </section>
    </div>
  );
}

function handleSse(block: string, updateLast: (m: (msg: Message) => Message) => void) {
  let event = "message";
  let dataRaw = "";
  for (const line of block.split("\n")) {
    if (line.startsWith("event: ")) event = line.slice(7).trim();
    else if (line.startsWith("data: ")) dataRaw += line.slice(6);
  }
  if (!dataRaw) return;
  let data: any;
  try {
    data = JSON.parse(dataRaw);
  } catch {
    return;
  }

  if (event === "text") {
    updateLast((m) => ({ ...m, text: (m.text || "") + (data.content || "") }));
  } else if (event === "tool_use") {
    updateLast((m) => ({
      ...m,
      activity: [...(m.activity || []), { kind: "tool_use", name: data.name, input: data.input }],
    }));
  } else if (event === "tool_result") {
    updateLast((m) => ({
      ...m,
      activity: [...(m.activity || []), { kind: "tool_result", content: data.content }],
    }));
  } else if (event === "done") {
    updateLast((m) => ({
      ...m,
      cost: data.cost_usd,
      text: data.reply || m.text,
    }));
  } else if (event === "error") {
    updateLast((m) => ({ ...m, text: `Error: ${data.message}` }));
  }
}

function MessageBubble({ message: m, streaming }: { message: Message; streaming: boolean }) {
  const hasActivity = m.activity && m.activity.length > 0;

  return (
    <div className={`msg-row ${m.role}`}>
      {m.role === "assistant" && hasActivity && (
        <details className="activity-wrapper" open={streaming}>
          <summary className="activity-summary">Logs</summary>
          <div className="activity-log">
            {m.activity!.map((a, i) => (
              <div key={i} className={`activity-${a.kind}`}>
                {a.kind === "tool_use" ? (
                  <>
                    <span className="activity-bullet">●</span>
                    <span className="activity-name">{a.name}</span>
                    <span className="activity-input">({summarizeInput(a.input)})</span>
                  </>
                ) : (
                  <>
                    <span className="activity-corner">⎿</span>
                    <pre className="activity-result">{a.content}</pre>
                  </>
                )}
              </div>
            ))}
          </div>
        </details>
      )}
      {(m.text || streaming) && (
        <div className={`msg ${m.role}`}>
          {m.text ? (
            m.role === "assistant" ? (
              <div className="markdown">
                <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{m.text}</ReactMarkdown>
              </div>
            ) : (
              m.text
            )
          ) : (
            <span className="thinking-placeholder">
              Thinking<span className="dot-pulse"></span>
            </span>
          )}
        </div>
      )}
      {m.cost != null && <div className="cost">${m.cost.toFixed(4)}</div>}
    </div>
  );
}

function summarizeInput(input: unknown): string {
  if (!input || typeof input !== "object") return "";
  const obj = input as Record<string, unknown>;
  const keys = ["file_path", "path", "pattern", "command", "url"];
  for (const k of keys) {
    const v = obj[k];
    if (typeof v === "string") return v.length > 80 ? v.slice(0, 80) + "…" : v;
  }
  const first = Object.entries(obj)[0];
  if (!first) return "";
  const v = String(first[1]);
  return v.length > 80 ? v.slice(0, 80) + "…" : v;
}
