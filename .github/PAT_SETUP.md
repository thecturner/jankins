# Personal Access Token Setup for Full NoOps Automation

To enable **100% automated releases** (from commit → PyPI), you need to create a GitHub Personal Access Token (PAT) that allows the semantic-release workflow to trigger the PyPI release workflow.

## Why is this needed?

GitHub's default `GITHUB_TOKEN` cannot trigger other workflows (security limitation). The semantic-release workflow needs to trigger the `release.yml` workflow to publish to PyPI, so it requires a PAT with workflow dispatch permissions.

## Setup Instructions

### 1. Create a Fine-Grained Personal Access Token

1. Go to GitHub Settings: https://github.com/settings/tokens?type=beta
2. Click **"Generate new token"** → **"Generate new token (fine-grained)"**
3. Fill in the details:
   - **Token name**: `jankins-release-automation`
   - **Expiration**: Choose your preference (90 days, 1 year, or no expiration)
   - **Repository access**: Select **"Only select repositories"** → Choose `jankins`
   - **Permissions** → Repository permissions:
     - **Actions**: Read and write ✅
     - **Contents**: Read and write ✅
4. Click **"Generate token"**
5. **Copy the token immediately** (you won't see it again!)

### 2. Add Token as Repository Secret

1. Go to your repository: https://github.com/thecturner/jankins/settings/secrets/actions
2. Click **"New repository secret"**
3. Fill in:
   - **Name**: `PAT_TOKEN`
   - **Secret**: Paste the token you copied
4. Click **"Add secret"**

### 3. Verify Setup

After adding the secret, the next commit with a `feat:` or `fix:` prefix will:

1. ✅ Semantic-release creates version commit and tag
2. ✅ Semantic-release triggers release.yml workflow
3. ✅ Release workflow publishes to PyPI
4. ✅ Release workflow creates GitHub release

## Testing

Push a test commit to verify the automation:

```bash
git commit --allow-empty -m "feat(ci): test full NoOps automation"
git push origin master
```

Then watch the workflows:
```bash
gh run list --limit 3
```

You should see:
1. Semantic Release workflow completes
2. Release workflow automatically triggers
3. Package appears on PyPI

## Security Notes

- The PAT has **minimal scope** (only this repo, only Actions + Contents)
- Consider setting an expiration date and setting a calendar reminder
- If the token expires, releases will still work but require manual triggering:
  ```bash
  gh workflow run release.yml --ref v<VERSION>
  ```

## Token Permissions Summary

| Permission | Access | Why Needed |
|------------|--------|------------|
| Actions | Read and write | Trigger release.yml workflow |
| Contents | Read and write | Push version commits and tags |

## Troubleshooting

### Token not working
- Verify token has correct permissions (Actions: Read and write, Contents: Read and write)
- Verify token is scoped to the `jankins` repository
- Verify secret name is exactly `PAT_TOKEN` (case-sensitive)

### Workflow still failing
- Check workflow logs: `gh run view --log`
- Verify the semantic-release workflow can read the secret
- Ensure token hasn't expired

## Alternative: Manual Trigger

If you prefer not to use a PAT, you can manually trigger releases:

```bash
# After semantic-release creates a tag (e.g., v1.3.0)
gh workflow run release.yml --ref v1.3.0
```

This gives you **95% NoOps** (only manual step is triggering PyPI publish).
