# mistral

Mistral Studio -työtilan workflow-projektit.

## apps/worker — aamuraportti (`morning-report`)

Workflow, joka ajetaan joka aamu klo 5 Suomen aikaa (ajastus: cron `0 5 * * *`, aikavyöhyke `Europe/Helsinki`, luodaan Studion ajastuksena). Se tuottaa suomenkielisen raportin, joka näkyy Studion workflow-ajojen tuloksena:

- **Kuopion säätila** — Open-Meteo-rajapinta (ei vaadi API-avainta): nykyhetki ja seuraavat 12 tuntia.
- **USA:n tärkeimmät tapahtumat edellisten 12 tunnin ajalta** — uutis-RSS-syötteet (NYT, Washington Post, ABC, CBS, BBC, Guardian, AP, Reuters, CNN, NPR), suodatettu julkaisuajan mukaan; Mistral-malli tiivistää raportiksi suomeksi.

### Rakenne

```
apps/worker/
├── Dockerfile            # managed deployment -imagen build (build context: apps/worker)
├── pyproject.toml / uv.lock
├── src/worker/
│   ├── entrypoints/worker.py   # worker-päätepiste: discover_all_workflows_in_package + run_worker
│   └── workflows/morning_report.py
└── tests/                # pytest: yksikkötestit + päästä-päähän -testi (Temporal test env, activityt stubattu)
```

### Kehitys

```bash
cd apps/worker
uv sync --all-groups
uv run pytest
```

### Deployment

Managed deployment rakennetaan tästä GitHub-reposta (build directory `apps/worker`, Dockerfile `Dockerfile`). Julkaise muutokset PR:nä, deployaa pushattu commit, ja luo ajastus Studiossa (`create_workflow_schedule`, cron `0 5 * * *`, `time_zone_name: Europe/Helsinki`).
