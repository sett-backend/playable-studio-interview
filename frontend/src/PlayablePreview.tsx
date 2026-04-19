import { useEffect, useState } from "react";

interface PlayableInfo {
  url: string | null;
  aspect: string;
}

function parseAspect(aspect: string): number {
  const [w, h] = aspect.split(":").map(Number);
  if (!w || !h) return 9 / 16;
  return w / h;
}

export function PlayablePreview() {
  const [info, setInfo] = useState<PlayableInfo | null>(null);
  const [iframeKey, setIframeKey] = useState(0);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/playable");
        if (!res.ok) return;
        setInfo(await res.json());
      } catch (e) {
        console.error("Playable fetch failed:", e);
      }
    })();
  }, []);

  if (!info?.url) {
    return (
      <div className="preview-empty">
        No <code>PLAYABLE_URL</code> set. Copy <code>.env.example</code> to{" "}
        <code>.env</code> and point it at your running <code>npm run dev</code>.
      </div>
    );
  }

  const ratio = parseAspect(info.aspect);

  return (
    <div className="preview-root">
      <div className="preview-toolbar">
        <div className="preview-title">
          <div className="preview-title-row">
            <span className="header-dot" aria-hidden />
            <h2>Modified Playable</h2>
          </div>
          <span className="preview-url">Running on {info.url}</span>
        </div>
        <button
          className="reload-btn"
          onClick={() => setIframeKey((k) => k + 1)}
          aria-label="Reload"
          title="Reload"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 12a9 9 0 1 1-3-6.7" />
            <path d="M21 3v6h-6" />
          </svg>
        </button>
      </div>
      <div className="preview-stage">
        <div className="preview-frame" style={{ aspectRatio: String(ratio) }}>
          <iframe
            key={iframeKey}
            src={info.url}
            title="playable preview"
            allow="autoplay; fullscreen"
          />
        </div>
      </div>
    </div>
  );
}
