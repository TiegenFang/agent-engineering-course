# T03 浏览器验收复现

T03 的公共页面合同测试和浏览器验收都从仓库依赖运行，不依赖全局 `npx` 缓存或开发者机器上的 `PLAYWRIGHT_MODULE_ROOT`。Playwright 版本固定为 `1.62.1`，依赖和完整性信息位于根目录 `package-lock.json`。

## Windows PowerShell 7

在仓库根目录执行：

```powershell
npm ci
npm run browser:install
npm run test:browser
```

根目录的 `npm run verify` 也会在 Python、Astro、构建和站点合同测试之后调用同一条 `npm run test:browser`，因此干净 checkout 的最高层验证包含 T02 证据闭环的 7 个站点测试、T03 合同和浏览器接缝。

`npm run test:browser` 会先构建 `site/dist`，然后由 `site/scripts/verify-directions.mjs` 启动一个只监听 `127.0.0.1:4321` 的 Node 静态服务器，运行结束自动关闭服务。它直接服务构建产物，不依赖全局 Astro/npx。若已有人工启动的 preview，可传入完整 URL 并跳过脚本托管：

```powershell
$env:T03_PREVIEW_URL = 'http://127.0.0.1:4321/agent-engineering-course'
npm run test:browser --workspace @agent-engineering-course/site
Remove-Item Env:T03_PREVIEW_URL
```

`npm run browser:install` 只安装 Playwright Chromium；浏览器二进制不进入 Git。首次安装需要网络和用户对 Playwright 浏览器缓存目录的写权限，浏览器验收不需要账号、API key、付费服务或真实研究数据。

验收脚本覆盖 T03 方向索引和三版 route 的 1440×900 桌面与 390×844 移动视口、横向溢出、跳过链接、控制台/page error、reduced-motion 模拟、正常文字对比度、风险说明文字对比度、焦点指示器对比度、可见交互目标最小 44px，以及索引卡片 hover/focus 对比度和三版方向的键盘交互。它还验证 Editorial tabs 的 Arrow/Home/End 与 `aria-labelledby`，以及 Evidence listbox 的方向感知 Arrow/Home/End、roving tabindex 和 READ/VERIFY 模式。

每次运行会更新 `artifacts/t03-screenshots/manifest.json`，记录 Node、Playwright、Chromium 版本、视口、每张截图的 SHA-256、控制台错误和验证结果。当前提交中的截图是在 Windows 环境、Node `v22.18.0`、Playwright `1.62.1` 与 Chromium `151.0.7922.34` 下生成；仓库 engines 声明仍要求 Node `>=22.19.0`，因此 Node 22.18.0 是本次实际验证的已知环境边界。
