# Branch Protection Configuration

To enable full NoOps automation, configure these branch protection rules for `master`.

## Required Settings

### 1. Navigate to Branch Protection

1. Go to: `https://github.com/thecturner/jankins/settings/branches`
2. Click "Add branch protection rule"
3. Branch name pattern: `master`

### 2. Required Status Checks

Enable: **✓ Require status checks to pass before merging**

Select these required checks:
- ✓ `Lint & Format Check`
- ✓ `Type Check`
- ✓ `Security Scan`
- ✓ `CodeQL Analysis`
- ✓ `Test Python 3.10`
- ✓ `Test Python 3.11`
- ✓ `Test Python 3.12`
- ✓ `CI Success`

Options:
- ✓ Require branches to be up to date before merging

### 3. Auto-Merge Settings

Enable: **✓ Allow auto-merge**

This allows the auto-merge workflows to merge PRs automatically after approval and passing CI.

### 4. Other Recommended Settings

Enable: **✓ Require a pull request before merging**
- Require approvals: `1`
- ✓ Dismiss stale pull request approvals when new commits are pushed
- ✓ Require approval of the most recent reviewable push

Enable: **✓ Require conversation resolution before merging**

Enable: **✓ Do not allow bypassing the above settings**

Disable: ❌ Allow force pushes
Disable: ❌ Allow deletions

## GitHub Permissions

Ensure the GitHub Actions bot has these permissions:

1. Go to: `https://github.com/thecturner/jankins/settings/actions`
2. Under "Workflow permissions":
   - ✓ Read and write permissions
   - ✓ Allow GitHub Actions to create and approve pull requests

## Repository Settings for Auto-Merge

1. Go to: `https://github.com/thecturner/jankins/settings`
2. Under "Pull Requests":
   - ✓ Allow auto-merge
   - ✓ Automatically delete head branches

## Dependabot Settings

1. Go to: `https://github.com/thecturner/jankins/settings/security_analysis`
2. Enable:
   - ✓ Dependency graph
   - ✓ Dependabot alerts
   - ✓ Dependabot security updates

## Verification

After configuration, test with a Dependabot PR:

1. Wait for Dependabot to create a PR (or trigger manually)
2. Check that auto-approve workflow runs
3. Check that CI runs and passes
4. Verify PR auto-merges after approval + passing CI

## Troubleshooting

### Auto-merge not working

**Problem**: PRs not auto-merging despite approval and passing CI

**Solutions**:
1. Verify "Allow auto-merge" is enabled in repository settings
2. Check workflow permissions (Read and write + approve PRs)
3. Ensure branch protection isn't blocking auto-merge
4. Check workflow logs for errors

### Auto-approve not working for Dependabot

**Problem**: Dependabot PRs not auto-approved

**Solutions**:
1. Check `dependabot-auto-approve.yml` workflow logs
2. Verify `GITHUB_TOKEN` has correct permissions
3. Ensure Dependabot metadata fetch is working
4. Check PR is from `dependabot[bot]` actor

### Semantic release not creating versions

**Problem**: Merges to master don't trigger version bumps

**Solutions**:
1. Verify commits use conventional commit format
2. Check commit types (`feat`, `fix`, `perf` trigger releases)
3. Review `semantic-release.yml` workflow logs
4. Ensure python-semantic-release is configured correctly
5. Check `GITHUB_TOKEN` can push commits and tags

### CI checks not required

**Problem**: PRs can be merged without CI passing

**Solutions**:
1. Go to branch protection settings
2. Enable "Require status checks to pass before merging"
3. Select all CI job names as required
4. Enable "Require branches to be up to date before merging"

## Quick Setup Script

Run this to verify your configuration:

```bash
# Check if auto-merge is enabled
gh repo view thecturner/jankins --json autoMergeAllowed

# Check branch protection rules
gh api repos/thecturner/jankins/branches/master/protection

# List required status checks
gh api repos/thecturner/jankins/branches/master/protection/required_status_checks

# Check workflow permissions
gh api repos/thecturner/jankins/actions/permissions
```

## Manual Override

Repository admins can always merge manually by:

1. Using "Squash and merge" button in GitHub UI
2. Using `gh pr merge <number> --squash` command

This bypasses auto-merge workflows but still respects branch protection.
