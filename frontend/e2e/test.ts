/**
 * Playwright's test, with page.goto waiting until the app has taken over the prerendered HTML
 * (html[data-app=ready]). Before that, the page is static markup: a file set on its input would be
 * lost when React replaces it. Specs import { test, expect } from "./test".
 */
import { test as base } from "@playwright/test";

export { expect, type Page } from "@playwright/test";

export const test = base.extend({
  page: async ({ page }, provide) => {
    const goto = page.goto.bind(page);
    page.goto = async (url, options) => {
      const response = await goto(url, options);
      await page.waitForSelector("html[data-app=ready]", { state: "attached" });
      return response;
    };
    await provide(page);
  },
});
