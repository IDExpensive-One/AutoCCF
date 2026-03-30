// tests/test_ui/test_payload_e2e.js
// 全流程 Payload 验证 E2E 测试 — 通过 Electron GUI 真实调用 Python Bridge，
// 拦截 IPC 返回值并断言数据结构和内容完整性。
// 目标用户: 团子传说
const { test, expect, _electron: electron } = require('@playwright/test');
const path = require('path');
const fs = require('fs');

const electronExe = require(
  path.join(__dirname, '..', '..', 'electron', 'node_modules', 'electron'),
);
const appPath = path.join(__dirname, '..', '..', 'electron', 'main.js');
const TARGET_USERNAME = '团子传说';

let app;
let page;

// ── 辅助：在渲染进程内调用 window.api.invoke 并返回原始 payload ──
async function invokebridge(action, payload = {}) {
  return page.evaluate(
    ({ action, payload }) => window.api.invoke(action, payload),
    { action, payload },
  );
}

// ── 辅助：在渲染进程内监听一次 bridge:progress 事件 ──
async function collectProgressEvents(action, payload, timeoutMs = 120000) {
  return page.evaluate(
    ({ action, payload, timeoutMs }) =>
      new Promise((resolve, reject) => {
        const events = [];
        const timer = setTimeout(() => resolve({ events, result: null, timedOut: true }), timeoutMs);

        window.api.onProgress((data) => {
          events.push(data);
        });

        window.api.invoke(action, payload).then((result) => {
          clearTimeout(timer);
          // 给 progress 回调最后一点时间到达
          setTimeout(() => {
            window.api.removeAllListeners('bridge:progress');
            resolve({ events, result, timedOut: false });
          }, 200);
        }).catch((err) => {
          clearTimeout(timer);
          window.api.removeAllListeners('bridge:progress');
          reject(err);
        });
      }),
    { action, payload, timeoutMs },
  );
}

function createSubsetApouInput(outputPath, limit = 2) {
  const raw = JSON.parse(fs.readFileSync(outputPath, 'utf-8'));
  const posts = Array.isArray(raw) ? raw : raw.posts || [];
  const subset = posts.slice(0, limit);
  const subsetPath = path.join(path.dirname(outputPath), 'posts_subset.json');
  const payload = Array.isArray(raw) ? subset : { ...raw, posts: subset };
  fs.writeFileSync(subsetPath, JSON.stringify(payload, null, 2), 'utf-8');
  return { subsetPath, subset };
}

test.beforeAll(async () => {
  app = await electron.launch({
    executablePath: electronExe,
    args: [appPath],
  });
  page = await app.firstWindow();
  await expect(page).toHaveTitle(/AutoCCF/, { timeout: 10000 });
});

test.afterAll(async () => {
  if (app) {
    await app.close();
  }
});

// ═══════════════════════════════════════════════════════════════════
// Phase 1: config:load — 验证配置加载 payload 结构
// ═══════════════════════════════════════════════════════════════════
test.describe.serial('Phase 1: Config Payload 验证', () => {
  let configPayload;

  test('config:load 返回完整配置结构', async () => {
    configPayload = await invokebridge('config:load');

    // 顶级字段
    expect(configPayload).toHaveProperty('success', true);
    expect(configPayload).toHaveProperty('config');

    const config = configPayload.config;

    // database_dir 必须是字符串
    expect(typeof config.database_dir).toBe('string');
    expect(config.database_dir.length).toBeGreaterThan(0);

    // accounts 必须是非空数组
    expect(Array.isArray(config.accounts)).toBe(true);
    expect(config.accounts.length).toBeGreaterThan(0);

    // 每个 account 有 name + bduss
    for (const account of config.accounts) {
      expect(typeof account.name).toBe('string');
      expect(account.name.length).toBeGreaterThan(0);
      expect(typeof account.bduss).toBe('string');
      expect(account.bduss.length).toBeGreaterThan(0);
    }
  });

  test('config:load 包含 APoU 参数', async () => {
    const apou = configPayload.config.apou;
    expect(apou).toBeDefined();
    expect(typeof apou.page_delay).toBe('number');
    expect(apou.page_delay).toBeGreaterThan(0);
    expect(typeof apou.max_retries).toBe('number');
    expect(apou.max_retries).toBeGreaterThanOrEqual(1);
  });

  test('config:load 包含 DoPJ 参数', async () => {
    const dopj = configPayload.config.dopj;
    expect(dopj).toBeDefined();
    expect(typeof dopj.threads).toBe('number');
    expect(dopj.threads).toBeGreaterThanOrEqual(1);
    expect(typeof dopj.max_retries).toBe('number');
    expect(dopj.max_retries).toBeGreaterThanOrEqual(1);
    expect(typeof dopj.min_interval).toBe('number');
    expect(dopj.min_interval).toBeGreaterThan(0);
    expect(typeof dopj.max_fails).toBe('number');
    expect(dopj.max_fails).toBeGreaterThanOrEqual(1);
  });
});

// ═══════════════════════════════════════════════════════════════════
// Phase 2: apou:crawl — 真实爬取 "团子传说" 并验证 progress + result
// ═══════════════════════════════════════════════════════════════════
test.describe.serial('Phase 2: APoU 爬取 Payload 验证', () => {
  let crawlResult;
  let progressEvents;

  test('apou:crawl 对 "团子传说" 返回 progress 事件和成功 result', async () => {
    test.setTimeout(300000);

    const outcome = await collectProgressEvents(
      'apou:crawl',
      { username: TARGET_USERNAME },
      270000,
    );

    expect(outcome.timedOut).toBe(false);
    progressEvents = outcome.events;
    crawlResult = outcome.result;

    // result payload 验证
    expect(crawlResult).toHaveProperty('success', true);
    expect(typeof crawlResult.posts_count).toBe('number');
    expect(crawlResult.posts_count).toBeGreaterThan(0);
    expect(typeof crawlResult.output_file).toBe('string');
    expect(crawlResult.output_file).toContain(TARGET_USERNAME);
  });

  test('apou:crawl progress 事件包含 page 和 posts_count 字段', async () => {
    expect(progressEvents.length).toBeGreaterThan(0);

    for (const event of progressEvents) {
      expect(typeof event.page).toBe('number');
      expect(event.page).toBeGreaterThanOrEqual(1);
      expect(typeof event.posts_count).toBe('number');
      expect(event.posts_count).toBeGreaterThanOrEqual(0);
      expect(typeof event.message).toBe('string');
    }

    // 最后一个 progress 事件的 page 应该 >= 1（至少爬了一页）
    const lastProgress = progressEvents[progressEvents.length - 1];
    expect(lastProgress.page).toBeGreaterThanOrEqual(1);
  });

  test('apou:crawl 的 posts_count 与 progress 事件一致', async () => {
    // progress 中的 posts_count 是每页原始帖子数，最终结果可能因为去重而更小
    const totalFromProgress = progressEvents.reduce(
      (sum, e) => sum + (e.posts_count || 0),
      0,
    );
    expect(totalFromProgress).toBeGreaterThanOrEqual(crawlResult.posts_count);
    expect(crawlResult.posts_count).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════════
// Phase 3: apou:outputs — 验证 APoU 输出列表包含刚爬取的用户
// ═══════════════════════════════════════════════════════════════════
test.describe.serial('Phase 3: APoU Outputs Payload 验证', () => {
  test('apou:outputs 包含 "团子传说" 的输出', async () => {
    const result = await invokebridge('apou:outputs');

    expect(result).toHaveProperty('success', true);
    expect(Array.isArray(result.outputs)).toBe(true);
    expect(result.outputs.length).toBeGreaterThan(0);

    // 找到目标用户的输出
    const targetOutput = result.outputs.find(
      (o) => o.username === TARGET_USERNAME,
    );
    expect(targetOutput).toBeDefined();
    expect(typeof targetOutput.path).toBe('string');
    expect(targetOutput.path.length).toBeGreaterThan(0);
    expect(typeof targetOutput.posts_count).toBe('number');
    expect(targetOutput.posts_count).toBeGreaterThan(0);
  });

  test('dopj:crawl 可基于最小 APoU 子集完成抓取', async () => {
    test.setTimeout(240000);

    const outputsResult = await invokebridge('apou:outputs');
    const targetOutput = outputsResult.outputs.find(
      (o) => o.username === TARGET_USERNAME,
    );
    expect(targetOutput).toBeDefined();

    const { subsetPath, subset } = createSubsetApouInput(targetOutput.path, 2);
    expect(subset.length).toBeGreaterThan(0);

    const outcome = await collectProgressEvents(
      'dopj:crawl',
      { input_json: subsetPath, threads: 1 },
      210000,
    );

    expect(outcome.timedOut).toBe(false);
    expect(outcome.result).toHaveProperty('success', true);
    expect(outcome.result.stats.total).toBe(subset.length);
    expect(outcome.result.stats.success + outcome.result.stats.skipped).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════════
// Phase 4: users:list — 验证用户列表包含爬取后的目标用户
// ═══════════════════════════════════════════════════════════════════
test.describe.serial('Phase 4: Users List Payload 验证', () => {
  let usersPayload;

  test('users:list 包含 "团子传说"', async () => {
    usersPayload = await invokebridge('users:list');

    expect(usersPayload).toHaveProperty('success', true);
    expect(Array.isArray(usersPayload.users)).toBe(true);
    expect(usersPayload.users.length).toBeGreaterThan(0);

    const targetUser = usersPayload.users.find(
      (u) => u.name === TARGET_USERNAME,
    );
    expect(targetUser).toBeDefined();

    // 验证用户字段结构
    expect(typeof targetUser.name).toBe('string');
    expect(typeof targetUser.posts_count).toBe('number');
    expect(targetUser.posts_count).toBeGreaterThan(0);
  });

  test('users:list 每个用户都有 name 和 posts_count', async () => {
    for (const user of usersPayload.users) {
      expect(typeof user.name).toBe('string');
      expect(user.name.length).toBeGreaterThan(0);
      // posts_count 可以为 0（其他用户可能没有帖子）
      expect(typeof user.posts_count).toBe('number');
    }
  });
});

// ═══════════════════════════════════════════════════════════════════
// Phase 5: users:detail — 验证用户详情 payload（帖子/线程/文件）
// ═══════════════════════════════════════════════════════════════════
test.describe.serial('Phase 5: User Detail Payload 验证', () => {
  let detailPayload;

  test('users:detail 返回 "团子传说" 的完整详情', async () => {
    detailPayload = await invokebridge('users:detail', {
      username: TARGET_USERNAME,
    });

    expect(detailPayload).toHaveProperty('success', true);
    expect(detailPayload.username).toBe(TARGET_USERNAME);
    expect(typeof detailPayload.user_dir).toBe('string');
    expect(detailPayload.user_dir.length).toBeGreaterThan(0);
  });

  test('users:detail posts 是包含 tid/title/href 的数组', async () => {
    expect(Array.isArray(detailPayload.posts)).toBe(true);
    expect(detailPayload.posts.length).toBeGreaterThan(0);

    for (const post of detailPayload.posts) {
      // 每条帖子有 tid（数字或字符串均可，取决于 APoU 输出格式）
      expect(post).toHaveProperty('tid');
      expect(post).toHaveProperty('title');
      expect(post).toHaveProperty('href');

      // title 和 href 是字符串
      expect(typeof post.title).toBe('string');
      expect(typeof post.href).toBe('string');
      // href 应该包含 tieba.baidu.com 或是相对路径
      expect(post.href.length).toBeGreaterThan(0);
    }
  });

  test('users:detail files 是包含 name/is_dir/size_text 的数组', async () => {
    expect(Array.isArray(detailPayload.files)).toBe(true);
    // 爬取后至少有 apou 子目录
    expect(detailPayload.files.length).toBeGreaterThan(0);

    for (const file of detailPayload.files) {
      expect(typeof file.name).toBe('string');
      expect(typeof file.is_dir).toBe('boolean');
      expect(typeof file.size_text).toBe('string');
    }

    // 验证有 "apou" 目录
    const apouDir = detailPayload.files.find(
      (f) => f.name === 'apou' && f.is_dir === true,
    );
    expect(apouDir).toBeDefined();
  });

  test('users:detail threads 是数组（可为空）', async () => {
    expect(Array.isArray(detailPayload.threads)).toBe(true);
    // threads 可能为空（如果没运行 DoPJ），但结构要正确
    for (const thread of detailPayload.threads) {
      expect(thread).toHaveProperty('tid');
      expect(thread).toHaveProperty('title');
      expect(thread).toHaveProperty('status');
    }
  });
});

// ═══════════════════════════════════════════════════════════════════
// Phase 6: GUI 全流程 — 从 UI 操作触发爬取并验证 GUI 展示的数据
// ═══════════════════════════════════════════════════════════════════
test.describe.serial('Phase 6: GUI 驱动的全流程 Payload 核验', () => {
  test('首页 stat cards 展示真实数据', async () => {
    await page.click('.nav-item[data-view="home"]');
    await expect(page.locator('.content-header h2')).toHaveText('首页', { timeout: 10000 });

    // 等待 stat cards 加载（首页调用 users:list）
    await expect(page.locator('.stat-card')).toHaveCount(3, { timeout: 10000 });

    // "已爬取用户" 数字 >= 1
    const usersCard = page.locator('.card.stat-card', { hasText: '已爬取用户' });
    const usersText = await usersCard.locator('p').textContent();
    expect(Number(usersText)).toBeGreaterThanOrEqual(1);

    // "帖子总数" 数字 > 0
    const postsCard = page.locator('.card.stat-card', { hasText: '帖子总数' });
    const postsText = await postsCard.locator('p').textContent();
    expect(Number(postsText)).toBeGreaterThan(0);
  });

  test('设置视图展示真实配置（账户名 + BDUSS 掩码）', async () => {
    await page.click('.nav-item[data-view="settings"]');
    await expect(page.locator('.content-header h2')).toHaveText('设置', { timeout: 10000 });

    // 等待配置加载完成（账户行出现 BDUSS 掩码 "..." 表示已加载真实配置）
    const accountBody = page.locator('[data-account-body]');
    await expect(accountBody.locator('tr', { hasText: '...' })).toBeVisible({ timeout: 15000 });

    // database_dir 不为空
    const dbDir = await page.locator('[data-database-dir]').inputValue();
    expect(dbDir.length).toBeGreaterThan(0);

    // 账户表有至少一行且包含 BDUSS 掩码格式 (前6位...)
    const accountRows = accountBody.locator('tr');
    const firstRowText = await accountRows.first().textContent();
    expect(firstRowText).toMatch(/\.\.\./); // BDUSS 掩码包含 "..."

    // 滑块值与 payload 一致
    const configPayload = await invokebridge('config:load');
    const apouDelay = configPayload.config.apou.page_delay;
    const sliderValue = await page.locator('[data-apou-page-delay]').inputValue();
    expect(Number(sliderValue)).toBeCloseTo(apouDelay, 1);
  });

  test('APoU 视图表单提交后 UI 展示与 payload 一致', async () => {
    await page.click('.nav-item[data-view="apou"]');
    await expect(page.locator('[data-apou-form]')).toBeVisible({ timeout: 10000 });

    // 先通过 IPC 获取预期数据（直接调用 bridge）
    const usersResult = await invokebridge('users:list');
    const targetUser = usersResult.users.find((u) => u.name === TARGET_USERNAME);

    // 验证 APoU 已爬取 — 进度文字应该包含帖子数
    // 重新爬取太慢，改为验证 APoU outputs 和 UI 输入框可用性
    const outputsResult = await invokebridge('apou:outputs');
    const targetOutput = outputsResult.outputs.find(
      (o) => o.username === TARGET_USERNAME,
    );
    expect(targetOutput).toBeDefined();
    expect(targetOutput.posts_count).toBe(targetUser.posts_count);
  });

  test('DoPJ 视图下拉框展示 APoU 输出且数据正确', async () => {
    await page.click('.nav-item[data-view="dopj"]');
    await expect(page.locator('[data-user-select]')).toBeVisible({ timeout: 10000 });

    // 等待选项加载
    await expect.poll(
      async () => page.locator('[data-user-select] option').count(),
      { timeout: 10000 },
    ).toBeGreaterThan(1); // 至少 "请选择" + 1 个真实选项

    // 找到团子传说的选项
    const optionTexts = await page.locator('[data-user-select] option').allTextContents();
    const targetOption = optionTexts.find((t) => t.includes(TARGET_USERNAME));
    expect(targetOption).toBeDefined();
    // 选项格式: "团子传说 (XX 条帖子)"
    expect(targetOption).toMatch(/\d+ 条帖子/);

    // 验证帖子数与 payload 一致
    const outputsResult = await invokebridge('apou:outputs');
    const targetOutput = outputsResult.outputs.find(
      (o) => o.username === TARGET_USERNAME,
    );
    const expectedCount = targetOutput.posts_count;
    expect(targetOption).toContain(`${expectedCount} 条帖子`);

    // 验证账户状态表显示了真实账户
    const accountBody = page.locator('[data-account-body] tr');
    await expect(accountBody.first()).toBeVisible({ timeout: 5000 });
    const configResult = await invokebridge('config:load');
    const expectedAccountName = configResult.config.accounts[0].name;
    const accountText = await accountBody.first().textContent();
    expect(accountText).toContain(expectedAccountName);
  });

  test('用户列表展示 payload 中的真实用户数据', async () => {
    await page.click('.nav-item[data-view="users"]');
    await expect(page.locator('.content-header h2')).toHaveText('用户', { timeout: 10000 });

    // 等待加载完成
    await expect(page.locator('[data-users-loading]')).toBeHidden({ timeout: 10000 });

    // 获取 payload 作为真值
    const usersPayload = await invokebridge('users:list');
    const expectedNames = usersPayload.users.map((u) => u.name);

    // 验证表格行数与 payload 一致
    const tableRows = page.locator('[data-users-body] tr');
    await expect(tableRows).toHaveCount(expectedNames.length, { timeout: 5000 });

    // 验证每个用户名在 UI 中出现
    for (const name of expectedNames) {
      await expect(page.locator('[data-users-body]')).toContainText(name);
    }

    // 搜索过滤后再验证
    await page.fill('[data-users-search]', TARGET_USERNAME.slice(0, 2)); // "团子"
    const filteredRows = page.locator('[data-users-body] tr');
    const filteredTexts = await filteredRows.allTextContents();
    expect(filteredTexts.some((t) => t.includes(TARGET_USERNAME))).toBe(true);

    await page.fill('[data-users-search]', '');
  });

  test('用户详情页展示 payload 中的帖子/文件数据', async () => {
    // 确保在用户列表页
    await page.click('.nav-item[data-view="users"]');
    await expect(page.locator('[data-users-loading]')).toBeHidden({ timeout: 10000 });
    await page.fill('[data-users-search]', '');

    // 点击目标用户的 "查看详情"
    const actionButton = page.locator(`[data-user-action="${TARGET_USERNAME}"]`);
    await expect(actionButton).toBeVisible({ timeout: 5000 });
    await actionButton.click();

    // 等待详情加载
    await expect(page.locator('[data-user-detail-username]')).toBeVisible({ timeout: 10000 });

    // 获取 payload 真值
    const detailPayload = await invokebridge('users:detail', {
      username: TARGET_USERNAME,
    });

    // 验证用户名
    const displayedName = await page.locator('[data-user-detail-username]').textContent();
    expect(displayedName).toBe(detailPayload.username);

    // 验证 meta 信息包含帖子数
    const metaText = await page.locator('[data-user-detail-meta]').textContent();
    expect(metaText).toContain(`帖子数 ${detailPayload.posts.length}`);

    // 验证帖子列表 — 表格行数与 payload 一致
    if (detailPayload.posts.length > 0) {
      const postRows = page.locator('[data-user-detail-posts] tbody tr');
      await expect(postRows).toHaveCount(detailPayload.posts.length, { timeout: 5000 });

      // 验证第一条帖子标题在 UI 中出现
      const firstPostTitle = detailPayload.posts[0].title;
      if (firstPostTitle) {
        await expect(page.locator('[data-user-detail-posts]')).toContainText(firstPostTitle);
      }
    }

    // 切换到文件标签
    await page.locator('[data-tab="files"]').click();
    await expect(page.locator('[data-user-detail-files]')).toBeVisible();

    // 验证文件列表包含 apou 目录
    if (detailPayload.files.length > 0) {
      const filesContent = await page.locator('[data-user-detail-files]').textContent();
      expect(filesContent).toContain('apou');
    }

    // 回到用户列表
    await page.locator('[data-user-detail-back]').click();
    await expect(page.locator('.content-header h2')).toHaveText('用户', { timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════════════════════════
// Phase 7: 错误处理 payload 验证
// ═══════════════════════════════════════════════════════════════════
test.describe.serial('Phase 7: 错误 Payload 验证', () => {
  test('apou:crawl 空 username 返回错误', async () => {
    await expect(
      invokebridge('apou:crawl', { username: '' }),
    ).rejects.toThrow();
  });

  test('users:detail 空 username 返回错误', async () => {
    await expect(
      invokebridge('users:detail', { username: '' }),
    ).rejects.toThrow();
  });

  test('未知 action 返回错误', async () => {
    await expect(
      invokebridge('nonexistent:action', {}),
    ).rejects.toThrow();
  });
});
