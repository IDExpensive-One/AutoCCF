# AutoCCF

AutoCCF is a Baidu Tieba data collection toolkit with a two-stage workflow for user post discovery and thread detail extraction.  
AutoCCF 是一个面向百度贴吧的数据采集工具集，采用“两阶段”流程，覆盖用户发言索引采集与帖子详情归档。

## Overview / 项目概览

AutoCCF is designed for controlled, reviewable data collection workflows. It separates fast user-level discovery from slower thread-level archival so teams can manage scope, credentials, and storage more carefully.  
AutoCCF 面向可控、可审计的数据采集流程设计。它将快速的用户级发现与较慢的帖子级归档拆分开来，便于团队更谨慎地管理采集范围、凭证和存储。

### Stage 1: APoU
- English: `APoU` (`All Posts of User`) collects a user's public posting index quickly.
- 中文：`APoU`（`All Posts of User`）用于快速获取用户公开发言索引。

### Stage 2: DoPJ
- English: `DoPJ` (`Detail of Posts JSON`) fetches detailed thread content from APoU output.
- 中文：`DoPJ`（`Detail of Posts JSON`）基于 APoU 输出进一步抓取帖子详情内容。

### Optional GUI
- English: An Electron desktop interface is available for operational workflows.
- 中文：项目提供可选的 Electron 桌面界面，用于图形化操作流程。

## Intended Use and Legal Boundary / 使用边界与合法授权

This repository is intended only for lawful research, learning, internal tooling, and other authorized data processing scenarios.  
本仓库仅适用于合法合规的研究、学习、内部工具建设及其他已获得授权的数据处理场景。

Before using this project, make sure all of the following are true:  
在使用本项目之前，请确保以下条件全部成立：

1. You have a lawful basis and sufficient authorization for the target data.  
   你对目标数据具备合法处理依据和充分授权。
2. Your use complies with applicable laws, platform terms, and privacy obligations.  
   你的使用方式符合适用法律、平台条款和隐私义务。
3. You collect only the minimum data necessary for the stated purpose.  
   你仅采集实现既定目的所必需的最小数据范围。
4. You define retention, access control, and deletion rules for collected data.  
   你已经为采集数据定义保留、访问控制和删除规则。
5. You do not use this project to bypass access restrictions, abuse controls, or platform security mechanisms.  
   你不会使用本项目绕过访问限制、风控机制或平台安全措施。

If any of the above cannot be satisfied, do not use this project.  
如果无法满足以上任一条件，请勿使用本项目。

## Privacy and Data Minimization / 隐私与数据最小化

Collected forum content may contain personal data, user-generated content, identifiers, or other sensitive context.  
采集到的论坛内容可能包含个人信息、用户生成内容、标识符或其他敏感上下文。

Recommended operating principles:  
建议遵循以下操作原则：

1. Minimize collection scope.  
   最小化采集范围。
2. Avoid collecting accounts, users, or threads unrelated to your approved purpose.  
   避免采集与你的授权目的无关的账户、用户或帖子。
3. Restrict internal access to raw outputs.  
   对原始输出实施最小权限访问控制。
4. Remove or anonymize sensitive data before redistribution.  
   在再次分发前删除或匿名化敏感数据。
5. Establish a deletion timeline for intermediate files and archived outputs.  
   为中间文件和归档输出建立明确的删除周期。

## Credential Security / 凭证安全

`BDUSS` is a high-risk credential and must be treated as a secret.  
`BDUSS` 属于高风险凭证，必须按密钥级别进行保护。

Security requirements:  
安全要求：

1. Never commit, publish, or paste a real `BDUSS` into issue trackers, chat logs, or screenshots.  
   不要在 issue、聊天记录、截图或代码仓库中提交、公开或粘贴真实 `BDUSS`。
2. Use dedicated accounts for testing whenever possible.  
   在可能的情况下使用专用测试账号。
3. Rotate or revoke credentials immediately after suspected exposure.  
   一旦怀疑泄露，应立即轮换或吊销凭证。
4. Store credentials only in local configuration files or approved secret stores.  
   仅在本地配置文件或受控密钥管理系统中保存凭证。

## Files That Must Not Be Committed / 严禁提交的文件

The following files must never be committed to the repository:  
以下文件严禁提交到仓库：

- `DoPJ/config/config.json`
- `**/bduss.txt`
- `**/tieba_auth.json`
- `*_posts.json` except sanitized examples
- Raw archive outputs under `database/`, `posts/`, or similar runtime directories

Repository maintainers should verify this before every push or PR.  
维护者应在每次推送或提交 PR 前对此进行检查。

## Architecture / 架构说明

```text
AutoCCF/
├── APoU.py
├── APoU/
├── DoPJ/
├── AutoCCF/
├── electron/
├── tests/
├── README.md
└── requirements.txt
```

### APoU / 用户发言索引采集
- English: Retrieves a user's posting index quickly and writes a JSON list for downstream use.
- 中文：快速获取用户发言索引，并输出供后续处理使用的 JSON 列表。

### DoPJ / 帖子详情抓取
- English: Reads APoU output and fetches detailed thread content with retry and concurrency controls.
- 中文：读取 APoU 输出，在重试与并发控制下进一步抓取帖子详情内容。

### Electron GUI / 桌面界面
- English: Provides a GUI wrapper around the project workflow for local operation.
- 中文：为本地使用提供图形界面封装。

## Quick Start / 快速开始

### Prerequisites / 环境要求

- Python `3.10+`
- A working network connection to required upstream services
- Optional: Node.js and npm for the Electron GUI

### Python Environment / Python 环境准备

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Stage 1: Run APoU / 运行 APoU

```bash
python APoU.py -u <用户名>
```

Expected result: a user post index file suitable for downstream processing.  
预期结果：生成可供后续处理的用户发言索引文件。

### Stage 2: Run DoPJ / 运行 DoPJ

```bash
cd DoPJ
python DoPJ.py -i ../<用户名>_posts.json -c config/config.json -t 3
```

Expected result: detailed thread data and related output files under the configured output directory.  
预期结果：在配置的输出目录下生成帖子详情数据及相关输出文件。

### Optional GUI / 可选桌面端

```bash
cd electron
npm install
npm start
```

## Output and Storage / 输出与存储

Typical runtime output structure:  
典型运行时输出结构如下：

```text
database/
└── <username>/
    ├── apou/
    │   └── posts.json
    └── dopj/
        ├── index.json
        └── <tid>/
```

Output paths may vary depending on configuration and legacy compatibility paths.  
实际输出路径可能因配置和旧版兼容路径而有所不同。

All collected outputs should be treated as controlled data assets.  
所有采集输出都应视为受控数据资产进行管理。

## Validation and Testing / 验证与测试

### Basic syntax checks / 基础语法检查

```bash
python -m py_compile APoU.py
python -m py_compile DoPJ/DoPJ.py
```

### Representative module checks / 代表性模块检查

```bash
python -c "from APoU import UserPostsCrawler; print('APoU module OK')"
cd DoPJ
python -c "from utils.url_parser import parse_tieba_url; print(parse_tieba_url('https://tieba.baidu.com/p/123?pid=456'))"
```

### Optional UI E2E / 可选界面端到端测试

```bash
npx playwright test tests/test_ui/test_payload_e2e.js -g "Phase 2: APoU"
```

## Collaboration and Review / 协作与审查

For contribution and review standards, see the following documents:  
关于贡献和审查规范，请参考以下文档：

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [PRE_UPLOAD_CHECKLIST.md](PRE_UPLOAD_CHECKLIST.md)
- [CHANGELOG.md](CHANGELOG.md)

Recommended pull request expectations:  
建议的 Pull Request 要求：

1. State scope clearly.  
   明确说明变更范围。
2. List validation commands actually executed.  
   列出实际执行过的验证命令。
3. Confirm no secrets or runtime data were included.  
   确认未包含密钥或运行时数据。

## Known Limitations / 已知限制

1. Upstream API behavior may change without notice.  
   上游 API 行为可能在无通知情况下发生变化。
2. Platform risk control may reduce crawl success rate.  
   平台风控可能降低抓取成功率。
3. Large-scale collection can be sensitive from both compliance and operational perspectives.  
   大规模采集在合规和运维层面都具有较高敏感性。

## License / 许可证

This project is licensed under the [MIT License](LICENSE).  
本项目采用 [MIT License](LICENSE) 许可协议。

## Final Notice / 最终提示

Use this project only within authorized, reviewable, and compliant boundaries.  
请仅在获得授权、可接受审计且符合合规要求的边界内使用本项目。

Perform legal, privacy, and security review before any production or organization-wide deployment.  
在任何生产环境或组织级部署之前，请先完成法务、隐私和安全审查。
