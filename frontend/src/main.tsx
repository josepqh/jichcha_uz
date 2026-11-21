// Self-hosted (latin + cyrillic subsets load on demand): no request to Google on page load.
import "@fontsource-variable/onest";
import "@fontsource-variable/unbounded";
import "@fontsource-variable/jetbrains-mono";
import "./index.css";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";

import { App } from "./App";
import { DEFAULT_LANGUAGE, directionOf, isLanguage, setLanguage } from "./i18n";

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false } },
});

// The page's language comes from its URL; its strings load before the first render, so no
// untranslated text flashes (the prerendered HTML stays on screen meanwhile).
const first = window.location.pathname.split("/")[1];
const lang = isLanguage(first) ? first : DEFAULT_LANGUAGE;
document.documentElement.dir = directionOf(lang);
await setLanguage(lang);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
