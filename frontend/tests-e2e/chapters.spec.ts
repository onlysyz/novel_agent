import { test, expect } from "@playwright/test";
import { mockTauriApi } from "./setup";

test.describe("ChapterList", () => {
  test.beforeEach(async ({ page }) => {
    await mockTauriApi(page);
    await page.goto("/");
    await page.waitForSelector(".app", { state: "visible", timeout: 15000 });
    // Navigate to Chapters
    await page.locator(".nav-items button").filter({ hasText: "Chapters" }).click();
    await page.waitForSelector(".chapter-list", { state: "visible" });
  });

  test("shows Chapters page header", async ({ page }) => {
    await expect(page.locator(".chapter-list h1")).toContainText("Chapters");
  });

  test("displays chapter cards from mock data", async ({ page }) => {
    const cards = page.locator(".chapter-card");
    await expect(cards).toHaveCount(3);
  });

  test("first chapter shows correct title", async ({ page }) => {
    await expect(page.locator(".chapter-card").first().locator(".chapter-title")).toContainText("The Beginning");
  });

  test("first chapter shows correct word count", async ({ page }) => {
    await expect(page.locator(".chapter-card").first().locator(".chapter-meta")).toContainText("3,500");
  });

  test("chapter with score shows score label", async ({ page }) => {
    // First two chapters have scores
    await expect(page.locator(".chapter-card").first().locator(".score")).toContainText("Score:");
    await expect(page.locator(".chapter-card").first().locator(".score")).toContainText("7.5");
  });

  test("chapter without score does not show score", async ({ page }) => {
    // Third chapter has score: null
    const thirdCard = page.locator(".chapter-card").nth(2);
    await expect(thirdCard.locator(".score")).toHaveCount(0);
  });

  test("clicking chapter card selects it", async ({ page }) => {
    await page.locator(".chapter-card").first().click();
    // Chapter editor should appear (rendered in parent App component)
    await expect(page.locator(".chapter-editor")).toBeVisible();
  });

  test("selected chapter card has selected class", async ({ page }) => {
    await page.locator(".chapter-card").first().click();
    await expect(page.locator(".chapter-card.selected")).toHaveCount(1);
  });

  test("chapter editor shows close button", async ({ page }) => {
    await page.locator(".chapter-card").first().click();
    await expect(page.locator(".chapter-editor .btn-secondary")).toContainText("Close");
  });

  test("chapter editor shows chapter content", async ({ page }) => {
    await page.locator(".chapter-card").first().click();
    // Editor textarea should be visible
    await expect(page.locator(".chapter-editor textarea")).toBeVisible();
  });

  test("clicking close button closes chapter editor", async ({ page }) => {
    await page.locator(".chapter-card").first().click();
    await expect(page.locator(".chapter-editor")).toBeVisible();
    await page.locator(".chapter-editor .btn-secondary").click();
    await expect(page.locator(".chapter-editor")).not.toBeVisible();
  });

  test("chapter numbers show chapter text", async ({ page }) => {
    // Should show "Chapter" (translation may or may not include number)
    await expect(page.locator(".chapter-card").first().locator(".chapter-number")).toContainText("Chapter");
  });
});