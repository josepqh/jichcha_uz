/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Google Identity Services client id. Sign-in with Google is hidden when empty. */
  readonly VITE_GOOGLE_CLIENT_ID?: string;
  readonly VITE_LEGAL_NAME?: string;
  readonly VITE_CONTACT_EMAIL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
