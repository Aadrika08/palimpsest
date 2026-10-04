# Prepared draft PR handoff

The branches are pushed to `Aadrika08/palimpsest`, with repository-local commit
identity Aadrika Maurya <aadrikamaurya@gmail.com>. Main remains at
`ee6bf61ea8faec02d5522c7eee30ab7cf333f29d`. No merge occurred in this phase.

Draft PR creation is blocked: the available GitHub API connection identifies as
`pro-utkarshM`; the requested `Aadrika08` API credential is unavailable. SSH
branch pushes succeeded, but that does not establish an authenticated API actor.
No account was switched or PR submitted as another account.

| Scope | Pushed branch | Prepared body | Compare |
|---|---|---|---|
| Decisions and memory design | `research/phase-decisions` | [Body](pr-phase-decisions.md) | [Compare](https://github.com/Aadrika08/palimpsest/compare/main...research/phase-decisions) |
| Puck runner and evidence | `research/puck-fit-ladder` | [Body](pr-puck-fit-ladder.md) | [Compare](https://github.com/Aadrika08/palimpsest/compare/main...research/puck-fit-ladder) |
| Navigation runner and evidence | `research/nav-fit-ladder` | [Body](pr-nav-fit-ladder.md) | [Compare](https://github.com/Aadrika08/palimpsest/compare/main...research/nav-fit-ladder) |
| Complete phase and handoff | `research/capability-integration` | [Body](pr-capability-integration.md) | [Compare](https://github.com/Aadrika08/palimpsest/compare/main...research/capability-integration) |

The integration branch already contains the three lanes. Choose one integration
PR or separate lane PRs followed by the remaining readout; these are overlapping
review choices, not four independent changes to merge blindly.

With a CLI session already authenticated as **Aadrika08**, create the desired
draft from the integration checkout. The identity check must print `Aadrika08`
before submission; it does not itself switch accounts:

```bash
gh api user --jq .login
gh pr create --repo Aadrika08/palimpsest --base main --head research/capability-integration --draft --title 'Implement bounded capability-first research and retain failed probes' --body-file docs/reports/research-capability-execution/pr-capability-integration.md
```

For separate lane reviews, use these prepared submissions instead:

```bash
gh pr create --repo Aadrika08/palimpsest --base main --head research/phase-decisions --draft --title 'Retire memory v1 and specify decision-bearing v2 research' --body-file docs/reports/research-capability-execution/pr-phase-decisions.md
gh pr create --repo Aadrika08/palimpsest --base main --head research/puck-fit-ladder --draft --title 'Add guarded puck fitting ladder and retain failed probes' --body-file docs/reports/research-capability-execution/pr-puck-fit-ladder.md
gh pr create --repo Aadrika08/palimpsest --base main --head research/nav-fit-ladder --draft --title 'Add grouped navigation fitting probes and recovery readout' --body-file docs/reports/research-capability-execution/pr-nav-fit-ladder.md
```

Creating a draft does not authorize merging or further scientific work. Future
confirmation and memory-v2 implementation require their own frozen scope.
