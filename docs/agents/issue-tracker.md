# Issue tracker: GitHub

Issues and specs for this repository live in GitHub Issues at `TiegenFang/agent-engineering-course`. Use the `gh` CLI for tracker operations.

## Conventions

- Create an issue with `gh issue create --repo TiegenFang/agent-engineering-course`.
- Read an issue with `gh issue view <number> --repo TiegenFang/agent-engineering-course --comments` and include its labels.
- List issues with `gh issue list --repo TiegenFang/agent-engineering-course`, adding state and label filters appropriate to the task.
- Comment with `gh issue comment <number> --repo TiegenFang/agent-engineering-course`.
- Apply or remove labels with `gh issue edit <number> --repo TiegenFang/agent-engineering-course`.
- Close an issue with `gh issue close <number> --repo TiegenFang/agent-engineering-course` and leave a concise completion comment when useful.
- For a multiline issue body, use `--body-file` with a reviewed Markdown file. Do not rely on Bash heredocs or shell redirection.
- Keep the explicit `--repo` argument until this working directory is connected to the GitHub remote.

## Pull requests as a triage surface

**PRs as a request surface: no.** External pull requests are not treated as feature requests by the triage workflow. This flag can be changed here later if the repository adopts that convention.

## Skill vocabulary

- When a skill says “publish to the issue tracker,” create a GitHub issue in this repository.
- When a skill says “fetch the relevant ticket,” read the referenced GitHub issue and its comments and labels.
- GitHub shares one number space across issues and pull requests; resolve an ambiguous number before mutating it.
