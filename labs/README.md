# 设备遥测与报告工具

`labs` 将承载贯穿课程的合成设备遥测项目。模块 0 先提供一个不接触遥测数据的环境诊断脚本：

```powershell
pwsh -NoProfile -File .\labs\module-0\diagnose-environment.ps1
```

脚本只输出 `t05-environment` 的命令/版本/人工确认状态，供 `course_check` 生成既有匿名 evidence contract。当前 Alpha 切片仍只固定设备遥测项目边界；具体数据、CLI、测试和故障样例由后续纵向 ticket 加入。

这里不得加入真实敏感科研数据、企业数据、密钥或个人信息。

