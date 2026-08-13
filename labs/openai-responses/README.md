# 模块 11B：OpenAI Responses API 适配实验

本实验把模块 11A（T26）的 Python 最小 Agent loop 接到一个官方
Responses API/SDK 的**适配边界**。循环仍由应用拥有：T26 决定工具执行、
状态回填、重试和 `max_steps`；本目录只把 `client.responses.create(...)` 的
function call 或最终 JSON 转成 T26 的 `FixtureResponse` 形状。

## 离线主路径：不需要 SDK、账号或 API key

先在课程工作区根目录运行确定性夹具。它使用录制的假 `responses.create`
端点，不读取 `OPENAI_API_KEY`，不安装 SDK，也不会产生网络请求：

```powershell
python .\labs\openai-responses\run_fixture.py --output .\t27-openai-responses-fixture.json
Set-Location -LiteralPath .\checker
python -m course_check check t27-openai-responses --root .. --evidence-file ..\t27-openai-responses-fixture.json --output ..\t27-openai-responses-checked.json --json
Get-Content -LiteralPath ..\t27-openai-responses-checked.json
```

夹具覆盖四条状态路径：成功的 function call/output 回填、无效工具参数、
不符合 JSON 的 structured output，以及 SDK 风格连接错误。导出的 evidence
只包含稳定的状态、计数、模型标识和 `not-run` 现场边界；它不包含 prompt、
工具参数、原始模型文本、路径、读数或凭据。

## T26 注入点

`ResponsesResponseSource` 实现 `respond(state)`，并可通过下列方式交给
T26 的 loop：

```python
from agent_loop import FixtureResponse, run_agent_loop
from openai_responses_adapter import ResponsesResponseSource, create_live_openai_client

client = create_live_openai_client(api_key)  # 仅在人工批准的现场测试中调用
source = ResponsesResponseSource(client, response_factory=FixtureResponse)
result = run_agent_loop(
    "success",
    response_source=source,
    tool_executor=telemetry_tool,
    max_steps=4,
    retry_budget=1,
)
```

上面是适配示意，不是本课执行步骤。T26 的离线 fixture/evidence schema 不会
因接入 SDK 而被改写；本目录的 `run_fixture.py` 也不会构造 live client。

## 可选现场 smoke：本轮未执行

真实请求有账号、凭据、网络和潜在计费副作用，必须由学员在自己的项目中
批准后再做。现场记录至少应写明：实际 `openai` SDK 版本、模型 ID、日期、
一次请求的成本/用量观察、项目权限、失败类别和限制。不要把 API key、完整
prompt、原始响应、研究数据或个人路径放进课程 evidence。

当前 `live_smoke` 元数据固定为 `status: not-run`；它说明本课**没有**做真实
API 调用，不能替代现场验收。
