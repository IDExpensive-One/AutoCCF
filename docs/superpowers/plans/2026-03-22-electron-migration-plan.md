# AutoCCF Electron 薄壳迁移实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为 AutoCCF 引入一个安全的 Electron 桌面壳层，复用现有 Python 爬虫与配置能力，并通过 payload 回放完成可重复的桌面端验证。

**架构：** 现有 `gui/workers` 中的任务编排会先提取为独立 Python 服务层，再通过本地 Python facade 暴露给 Electron。Electron 采用 `main` / `preload` / `renderer` 三层结构，renderer 只能通过白名单 preload API 与本地 Python sidecar 交互。

**技术栈：** Python 3.10+、pytest、Electron、TypeScript、Playwright（Electron 模式）、本地 sidecar 进程管理。

---

## 文件分组

### Python 服务与接口
- 创建：`AutoCCF/services/__init__.py`
- 创建：`AutoCCF/services/apou_service.py`
- 创建：`AutoCCF/services/dopj_service.py`
- 创建：`AutoCCF/services/job_registry.py`
- 创建：`AutoCCF/electron_schemas.py`
- 创建：`AutoCCF/electron_facade.py`
- 创建：`AutoCCF/electron_server.py`
- 修改：`gui/workers/apou_worker.py`
- 修改：`gui/workers/dopj_worker.py`
- 可能修改：`gui_main.py`

### Electron 工程
- 创建：`package.json`
- 创建：`tsconfig.json`
- 创建：`electron/main.ts`
- 创建：`electron/preload.ts`
- 创建：`electron/common/contracts.ts`
- 创建：`electron/renderer/index.html`
- 创建：`electron/renderer/app.ts`
- 创建：`electron/renderer/styles.css`
- 创建：`electron/scripts/spawn-python.ts`
- 创建：`electron-builder.yml`

### 测试与夹具
- 创建：`tests/test_electron/test_service_contracts.py`
- 创建：`tests/test_electron/test_electron_server.py`
- 创建：`tests/test_electron/test_payload_replay.py`
- 创建：`tests/fixtures/electron/apou/basic.json`
- 创建：`tests/fixtures/electron/dopj/basic.json`
- 创建：`electron/tests/main.spec.ts`
- 创建：`electron/tests/preload.spec.ts`
- 创建：`electron/tests/e2e/apou-payload.spec.ts`
- 创建：`electron/tests/e2e/dopj-payload.spec.ts`

## 提交策略
- Commit 1：`test: define electron facade contracts and failing tests`
- Commit 2：`refactor: extract reusable crawler services from gui workers`
- Commit 3：`feat: add local python facade for electron`
- Commit 4：`feat: scaffold secure electron shell`
- Commit 5：`build: add electron and python sidecar packaging`
- Commit 6：`test: add payload-based electron e2e coverage`

## 任务 1：定义 Python / Electron 协议与失败测试
**文件：** `tests/test_electron/test_service_contracts.py`、`tests/test_electron/test_electron_server.py`、`tests/test_electron/test_payload_replay.py`、`AutoCCF/electron_schemas.py`、`electron/common/contracts.ts`
- [ ] 先写 Python 协议失败测试，覆盖无效用户名、非法路径、非法线程数等场景。
- [ ] 运行 `pytest tests/test_electron/test_service_contracts.py -q`，确认测试先失败。
- [ ] 再写 Electron preload 合同失败测试，确保只暴露白名单 API。
- [ ] 运行 `npm test -- electron/tests/preload.spec.ts`，确认测试先失败。
- [ ] 用最小 schema 与 DTO 结构让上述测试转绿。
- [ ] 只在两个目标测试文件通过后进入下一个任务。
- [ ] 完成后单独提交一次。

## 任务 2：提取可复用的 Python 服务层
**文件：** `AutoCCF/services/__init__.py`、`AutoCCF/services/apou_service.py`、`AutoCCF/services/dopj_service.py`、`AutoCCF/services/job_registry.py`、`gui/workers/apou_worker.py`、`gui/workers/dopj_worker.py`
- [ ] 先写 APoU / DoPJ 服务失败测试，覆盖启动、停止、进度和结果事件。
- [ ] 运行 `pytest tests/test_electron/test_service_contracts.py -q`，确认测试先失败。
- [ ] 提取服务层，让旧 worker 只负责 GUI 回调和 `app_state` 同步。
- [ ] 运行 `pytest tests/test_electron/test_service_contracts.py -q`。
- [ ] 串行运行 `pytest tests/test_apou/test_parser.py -q` 和 `pytest tests/test_dopj/test_task_manager.py -q`，确认没有破坏既有核心行为。
- [ ] 完成后单独提交一次。

## 任务 3：实现 Electron 可调用的 Python facade
**文件：** `AutoCCF/electron_facade.py`、`AutoCCF/electron_server.py`、`AutoCCF/electron_schemas.py`、`gui_main.py`
- [ ] 先写本地 facade / server 失败测试，覆盖配置读取、用户列表、APoU / DoPJ 启停和 job 查询。
- [ ] 运行 `pytest tests/test_electron/test_electron_server.py -q`，确认测试先失败。
- [ ] 实现仅限本机访问的 Python facade，并接入 replay 模式。
- [ ] 运行 `pytest tests/test_electron/test_electron_server.py -q`。
- [ ] 运行 `pytest tests/test_electron/test_payload_replay.py -q`。
- [ ] 两个目标测试都通过后再提交。

## 任务 4：搭建安全的 Electron 壳层
**文件：** `package.json`、`tsconfig.json`、`electron/main.ts`、`electron/preload.ts`、`electron/renderer/index.html`、`electron/renderer/app.ts`、`electron/renderer/styles.css`
- [ ] 先写主进程和 preload 失败测试，验证 `contextIsolation`、`nodeIntegration`、导航限制和 API 白名单。
- [ ] 运行 `npm test -- electron/tests/main.spec.ts`。
- [ ] 运行 `npm test -- electron/tests/preload.spec.ts`。
- [ ] 实现最小 Electron 工程骨架，只接入设置、APoU、DoPJ、用户列表的基本流程。
- [ ] 再次运行两个目标测试文件，确认通过后再提交。

## 任务 5：加入打包与开发启动编排
**文件：** `electron/scripts/spawn-python.ts`、`electron-builder.yml`、`package.json`
- [ ] 先写开发态 / 打包态 sidecar 路径解析失败测试。
- [ ] 运行 `npm test -- electron/tests/main.spec.ts`，确认测试先失败。
- [ ] 实现 sidecar 启动脚本、`process.resourcesPath` 路径解析和打包清单。
- [ ] 运行 `npm test -- electron/tests/main.spec.ts`。
- [ ] 运行 `npm run build`，确认构建退出码为 0。
- [ ] 通过后再提交。

## 任务 6：加入 payload 驱动的 Electron E2E
**文件：** `tests/fixtures/electron/apou/basic.json`、`tests/fixtures/electron/dopj/basic.json`、`electron/tests/e2e/apou-payload.spec.ts`、`electron/tests/e2e/dopj-payload.spec.ts`、`tests/test_electron/test_payload_replay.py`
- [ ] 先写 APoU 与 DoPJ 的 E2E 失败测试。
- [ ] 运行 `npm test -- electron/tests/e2e/apou-payload.spec.ts`，确认测试先失败。
- [ ] 补全 replay 夹具与最小页面流。
- [ ] 串行运行 `pytest tests/test_electron/test_payload_replay.py -q`。
- [ ] 串行运行 `npm test -- electron/tests/e2e/apou-payload.spec.ts`。
- [ ] 串行运行 `npm test -- electron/tests/e2e/dopj-payload.spec.ts`。
- [ ] 运行一次 `npm run build` 加 E2E 烟雾验证。
- [ ] 通过后单独提交。

## 完成定义
- Python 服务层已经从 Flet worker 中抽出，且旧 GUI 仍可复用它们。
- Electron renderer 只能通过 preload API 访问功能。
- Python facade 已能管理 APoU / DoPJ 任务、配置、用户列表和回放模式。
- 本地开发与打包场景都能启动 sidecar。
- 目标测试文件逐个串行通过，且未运行全量测试。
