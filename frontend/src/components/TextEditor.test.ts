import { describe, expect, it } from "vitest";

import { htmlDocument, renderMarkdown } from "./TextEditor";

describe("renderMarkdown", () => {
  it("renders Markdown", () => {
    const html = renderMarkdown("# Sarlavha\n\n**qalin** va [havola](https://example.uz)");
    expect(html).toContain("<h1>Sarlavha</h1>");
    expect(html).toContain("<strong>qalin</strong>");
    expect(html).toContain('href="https://example.uz"');
  });

  it("strips scripts, handlers and javascript: links", () => {
    const html = renderMarkdown(
      '<script>alert(1)</script><img src=x onerror="alert(2)"><a href="javascript:alert(3)">x</a><iframe src="https://evil"></iframe>',
    );
    expect(html).not.toMatch(/<script|onerror|javascript:|<iframe/i);
  });
});

describe("htmlDocument", () => {
  it("escapes the title", () => {
    expect(htmlDocument("<b>x</b>", "<p>y</p>")).toContain("<title>&lt;b&gt;x&lt;/b&gt;</title>");
  });
});
