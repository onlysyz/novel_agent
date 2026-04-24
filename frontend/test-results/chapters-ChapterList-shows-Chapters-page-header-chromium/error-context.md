# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: chapters.spec.ts >> ChapterList >> shows Chapters page header
- Location: tests-e2e/chapters.spec.ts:13:3

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:1420/
Call log:
  - navigating to "http://localhost:1420/", waiting until "load"

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - generic [ref=e6]:
    - heading "无法访问此网站" [level=1] [ref=e7]
    - paragraph [ref=e8]:
      - strong [ref=e9]: localhost
      - text: 拒绝了我们的连接请求。
    - generic [ref=e10]:
      - paragraph [ref=e11]: 请试试以下办法：
      - list [ref=e12]:
        - listitem [ref=e13]: 检查网络连接
        - listitem [ref=e14]:
          - link "检查代理服务器和防火墙" [ref=e15] [cursor=pointer]:
            - /url: "#buttons"
    - generic [ref=e16]: ERR_CONNECTION_REFUSED
  - generic [ref=e17]:
    - button "重新加载" [ref=e19] [cursor=pointer]
    - button "详情" [ref=e20] [cursor=pointer]
```

# Test source

```ts
  1  | import { test, expect } from "@playwright/test";
  2  | import { mockTauriApi } from "./setup";
  3  | 
  4  | test.describe("ChapterList", () => {
  5  |   test.beforeEach(async ({ page }) => {
> 6  |     await mockTauriApi(page);
     |                ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:1420/
  7  |     await page.goto("/");
  8  |     await page.waitForSelector(".app", { state: "visible", timeout: 15000 });
  9  |     // Navigate to Chapters
  10 |     await page.locator(".nav-items button").filter({ hasText: "Chapters" }).click();
  11 |     await page.waitForSelector(".chapter-list", { state: "visible" });
  12 |   });
  13 | 
  14 |   test("shows Chapters page header", async ({ page }) => {
  15 |     await expect(page.locator(".chapter-list h1")).toContainText("Chapters");
  16 |   });
  17 | 
  18 |   test("displays chapter cards from mock data", async ({ page }) => {
  19 |     const cards = page.locator(".chapter-card");
  20 |     await expect(cards).toHaveCount(3);
  21 |   });
  22 | 
  23 |   test("first chapter shows correct title", async ({ page }) => {
  24 |     await expect(page.locator(".chapter-card").first().locator(".chapter-title")).toContainText("The Beginning");
  25 |   });
  26 | 
  27 |   test("first chapter shows correct word count", async ({ page }) => {
  28 |     await expect(page.locator(".chapter-card").first().locator(".chapter-meta")).toContainText("3,500");
  29 |   });
  30 | 
  31 |   test("chapter with score shows score label", async ({ page }) => {
  32 |     // First two chapters have scores
  33 |     await expect(page.locator(".chapter-card").first().locator(".score")).toContainText("Score:");
  34 |     await expect(page.locator(".chapter-card").first().locator(".score")).toContainText("7.5");
  35 |   });
  36 | 
  37 |   test("chapter without score does not show score", async ({ page }) => {
  38 |     // Third chapter has score: null
  39 |     const thirdCard = page.locator(".chapter-card").nth(2);
  40 |     await expect(thirdCard.locator(".score")).toHaveCount(0);
  41 |   });
  42 | 
  43 |   test("clicking chapter card selects it", async ({ page }) => {
  44 |     await page.locator(".chapter-card").first().click();
  45 |     // Chapter editor should appear (rendered in parent App component)
  46 |     await expect(page.locator(".chapter-editor")).toBeVisible();
  47 |   });
  48 | 
  49 |   test("selected chapter card has selected class", async ({ page }) => {
  50 |     await page.locator(".chapter-card").first().click();
  51 |     await expect(page.locator(".chapter-card.selected")).toHaveCount(1);
  52 |   });
  53 | 
  54 |   test("chapter editor shows close button", async ({ page }) => {
  55 |     await page.locator(".chapter-card").first().click();
  56 |     await expect(page.locator(".chapter-editor .btn-secondary")).toContainText("Close");
  57 |   });
  58 | 
  59 |   test("chapter editor shows chapter content", async ({ page }) => {
  60 |     await page.locator(".chapter-card").first().click();
  61 |     // Editor textarea should be visible
  62 |     await expect(page.locator(".chapter-editor textarea")).toBeVisible();
  63 |   });
  64 | 
  65 |   test("clicking close button closes chapter editor", async ({ page }) => {
  66 |     await page.locator(".chapter-card").first().click();
  67 |     await expect(page.locator(".chapter-editor")).toBeVisible();
  68 |     await page.locator(".chapter-editor .btn-secondary").click();
  69 |     await expect(page.locator(".chapter-editor")).not.toBeVisible();
  70 |   });
  71 | 
  72 |   test("chapter numbers show chapter text", async ({ page }) => {
  73 |     // Should show "Chapter" (translation may or may not include number)
  74 |     await expect(page.locator(".chapter-card").first().locator(".chapter-number")).toContainText("Chapter");
  75 |   });
  76 | });
```