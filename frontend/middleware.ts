/**
 * Vercel Routing Middleware: sends /api/* to the backend (API_ORIGIN, e.g. the ngrok tunnel to the
 * Docker stack), so the browser only ever talks to the site's own origin (cookies stay first-party).
 *
 * Project env vars on Vercel:
 *   API_ORIGIN   https://<your-domain>.ngrok-free.app
 *   EDGE_SECRET  same value as EDGE_SECRET in the backend's .env (proves the request came through here)
 */
import { rewrite } from "@vercel/functions";

export const config = { matcher: "/api/:path*" };

export default function middleware(request: Request): Response {
  const origin = process.env.API_ORIGIN;
  if (!origin) {
    return Response.json(
      { error: { code: "tool_unavailable", message: "The service is offline right now.", details: {} } },
      { status: 503 },
    );
  }
  const url = new URL(request.url);
  const headers = new Headers(request.headers);
  headers.set("x-universe-edge", process.env.EDGE_SECRET ?? "");
  // ngrok's free plan shows a warning page to browsers unless this header is present.
  headers.set("ngrok-skip-browser-warning", "1");
  return rewrite(new URL(url.pathname + url.search, origin), { request: { headers } });
}
