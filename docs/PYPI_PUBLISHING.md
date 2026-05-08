# Publishing falsify-eval to PyPI

The `.github/workflows/publish.yml` workflow builds and publishes the package
to PyPI on every `v*` tag push. It uses **OIDC trusted publishing** — no API
tokens stored as repository secrets — so the only one-time setup is on the
PyPI side.

## One-time setup (Parth, ~10 minutes)

1. **Create a PyPI account** at https://pypi.org/account/register/.
   Verify email, enable 2FA (TOTP — use the same authenticator you use for
   GitHub).

2. **Add the pending trusted publisher** at
   https://pypi.org/manage/account/publishing/.
   Click "Add a new publisher" → GitHub, then fill in:

   ```
   PyPI Project Name : falsify-eval
   Owner             : spalsh-spec
   Repository name   : falsify-eval
   Workflow filename : publish.yml
   Environment name  : pypi
   ```

   Save. The publisher will be marked "pending" until the first publish
   succeeds, at which point it becomes a permanent trusted publisher
   for the project.

3. **Create the GitHub Actions environment** at
   https://github.com/spalsh-spec/falsify-eval/settings/environments.
   Click "New environment", name it `pypi` (must match the workflow's
   `environment.name`), save. No secrets needed inside the environment —
   the workflow's OIDC token is what authenticates.

   Optionally: add yourself as a required reviewer for the `pypi`
   environment so each release requires manual approval before publish.
   Recommended for a first publish; can be removed later.

## Releasing a new version

Every release is a single command sequence — no API token to remember,
no `twine upload`:

```bash
# 1. Bump version in BOTH places (the test_d7_version_sync guard catches drift)
#    falsify_eval/__init__.py:  __version__ = "0.1.6.10"
#    pyproject.toml:            version = "0.1.6.10"

# 2. Update CHANGELOG.md with a new section header

# 3. Run the full suite — must be green before tagging
python3 -W error::SyntaxWarning -m pytest tests/

# 4. Commit, tag, push (the publish workflow triggers on the tag)
git add -A
git commit -m "release: v0.1.6.10 — <one-line summary>"
git tag -a v0.1.6.10 -m "v0.1.6.10 — <one-line summary>"
git push origin main --follow-tags
```

The publish workflow will:
1. Build sdist + wheel
2. Run `twine check` to validate METADATA renders on PyPI
3. Verify the tag matches `falsify_eval.__version__` (catches typos)
4. Upload via OIDC trusted publishing
5. Make the release visible at https://pypi.org/project/falsify-eval/

After publish, anyone can install with the canonical one-liner:

```
pip install falsify-eval
```

## Local pre-flight (optional, before tagging)

```bash
# Build locally and validate
rm -rf dist build *.egg-info
python3 -m build
python3 -m twine check dist/*

# Inspect the wheel — should contain only falsify_eval/* and dist-info/
unzip -l dist/falsify_eval-*.whl

# Test install from the local wheel in a fresh venv
python3 -m venv /tmp/feval-test
/tmp/feval-test/bin/pip install dist/falsify_eval-*.whl
/tmp/feval-test/bin/falsify-eval doctor
```

If `doctor` exits clean against the local wheel, the PyPI publish will
work too — the wheel that goes to PyPI is byte-identical to the one CI
just validated.

## What if publish fails?

Common modes and fixes:

- **"trusted publisher not configured"** — step 2 above is incomplete or
  the workflow filename / environment name doesn't match exactly. Check
  the PyPI publishing settings page.

- **"version already exists"** — PyPI does not allow overwriting an
  existing version. Bump the patch number, retag, push.

- **"description content-type missing"** — `twine check` would have caught
  this in step 2 of the workflow; it indicates a malformed README. Ensure
  `pyproject.toml`'s `readme` field points to a valid file.

- **"tag does not match package version"** — the workflow's version-sync
  step caught a bump-one-place-not-the-other mistake. Bump both, retag.
