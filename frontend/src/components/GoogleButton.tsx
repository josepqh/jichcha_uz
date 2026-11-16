import { useEffect, useRef } from "react";

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? "";
const SCRIPT_SRC = "https://accounts.google.com/gsi/client";

interface GoogleId {
  initialize: (config: { client_id: string; callback: (r: { credential: string }) => void; ux_mode: "popup" }) => void;
  renderButton: (el: HTMLElement, options: Record<string, unknown>) => void;
}
declare global {
  interface Window {
    google?: { accounts: { id: GoogleId } };
  }
}

let loading: Promise<void> | null = null;
function loadScript(): Promise<void> {
  loading ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      loading = null;
      reject(new Error("gsi"));
    };
    document.head.appendChild(script);
  });
  return loading;
}

export const googleEnabled = CLIENT_ID !== "";

/** Official Google button (Google Identity Services). Renders nothing when no client id is configured. */
export function GoogleButton({ lang, onCredential }: { lang: string; onCredential: (credential: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const callback = useRef(onCredential);
  callback.current = onCredential;

  useEffect(() => {
    if (!googleEnabled) return;
    let cancelled = false;
    loadScript()
      .then(() => {
        const el = ref.current;
        const gsi = window.google?.accounts.id;
        if (cancelled || !el || !gsi) return;
        gsi.initialize({ client_id: CLIENT_ID, callback: (r) => callback.current(r.credential), ux_mode: "popup" });
        gsi.renderButton(el, {
          theme: document.documentElement.classList.contains("dark") ? "filled_black" : "outline",
          size: "large",
          shape: "rectangular",
          text: "continue_with",
          width: Math.min(el.clientWidth, 400),
          locale: lang,
        });
      })
      .catch(() => undefined); // blocked by an extension or offline: email sign-in still works
    return () => {
      cancelled = true;
    };
  }, [lang]);

  if (!googleEnabled) return null;
  return <div ref={ref} className="flex min-h-11 w-full justify-center" />;
}
