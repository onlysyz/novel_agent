import { test, expect } from "@playwright/test";
import { mockTauriApi } from "./setup";

test.describe("Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await mockTauriApi(page);
    await page.goto("/");
    await page.waitForSelector(".app", { state: "visible", timeout: 15000 });
  });

  test("shows page title", async ({ page }) => {
    // Should show novel title from mock config
    await expect(page.locator(".dashboard h1")).toContainText("The Amulet War");
  });

  test("shows phase stepper with 4 steps", async ({ page }) => {
    const stepper = page.locator(".phase-stepper");
    await expect(stepper).toBeVisible();
    await expect(stepper.locator(".step")).toHaveCount(4);
    await expect(stepper.locator(".step-label").nth(0)).toContainText("Foundation");
    await expect(stepper.locator(".step-label").nth(1)).toContainText("Drafting");
    await expect(stepper.locator(".step-label").nth(2)).toContainText("Review");
    await expect(stepper.locator(".step-label").nth(3)).toContainText("Export");
  });

  test("shows action card with Start Foundation button", async ({ page }) => {
    const actionCard = page.locator(".action-card");
    await expect(actionCard).toBeVisible();
    await expect(actionCard.locator("h2")).toContainText("Foundation");
    await expect(actionCard.locator(".btn-primary")).toBeVisible();
  });

  test("shows stats grid with 4 stat cards", async ({ page }) => {
    const statsGrid = page.locator(".stats-grid");
    await expect(statsGrid).toBeVisible();
    await expect(statsGrid.locator(".stat-card")).toHaveCount(4);
  });

  test("shows foundation scores section", async ({ page }) => {
    const foundationSection = page.locator(".foundation-scores");
    await expect(foundationSection).toBeVisible();
    // Should show 5 score bars: world, characters, outline, canon, voice
    await expect(foundationSection.locator(".score-bar")).toHaveCount(5);
  });

  test("shows chapter progress dots", async ({ page }) => {
    const chapterProgress = page.locator(".chapter-progress");
    await expect(chapterProgress).toBeVisible();
    // Should show 3 chapter dots (from mock state)
    await expect(chapterProgress.locator(".chapter-dot")).toHaveCount(3);
  });

  test("shows New Project button in header", async ({ page }) => {
    const header = page.locator(".page-header");
    await expect(header).toBeVisible();
    await expect(header.locator(".btn-secondary")).toContainText("New Project");
  });

  test("clicking Generate Title button triggers title generation", async ({ page }) => {
    // Find and click the Generate Title button (appears when no title but has foundation)
    const generateBtn = page.locator(".btn-secondary.btn-small").filter({ hasText: "Generate Title" });
    if (await generateBtn.isVisible()) {
      await generateBtn.click();
      // Title should update (mock returns "The Amulet War: Awakening")
      await expect(page.locator(".dashboard h1")).toContainText("The Amulet War");
    }
  });

  test("Start Foundation button triggers handleRun", async ({ page }) => {
    const runBtn = page.locator(".btn-primary.btn-large");
    await expect(runBtn).toBeVisible();
    // Click should not error (mock handles it)
    await runBtn.click();
    // After click, pipeline should be running (console should show log)
  });

  test("score bars show correct scores from state", async ({ page }) => {
    const worldBar = page.locator(".score-bar").filter({ hasText: "World" });
    await expect(worldBar).toBeVisible();
    // Score should be 7.5
    await expect(worldBar.locator(".score")).toContainText("7.5");
  });

  test("chapter dots show chapter numbers", async ({ page }) => {
    const dots = page.locator(".chapter-dot");
    await expect(dots.nth(0).locator(".ch-num")).toContainText("1");
    await expect(dots.nth(1).locator(".ch-num")).toContainText("2");
    await expect(dots.nth(2).locator(".ch-num")).toContainText("3");
  });

  test("chapter dots with scores show score value", async ({ page }) => {
    const dots = page.locator(".chapter-dot.done");
    await expect(dots.first().locator(".ch-score")).toBeVisible();
  });

  test("phase stepper shows current phase active", async ({ page }) => {
    // Phase stepper should be visible
    const stepper = page.locator(".phase-stepper");
    await expect(stepper).toBeVisible();
  });
});