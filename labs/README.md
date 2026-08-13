# 设备遥测与报告工具

`labs` 将承载贯穿课程的合成设备遥测项目。模块 0 先提供一个不接触遥测数据的环境诊断脚本：

```powershell
pwsh -NoProfile -File .\labs\module-0\diagnose-environment.ps1
```

脚本只输出 `t05-environment` 的命令/版本/人工确认状态，供 `course_check` 生成既有匿名 evidence contract。当前 Alpha 切片仍只固定设备遥测项目边界；具体数据、CLI、测试和故障样例由后续纵向 ticket 加入。

当前已加入 `agent-loop/` 的 Agent loop 合同和 `agent-instructions/` 的指令工程对照合同；真实数据、CLI 和设备接入不属于这些浏览器夹具。

- `agent-loop/`：模块 1 的确定性响应—工具—停止 trace。
- `agent-instructions/`：模块 2 的模糊/工程化指令、冲突、提示注入、过长预算和迁移输入。

这里不得加入真实敏感科研数据、企业数据、密钥或个人信息。

