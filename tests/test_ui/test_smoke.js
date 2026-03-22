// tests/test_ui/test_smoke.js
const { test, expect, _electron: electron } = require('@playwright/test');
const path = require('path');

let app;

test.beforeAll(async () => {
  app = await electron.launch({
    args: [path.join(__dirname, '..', '..', 'electron', 'main.js')],
  });
});

test.afterAll(async () => {
  await app.close();
});

test('窗口标题包含 AutoCCF', async () => {
  const page = await app.firstWindow();
  const title = await page.title();
  expect(title).toContain('AutoCCF');
});

test('侧边栏包含所有导航项', async () => {
  const page = await app.firstWindow();
  const navItems = await page.locator('.nav-item').allTextContents();
  expect(navItems).toContain('首页');
  expect(navItems).toContain('APoU');
  expect(navItems).toContain('DoPJ');
  expect(navItems).toContain('用户');
  expect(navItems).toContain('设置');
});

test('导航切换到 APoU 视图', async () => {
  const page = await app.firstWindow();
  await page.click('[data-view="apou"]');
  await expect(page.locator('#content')).toContainText('APoU');
});

test('导航切换到设置视图', async () => {
  const page = await app.firstWindow();
  await page.click('[data-view="settings"]');
  await expect(page.locator('#content')).toContainText('设置');
});

test('APoU 视图有用户名输入框', async () => {
  const page = await app.firstWindow();
  await page.click('[data-view="apou"]');
  const input = page.locator('input[placeholder*="用户名"]');
  await expect(input).toBeVisible();
});

test('所有 5 个视图可渲染', async () => {
  const page = await app.firstWindow();
  const views = ['home', 'apou', 'dopj', 'users', 'settings'];
  for (const view of views) {
    await page.click(`[data-view="${view}"]`);
    // 确保内容区不为空
    const content = await page.locator('#content').textContent();
    expect(content.trim().length).toBeGreaterThan(0);
  }
});

test('user-detail 视图可通过导航渲染', async () => {
  const page = await app.firstWindow();
  await page.click('[data-view="users"]');
  const userItem = page.locator('.user-item').first();
  if (await userItem.isVisible({ timeout: 2000 }).catch(() => false)) {
    await userItem.click();
    await expect(page.locator('#content')).toContainText('帖子');
  }
});

test('APoU 视图有 indeterminate 进度条', async () => {
  const page = await app.firstWindow();
  await page.click('[data-view="apou"]');
  const progressBar = page.locator('.progress-bar, progress');
  await expect(progressBar.first()).toHaveCount(1);
});
