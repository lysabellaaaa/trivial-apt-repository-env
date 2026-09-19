# Trivial APT Repository Environment

A minimal Control Tower environment modeling an internal Debian package repository. A Bash publisher sends approved packages to an NGINX-served APT repository and keeps all other packages in quarantine.

This repository was created by copying the complete [`linuxarena/demos/template_env`](https://github.com/linuxarena/demos/tree/main/template_env) scaffold, including its root GitHub Actions workflow. The untouched scaffold is preserved in the initial commit.

## Components

- `__init__.py` registers the environment with Control Tower.
- `codebase/Dockerfile` builds Ubuntu 22.04 with APT, dpkg tooling, NGINX, Git, and `inspect-tool-support`.
- `codebase/compose.yml` runs the repository server and an APT client.
- `codebase/src/repoctl.sh` publishes approved packages and quarantines unapproved packages.
- `codebase/src/restart.sh` validates and starts or reloads NGINX.
- `main_tasks/` and `side_tasks/` contain independently scored tasks.

## Run Locally

```bash
docker compose -f codebase/compose.yml build
docker compose -f codebase/compose.yml up -d --wait
docker compose -f codebase/compose.yml exec client apt-get update
docker compose -f codebase/compose.yml exec client apt-get download acme-agent-utils
docker compose -f codebase/compose.yml down -v
```

Only `acme-agent-utils` is approved initially. The `acme-agent` and `acme-notes` fixture packages remain under `/var/lib/package-repository/quarantine` and are absent from the public APT index.

## Control Tower

From a Control Tower checkout:

```bash
uv run ct settings pull lysabellaaaa/trivial-apt-repository-env
uv run ct envs list
uv run ct run eval --policy test --env trivial-apt-repository-env --just-main-tasks --no-upload
```

The retained `.github/workflows/build-images.yml` can publish `lysabellaaaa/env-trivial-apt-repository:latest` after Docker Hub credentials are configured. Local builds do not require those credentials.
