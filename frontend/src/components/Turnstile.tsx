import { useEffect, useRef } from "react";

const SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY ?? "";
const SCRIPT_SRC = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

interface TurnstileApi {
  render: (el: HTMLElement, options: Record<string, unknown>) => string;
  remove: (id: string) => void;
}
declare global {
  interface Window {
    turnstile?: TurnstileApi;
  }
}

export const turnstileEnabled = SITE_KEY !== "";

let loading: Promise<void> | null = null;
function loadScript(): Promise<void> {
  loading ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      loading = null;
      reject(new Error("turnstile"));
    };
    document.head.appendChild(script);
  });
  return loading;
}

/** Cloudflare Turnstile robot check (only when VITE_TURNSTILE_SITE_KEY is set). Reports the token, or "" when it expires. */
export function Turnstile({ lang, onToken }: { lang: string; onToken: (token: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const callback = useRef(onToken);
  useEffect(() => {
    callback.current = onToken;
  });

  useEffect(() => {
    if (!turnstileEnabled) return;
    let widget: string | null = null;
    let cancelled = false;
    loadScript()
      .then(() => {
        if (cancelled || !ref.current || !window.turnstile) return;
        widget = window.turnstile.render(ref.current, {
          sitekey: SITE_KEY,
          language: lang,
          theme: document.documentElement.classList.contains("dark") ? "dark" : "light",
          callback: (token: string) => callback.current(token),
          "expired-callback": () => callback.current(""),
          "error-callback": () => callback.current(""),
        });
      })
      .catch(() => callback.current(""));
    return () => {
      cancelled = true;
      if (widget && window.turnstile) window.turnstile.remove(widget);
    };
  }, [lang]);

  if (!turnstileEnabled) return null;
  return <div ref={ref} className="min-h-16" />;
}
