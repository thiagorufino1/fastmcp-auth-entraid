# Security Policy

## Supported versions

Only the latest commit on `main` receives security fixes. Fork the repository
and pin to a specific commit if you need a stable baseline.

## Reporting a vulnerability

If you believe you have found a security vulnerability in this project,
**do not open a public GitHub issue**. Instead, report it privately via one
of the channels below:

- **GitHub Security Advisories** (preferred):
  https://github.com/thiagorufino/fastmcp-auth-entraid/security/advisories/new
- **Email**: thiago.rufino@outlook.com (PGP key on request)

Please include, at minimum:

- A description of the vulnerability and its impact
- Reproduction steps or a proof-of-concept
- The commit hash and environment where you observed the issue
- Any suggested remediation, if available

You will receive an acknowledgement within **5 business days**. We aim to
provide a fix or risk acceptance within **30 days** of acknowledgement,
depending on severity.

## Scope

In scope:

- Authentication and authorization logic (`src/app/auth/*`)
- Token validation and claim handling
- The provisioning scripts under `scripts/`
- Container image build (`Dockerfile`)
- Dependency lock files (`requirements*.txt`)

Out of scope:

- Issues in third-party dependencies (report upstream; we will track via
  Dependabot or equivalent)
- Misconfiguration of an operator's Azure tenant (App Registration, group
  membership, conditional access)
- Social engineering, physical attacks, or denial-of-service against
  Microsoft Entra ID itself

## Coordinated disclosure

We commit to:

- Acknowledging your report
- Investigating and validating the issue
- Working with you on a coordinated public disclosure timeline
- Crediting you in the release notes unless you request anonymity

## Hardening references

Operational security guidance lives in:

- [`README.md`](README.md): section **Segurança**
- [`docs/architecture.md`](docs/architecture.md): trust boundaries
- [`docs/adr/`](docs/adr/): decision records (auth modes, App Roles, structlog, provisioning)
- [`scripts/provisioning.md`](scripts/provisioning.md): provisioning security notes
