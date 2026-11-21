/** Where people reach the team. VITE_* values (set at build time) override the defaults. */
export const CONTACT_EMAIL = import.meta.env.VITE_CONTACT_EMAIL || "jichchainfo@gmail.com";
export const TELEGRAM_USERNAME = import.meta.env.VITE_TELEGRAM_USERNAME || "jichcha_info";
export const TELEGRAM_URL = `https://t.me/${encodeURIComponent(TELEGRAM_USERNAME)}`;
