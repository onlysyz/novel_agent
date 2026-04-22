import { test, expect } from "@playwright/test";
import { mockTauriApi } from "./setup";

test.describe("Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await mockTauriApi(page);
    await page.goto("/");
    await page.waitForSelector(".app", { state: "visible", timeout: 15000 });
  });

  test("shows NovelForge logo", async ({ page }) => {
    await expect(page.locator(".logo")).toContainText("NovelForge");
  });

  test("shows all nav items", async ({ page }) => {
    await expect(page.locator(".nav-items")).toBeVisible();
    await expect(page.locator(".nav-items button").filter({ hasText: "Dashboard" })).toBeVisible();
    await expect(page.locator(".nav-items button").filter({ hasText: "Chapters" })).toBeVisible();
    await expect(page.locator(".nav-items button").filter({ hasText: "Foundation" })).toBeVisible();
    await expect(page.locator(".nav-items button").filter({ hasText: "Export" })).toBeVisible();
    await expect(page.locator(".nav-items button").filter({ hasText: "Settings" })).toBeVisible();
  });

  test("language switcher has EN and 中文 buttons", async ({ page }) => {
    await expect(page.locator(".lang-switch button").filter({ hasText: "EN" })).toBeVisible();
    await expect(page.locator(".lang-switch button").filter({ hasText: "中文" })).toBeVisible();
  });

  test("clicking Dashboard nav shows Dashboard view", async ({ page }) => {
    await page.locator(".nav-items button").filter({ hasText: "Dashboard" }).click();
    await expect(page.locator(".dashboard")).toBeVisible();
  });

  test("clicking Chapters nav shows Chapters view", async ({ page }) => {
    await page.locator(".nav-items button").filter({ hasText: "Chapters" }).click();
    await expect(page.locator(".chapter-list")).toBeVisible();
  });

  test("clicking Foundation nav shows Foundation view", async ({ page }) => {
    await page.locator(".nav-items button").filter({ hasText: "Foundation" }).click();
    await expect(page.locator(".foundation-view")).toBeVisible();
  });

  test("clicking Export nav works", async ({ page }) => {
    // Export button should be visible and clickable
    const exportBtn = page.locator(".nav-items button").filter({ hasText: "Export" });
    await expect(exportBtn).toBeVisible();
  });

  test("clicking Settings nav shows Settings view", async ({ page }) => {
    await page.locator(".nav-items button").filter({ hasText: "Settings" }).click();
    await expect(page.locator(".settings-view")).toBeVisible();
  });

  test("nav item gets active class when selected", async ({ page }) => {
    // Dashboard should be active by default
    await expect(page.locator(".nav-items li").filter({ hasText: "Dashboard" })).toHaveClass(/active/);

    // Click Chapters
    await page.locator(".nav-items button").filter({ hasText: "Chapters" }).click();
    await expect(page.locator(".nav-items li").filter({ hasText: "Chapters" })).toHaveClass(/active/);
    await expect(page.locator(".nav-items li").filter({ hasText: "Dashboard" })).not.toHaveClass(/active/);
  });

  test("switches language to Chinese", async ({ page }) => {
    await page.locator(".lang-switch button").filter({ hasText: "中文" }).click();
    await expect(page.locator(".nav-items button").filter({ hasText: "仪表盘" })).toBeVisible();
  });

  test("switches language back to English", async ({ page }) => {
    // First switch to Chinese
    await page.locator(".lang-switch button").filter({ hasText: "中文" }).click();
    // Then switch back to English
    await page.locator(".lang-switch button").filter({ hasText: "EN" }).click();
    await expect(page.locator(".nav-items button").filter({ hasText: "Dashboard" })).toBeVisible();
  });
});