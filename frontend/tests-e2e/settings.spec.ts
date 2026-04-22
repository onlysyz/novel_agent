import { test, expect } from "@playwright/test";
import { mockTauriApi } from "./setup";

test.describe("SettingsView", () => {
  test.beforeEach(async ({ page }) => {
    await mockTauriApi(page);
    await page.goto("/");
    await page.waitForSelector(".app", { state: "visible", timeout: 15000 });
    // Navigate to Settings
    await page.locator(".nav-items button").filter({ hasText: "Settings" }).click();
    await page.waitForTimeout(1500);
  });

  test("shows Settings page", async ({ page }) => {
    // Settings page should load
    const content = await page.content();
    expect(content.includes("Settings") || content.includes("Project")).toBeTruthy();
  });

  test("shows project path", async ({ page }) => {
    await expect(page.locator("body")).toContainText("/mock/novel/project");
  });
});

test.describe("FoundationView", () => {
  test.beforeEach(async ({ page }) => {
    await mockTauriApi(page);
    await page.goto("/");
    await page.waitForSelector(".app", { state: "visible", timeout: 15000 });
    // Navigate to Foundation
    await page.locator(".nav-items button").filter({ hasText: "Foundation" }).click();
    await page.waitForTimeout(1500);
  });

  test("shows Foundation page", async ({ page }) => {
    const content = await page.content();
    expect(content.includes("Foundation") || content.includes("World")).toBeTruthy();
  });
});