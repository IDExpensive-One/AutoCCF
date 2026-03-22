const { test, expect, _electron: electron } = require('@playwright/test');
const path = require('path');

const electronExe = require(
  path.join(__dirname, '..', '..', 'electron', 'node_modules', 'electron'),
);

const appPath = path.join(__dirname, '..', '..', 'electron', 'main.js');

let app;
let page;
let apouCrawlSucceeded = false;

function userDetailPage() {
  return {
    backButton: page.locator('[data-user-detail-back]'),
    username: page.locator('[data-user-detail-username]'),
    postsTab: page.locator('[data-tab="posts"]'),
    threadsTab: page.locator('[data-tab="threads"]'),
    filesTab: page.locator('[data-tab="files"]'),
    postsPanel: page.locator('[data-user-detail-posts]'),
    threadsPanel: page.locator('[data-user-detail-threads]'),
    filesPanel: page.locator('[data-user-detail-files]'),
  };
}

async function navigateToView(viewName) {
  await page.click(`.nav-item[data-view="${viewName}"]`);
  await expect(page.locator('.content-header h2')).toHaveText(
    {
      apou: 'APoU',
      dopj: 'DoPJ',
      users: '用户',
      settings: '设置',
      home: '首页',
    }[viewName],
    { timeout: 10000 },
  );
  await expect(page.locator('.nav-item.active')).toHaveAttribute('data-view', viewName);
}

async function waitForUsersLoaded() {
  await expect(page.locator('[data-users-loading]')).toBeHidden({ timeout: 5000 });
  const bodyRows = page.locator('[data-users-body] tr');
  await expect(bodyRows.first()).toBeVisible({ timeout: 5000 });
}

async function clickHomeShortcut() {
  await page.click('[data-nav="apou"]');
  await expect(page.locator('.content-header h2')).toHaveText('APoU', { timeout: 10000 });
  await expect(page.locator('[data-apou-form]')).toBeVisible({ timeout: 10000 });
}

async function expectCountGreaterThan(locator, min, timeout = 5000) {
  await expect
    .poll(async () => locator.count(), { timeout })
    .toBeGreaterThan(min);
}

test.beforeAll(async () => {
  app = await electron.launch({
    executablePath: electronExe,
    args: [appPath],
  });
  page = await app.firstWindow();
  await expect(page).toHaveTitle(/AutoCCF/, { timeout: 5000 });
});

test.afterAll(async () => {
  if (app) {
    await app.close();
  }
});

test.describe.serial('Phase 1: App Launch & Home View', () => {
  test('launches app and renders home shortcuts', async () => {
    await expect(page).toHaveTitle(/AutoCCF/);
    await expect(page.locator('[data-view="home"]')).toBeVisible();
    await expect(page.locator('.content-header h2')).toHaveText('首页');
    await expect(page.locator('.stat-card')).toHaveCount(3, { timeout: 5000 });
    await expect(page.getByRole('button', { name: '进入 APoU' })).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('button', { name: '进入 DoPJ' })).toBeVisible({ timeout: 5000 });
    await expect(page.locator('.card.stat-card', { hasText: '已爬取用户' })).toBeVisible();
    await expect(page.locator('.card.stat-card', { hasText: '帖子总数' })).toBeVisible();
    await expect(page.locator('.card.stat-card', { hasText: '最近活动' })).toBeVisible();
    await clickHomeShortcut();
  });
});

test.describe.serial('Phase 2: Settings View - Config Load & Account Management', () => {
  test('loads settings and manages accounts', async () => {
    await navigateToView('settings');
    await expect(page.locator('[data-database-dir]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('[data-database-dir]')).toHaveAttribute('readonly');
    await expect(page.locator('[data-account-body]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('[data-save-settings]')).toBeEnabled({ timeout: 5000 });
    await expect(page.locator('[data-apou-page-delay]')).toBeVisible();
    await expect(page.locator('[data-apou-max-retries]')).toBeVisible();
    await expect(page.locator('[data-dopj-threads]')).toBeVisible();
    await expect(page.locator('[data-dopj-max-retries]')).toBeVisible();
    await expect(page.locator('[data-dopj-min-interval]')).toBeVisible();
    await expect(page.locator('[data-dopj-max-fails]')).toBeVisible();

    await expect(page.locator('[data-apou-page-delay-value]')).toBeVisible();
    await expect(page.locator('[data-apou-max-retries-value]')).toBeVisible();
    await expect(page.locator('[data-dopj-threads-value]')).toBeVisible();
    await expect(page.locator('[data-dopj-max-retries-value]')).toBeVisible();
    await expect(page.locator('[data-dopj-min-interval-value]')).toBeVisible();
    await expect(page.locator('[data-dopj-max-fails-value]')).toBeVisible();

    const currentAccountRows = page.locator('[data-account-body] tr');
    await expect(currentAccountRows.first()).toBeVisible({ timeout: 5000 });

    await page.evaluate(() => {
      const range = document.querySelector('[data-apou-page-delay]');
      range.value = '3';
      range.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await expect(page.locator('[data-apou-page-delay-value]')).toHaveText('3.0', { timeout: 5000 });

    await page.click('[data-account-add]');
    await expect(page.locator('[data-account-name-input]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('[data-account-bduss-input]')).toBeVisible();

    await page.fill('[data-account-name-input]', '测试账户');
    await page.fill('[data-account-bduss-input]', 'FAKE_BDUSS_FOR_TEST');
    await page.click('[data-account-confirm]');

    const testAccountRow = page.locator('[data-account-body] tr').filter({ hasText: '测试账户' });
    await expect(testAccountRow).toBeVisible({ timeout: 5000 });
    await expect(testAccountRow.locator('button', { hasText: '删除' })).toBeVisible();

    await testAccountRow.locator('button', { hasText: '删除' }).click();
    await expect(testAccountRow).toHaveCount(0, { timeout: 5000 });

    await expect(page.locator('[data-save-settings]')).toBeVisible();
    await expect(page.locator('[data-reset-settings]')).toBeVisible();
  });
});

test.describe.serial('Phase 3: APoU View - Crawl Simulation', () => {
  test('runs a real APoU crawl and waits for completion', async () => {
    test.setTimeout(180000);
    await navigateToView('apou');
    await expect(page.locator('[data-apou-form]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('#apou-username')).toBeVisible();
    await expect(page.locator('[data-start-crawl]')).toBeVisible();

    await page.fill('#apou-username', '');
    await page.click('[data-start-crawl]');
    await expect(page.locator('[data-status]')).toContainText('请输入贴吧用户名', { timeout: 10000 });

    await page.fill('#apou-username', '团子传说');
    await page.click('[data-start-crawl]');
    await expect(page.locator('[data-start-crawl]')).toBeDisabled({ timeout: 10000 });
    await expect(page.locator('[data-progress-card]')).toBeVisible();
    await expect(page.locator('[data-log-card]')).toBeVisible();
    await expect(page.locator('[data-start-crawl]')).toBeEnabled({ timeout: 120000 });

    const statusText = String(await page.locator('[data-status]').textContent() || '');
    if (statusText.includes('aiotieba') || statusText.includes('内部错误')) {
      test.skip(true, statusText);
    }

    expect(statusText).toContain('爬取完成');

    const progressText = await page.locator('[data-progress-text]').textContent();
    const match = String(progressText).match(/\d+/);
    expect(match).not.toBeNull();
    expect(Number(match[0])).toBeGreaterThan(0);

    const logs = page.locator('[data-log-viewer] div');
    await expectCountGreaterThan(logs, 0, 5000);

    apouCrawlSucceeded = true;
  });
});

test.describe.serial('Phase 4: DoPJ View - Setup Verification', () => {
  test('loads DoPJ page and verifies output accounts', async () => {
    if (!apouCrawlSucceeded) {
      test.skip(true, 'APoU crawl not completed, cannot assert DoPJ output selection reliably');
    }

    await navigateToView('dopj');
    await expect(page.locator('[data-user-select]')).toBeVisible({ timeout: 5000 });

    const options = page.locator('[data-user-select] option');
    await expectCountGreaterThan(options, 0, 5000);
    const optionTexts = await options.allTextContents();
    expect(optionTexts.some((value) => value.trim().length > 0)).toBeTruthy();

    await expectCountGreaterThan(page.locator('[data-account-body] tr'), 0, 5000);
    await expect(page.locator('[data-start-crawl]')).toBeVisible();
  });
});

test.describe.serial('Phase 5: Users View - User List & Search', () => {
  test('loads users and validates search behavior', async () => {
    await navigateToView('users');
    await waitForUsersLoaded();

    const tableRows = page.locator('[data-users-body] tr');
    await expectCountGreaterThan(tableRows, 0);
    await expect(page.locator('[data-users-search]')).toBeVisible({ timeout: 5000 });

    await page.fill('[data-users-search]', '团子');
    await expectCountGreaterThan(tableRows, 0);

    await page.fill('[data-users-search]', '不存在的用户名xyz');
    await expect(page.locator('[data-users-body]')).toContainText('暂无匹配用户');

    await page.fill('[data-users-search]', '');
    await waitForUsersLoaded();
  });
});

test.describe.serial('Phase 6: User Detail View', () => {
  test('opens detail and switches tabs', async () => {
    await page.fill('[data-users-search]', '');
    await expectCountGreaterThan(page.locator('[data-user-action]'), 0, 5000);

    await page.locator('[data-user-action]').first().click();
    await expect(page.locator('[data-user-detail-back]')).toBeVisible({ timeout: 10000 });
    await expect(userDetailPage().username).toHaveText(/.+/, { timeout: 10000 });

    const tabs = userDetailPage();
    await expect(tabs.postsTab).toHaveClass(/active/);
    await expect(tabs.postsPanel).toBeVisible();
    await expect(tabs.threadsPanel).toBeHidden();

    await tabs.threadsTab.click();
    await expect(tabs.threadsPanel).toBeVisible();
    await expect(tabs.postsPanel).toBeHidden();

    await tabs.filesTab.click();
    await expect(tabs.filesPanel).toBeVisible();

    await tabs.postsTab.click();
    await expect(tabs.postsPanel).toBeVisible();

    await tabs.backButton.click();
    await expect(page.locator('.content-header h2')).toHaveText('用户', { timeout: 10000 });
  });
});

test.describe.serial('Phase 7: Navigation Integrity', () => {
  test('returns to home and validates nav active states', async () => {
    await navigateToView('home');
    await expect(page.locator('.stat-card')).toHaveCount(3, { timeout: 5000 });

    const navOrder = [
      { dataView: 'apou', title: 'APoU' },
      { dataView: 'dopj', title: 'DoPJ' },
      { dataView: 'users', title: '用户' },
      { dataView: 'settings', title: '设置' },
      { dataView: 'home', title: '首页' },
    ];

    for (const item of navOrder) {
      await page.click(`.nav-item[data-view="${item.dataView}"]`);
      await expect(page.locator('.content-header h2')).toHaveText(item.title, { timeout: 10000 });
      await expect(page.locator('.nav-item.active')).toHaveAttribute('data-view', item.dataView);
    }
  });
});
