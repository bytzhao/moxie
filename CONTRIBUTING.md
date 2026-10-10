# GITHUB.md — Commit Cheatsheet

Quick reference for writing good commits on this project. Skim this before you commit.

## Format

```
<type>(<scope>): <short summary>

<body>

<footer>
```

- **type** — required. See table below.
- **scope** — optional, parenthesized, names the part of the codebase touched: `(segmenter)`, `(db)`, `(api)`, `(frontend)`.
- **short summary** — imperative mood ("add", not "added"/"adds"), no trailing period, aim for under ~50 chars.
- **body** — optional, blank line before it. Explain *why*, not *what* — the diff already shows what changed.
- **footer** — optional. Breaking changes (`BREAKING CHANGE: ...`) or issue refs (`Closes #12`).

## Types

| Type | When to use it |
|---|---|
| `feat` | a new feature/capability |
| `fix` | a bug fix |
| `refactor` | code change that neither fixes a bug nor adds a feature |
| `docs` | documentation only |
| `test` | adding/correcting tests |
| `chore` | tooling, dependencies, config, non-code upkeep |
| `style` | formatting only (whitespace, semicolons) — no logic change |
| `perf` | performance improvement |

## Examples (from this repo's own history)

Before:
```
added regex to requirements for seg passage mandarin char strip
fmm & bmm modules completed
```

After:
```
fix(segmenter): add regex dependency for Mandarin char stripping
feat(segmenter): implement forward/backward maximum matching

Needed both directions to cross-validate segmentation
disagreements per PRD 0.3 §segmentation.
```

## Habits worth keeping

- **Atomic commits** — one logical change per commit. If you can't summarize it with one type + one line, it's probably two commits.
- **Imperative mood** — a commit message finishes the sentence "If applied, this commit will ___."
- **Body explains why, not what** — motivation, tradeoffs, context that won't be obvious from the diff in six months.
- **Wrap body text at ~72 chars** for readability in `git log` without `--stat`.

## Why bother

- `git log --oneline` becomes a real skimmable changelog.
- `git log --grep="^fix"` finds every bug fix instantly.
- Tools like `semantic-release` parse `feat`/`fix`/`BREAKING CHANGE` to auto-generate changelogs and version bumps, if you ever wire that up.
- It's the convention most teams/employers expect — good habit to build now.
