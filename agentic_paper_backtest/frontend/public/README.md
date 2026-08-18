# `frontend/public/` — Static assets

Most files here are committed normally. The Demo Hub usage tracker assets are **gitignored** because they come from an internal GitLab repo and should not be published to GitHub.

## Required tracker files (not in git)

Before building or deploying the frontend, place these three files in this directory:

- `usage-tracker-auto.bundle.min.js` (~104 KB)
- `usage-tracker-config.js`
- `terms.md`

## How to fetch them

```bash
# Requires a Midway-signed SSH key — see https://gitlab.pages.aws.dev/docs/Platform/ssh.html
git clone git@ssh.gitlab.aws.dev:guymor/demo-usage-tracker-client.git /tmp/demo-usage-tracker-client

cp /tmp/demo-usage-tracker-client/usage-tracker-auto.bundle.min.js \
   /tmp/demo-usage-tracker-client/terms.md \
   frontend/public/

# Use the project-specific config (production endpoint + registered demo ID), not the upstream one
# The committed template is at: frontend/public/usage-tracker-config.template.js
cp frontend/public/usage-tracker-config.template.js frontend/public/usage-tracker-config.js
```

## Wiring

- `app/layout.tsx` injects `<Script src="/usage-tracker-config.js" strategy="beforeInteractive">` and the bundle.
- `components/UsageTrackerInit.tsx` calls `new UsageTrackerAuto()` once the bundle has loaded.
- The tracker shows a Terms of Use modal on first load (`showTerms: true` in the config).

## Deployment notes

- Docker (`frontend/Dockerfile`) copies `public/` from the build context into the image, so the files must exist locally when running `frontend-deploy.sh`.
- If the files are missing the page still renders but the tracker silently fails to load (no ToS modal, no session tracked).
