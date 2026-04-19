import { useEffect, useRef, useState } from "react";
import { PlayablePreview } from "./PlayablePreview";

type Role = "user" | "assistant";

interface Message {
  role: Role;
  text: string;
  cost?: number | null;
}

interface HistoryEntry {
  chat_id: string;
  role: "user" | "agent";
  message: string;
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [thinking, setThinking] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/history");
        if (!res.ok) return;
        const data: { messages: HistoryEntry[] } = await res.json();
        const loaded: Message[] = (data.messages || []).map((m) => ({
          role: m.role === "agent" ? "assistant" : "user",
          text: m.message,
        }));
        setMessages(loaded);
      } catch (e) {
        console.error("History load failed:", e);
      }
    })();
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, thinking]);

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
    setMessages((prev) => [...prev, { role: "user", text }]);
    setThinking(true);

    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: { reply: string; cost_usd: number | null } = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", text: data.reply, cost: data.cost_usd }]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setMessages((prev) => [...prev, { role: "assistant", text: `Error: ${msg}` }]);
    } finally {
      setThinking(false);
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
            <div key={i} className={`msg ${m.role}`}>
              {m.text}
              {m.cost != null && <div className="cost">${m.cost.toFixed(4)}</div>}
            </div>
          ))}
          {thinking && (
            <div className="msg thinking">
              Thinking<span className="dot-pulse"></span>
            </div>
          )}
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
