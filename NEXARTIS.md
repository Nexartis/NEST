# Nexartis Integration

This fork is maintained by [Nexartis](https://github.com/Nexartis) for [KnowYourModel](https://knowyourmodel.link) (KYM) NANDA integration work.

## About Nexartis

**[Nexartis](https://nexartis.com)** builds AI infrastructure for the agentic web:

- **[KnowYourModel](https://knowyourmodel.link)** — The trust registry for AI agents and models. Decentralized identity (DIDs), W3C Verifiable Credentials, usage-proof voting, and adaptive model selection. Integrated with the NANDA global agent discovery network.
- **[CubiCube](https://cubicube.app)** — Full-stack web application generation platform. Templated creation, automated deployment, and registry integration with split-sheet revenue attribution via the OCMECO model.
- **[Pegasus HB3](https://github.com/Nexartis/pegasus-hb3-engine)** — Horizon Breakthrough v3 build engine. Uses KYM's registry to dynamically select the best agents and models for each build task via multi-armed bandit algorithms (Thompson Sampling, UCB1, epsilon-greedy). Powers CubiCube's agentic build pipeline.

## Upstream
- Upstream: [projnanda/NEST](https://github.com/projnanda/NEST)

## Purpose
Testing and validating NANDA integration changes in Nexartis environments before contributing upstream.

## Branch Strategy
- `dev` — default branch (protected). All feature branches open PRs to `dev`. Code reviews are required before merge.
- `prod` — production branch (protected). PRs from `dev` → `prod` after code review and validation.
- Feature branches are created from `dev` for all work.
