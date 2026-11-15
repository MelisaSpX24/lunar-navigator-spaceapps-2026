
# TEAM 24&28 — Lunar Landing Site Navigator

**Explore the Moon. Evaluate the Conditions. Find a Better Site.**

NASA Space Apps Challenge 2026 research prototype connecting NASA SPICE geometry and LOLA terrain evidence to an interactive lunar operation planning workflow.

## Explore the project

- [Seven-slide English presentation](frontend/COMMAND_14_JURY_DECK.pdf)
- [Submission description and AI disclosure](frontend/COMMAND_14_SPACE_APPS_SUBMISSION.md)
- [Scientific audit](backend/TEAM_24_28_COMMAND_13_SCIENTIFIC_AUDIT.md)
- [Frontend setup](frontend/README.md) · [Backend setup](backend/README.md)

React/TypeScript, Three.js and React Three Fiber provide a global lunar globe, observer-centered angular horizon, synchronized Sun/Earth samples and UTC playback.

A Python/FastAPI backend evaluates sampled visibility and explicit operation requirements. Bounded local and temporal optimizers compare nearby coordinates or alternative starts through source-aware A/B comparisons.

SQLite jobs and source-bound checkpoints support durable results, cancellation and explicit resume.

## Run the recorded demonstration

With Node 24 and npm installed:

```bash
cd frontend
npm ci
npm run build
npm run preview -- --host 127.0.0.1 --port 4173 --strictPort
```

Open http://127.0.0.1:4173/#/alternatives and keep **Recorded Evidence**.

Recorded evidence works without a backend or internet at runtime after setup.

The six-hour temporal and one-hour, 5 km local packages are separate studies; they are not fresh calculations.

Live computation requires separately configured NASA resources; no kernel binaries, DEM rasters or private job database are included.

## Scientific scope

This is a research prototype, not certified landing software. `science_ready=false`.

Absolute DEM registration is UNVERIFIED; configuration-equivalent Horizons validation is INCOMPLETE.

Sampled visibility does not guarantee physical continuity, power generation or radio-link success.

The planning index is not success probability. Historical Local8 (6 MET / 2 NOT_MET) and Temporal4 (2 MET / 2 NOT_MET) are finite PARTIAL searches, not global optima.

No NASA endorsement is implied. The local scientific worker/API is not a hardened public multi-tenant service.

## License and credits

Original team-authored code is licensed under [Apache License 2.0](LICENSE), with approval from both team members.

NASA imagery/data, dependencies and fonts retain their own rights; Apache does not relicense them or grant trademark rights.

See [NOTICE](NOTICE) and [third-party attributions](THIRD_PARTY_ATTRIBUTIONS.md).

Historical validation documents retain their original dates, test scopes and private-development references. Their earlier license/publication-pending notes are superseded by this public source distribution.

ChatGPT/Codex assisted implementation, tests and documentation; the team reports a Claude gap review.

Scientific outputs come from deterministic backend models, not AI-generated science.
