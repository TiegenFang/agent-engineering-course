# Worktree workflow

本仓库的 ticket 工作区使用 git worktree 隔离在 `.worktrees/`（已被 `.gitignore` 排除）。为避免每个 worktree 重复安装约 300 MB 的 `node_modules`，工作区通过 Windows 目录 junction 共享主工作区的中央副本。

## 创建 ticket 工作区

```powershell
git worktree add .worktrees/<name> -b ticket-<n>
pwsh -NoProfile -Command "New-Item -ItemType Junction -Path '<repo>\.worktrees\<name>\node_modules' -Target '<repo>\node_modules'"
```

junction 无需管理员权限（等价于 `mklink /J`）。验证方式：在 worktree 的 `site/` 目录运行 `node -e "console.log(require.resolve('astro'))"`，应解析到主工作区的 `node_modules`。

## 移除 ticket 工作区

**顺序不可颠倒**：先用 `rmdir` 删除 junction 本身（只删链接、不碰目标），再移除 worktree。直接对含 junction 的目录做递归删除可能穿透链接误删中央 `node_modules`。

```powershell
cmd /c rmdir "<repo>\.worktrees\<name>\node_modules"
git worktree remove --force .worktrees/<name>
```

移除 worktree 不会删除分支；未合并的提交保留在本地分支上。

## 约束

- 只在主工作区运行 `npm install` / `npm update`：在 worktree 内安装会穿过 junction 改写中央副本，影响所有链接方。
- 只对与当前 `package-lock.json` 一致的分支使用 junction；依赖快照不同的历史分支如需实跑，应独立安装。
- `site/dist`、`site/.astro` 等构建产物按 worktree 各自生成，不做共享。
- 清理含未提交改动的工作区前，先把改动 commit 到该分支留档（`wip: preserve ...`），再按上述顺序移除。
