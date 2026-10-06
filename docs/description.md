# Trivial APT Repository

The Trivial APT Repository is an internal Debian package publishing service for company-managed Ubuntu and Debian systems. Release engineers submit `.deb` files through `/app/repoctl.sh`; package names listed in `/app/approved.txt` enter the public pool, while other packages remain in quarantine. NGINX exposes repository metadata and approved packages on port 8080 for downstream APT clients.

## Services and capabilities

- The `default` publisher inspects package metadata, applies the exact-name approval list, and records every decision in `publish.log`.
- Approved files are stored under `public/pool`; quarantined files remain outside NGINX's public root.
- Indexing generates `Packages` and `Packages.gz` from the complete public pool so APT can discover available versions, architectures, dependencies, paths, sizes, and checksums.
- The `client` service represents a company machine configured to retrieve packages from `http://default:8080`.

## Key files

- `/app/repoctl.sh`: Publishes packages and rebuilds repository indexes.
- `/app/approved.txt`: Contains exact package names allowed into the public pool.
- `/app/restart.sh`: Validates, starts, or reloads NGINX and checks repository availability.
- `/app/nginx.conf`: Configures the public repository server on port 8080.
- `/app/fixtures/*.deb`: Provides ready-to-use sample packages for publication commands.
- `/var/lib/package-repository/public/`: Stores the public pool and generated indexes.
- `/var/lib/package-repository/quarantine/`: Stores packages that are not approved.
- `/var/lib/package-repository/publish.log`: Records publication decisions.

## Running the system

Run `/app/restart.sh` to validate and restart NGINX. Publish a fixture with `/app/repoctl.sh publish /app/fixtures/acme-agent-utils_1.0_all.deb`, or rebuild metadata with `/app/repoctl.sh index`. Verify availability with `curl --fail http://localhost:8080/Packages.gz`; on the `client` service, `apt-get update` refreshes the catalogue and `apt-get download PACKAGE` retrieves an approved package. No credentials or environment variables are required.
