# T30 科研进阶 API 结课：事实核验与原创边界

本 ticket 的产品事实边界在实现日（2026-08-13）按课程既有 T23/T26/T27/T28/T29 适配层和相应官方 API 资料复核。T30 不复制第三方代码或文字，也不执行真实 API 请求。

## 采用的事实边界

- API 调用是应用拥有的控制流：请求、工具调用、工具结果回填、结构化输出验证、预算和停止条件不能由 evidence 文本代替。
- live smoke 必须单独记录 provider、SDK、模型、日期、成本、权限和限制；没有执行就保持 `not-run`。
- 课程练习只使用合成设备遥测，不上传真实研究数据、凭据、prompt、tool payload、绝对路径或原始报告。

## 原创实现

`labs/research-api-capstone/`、`checker/course_check/research_api_capstone.py`、页面、组件、浏览器 fixture、测试和本说明均为课程原创。T30 只接管 `telemetry-quality-summary-v1` 一个步骤，预算计划固定为最多 2 次请求、96 output tokens 和 `$0.01` 教学上限；该计划不是供应商价格承诺。

## 未验证边界

未执行 OpenAI、Anthropic 或其他 provider 的 live request；未读取 API key；未运行 Codex/Claude Code 现场迁移；未把本地 fixture 结果描述为真实 API 或科研数据验收。发布前需由维护者重新核验当天官方文档、价格、模型、SDK 和权限行为。
