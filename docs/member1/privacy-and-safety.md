# Privacy and Safety Notes

- The ML dataset generator creates synthetic development data. Never label it as real patient data.
- The API currently uses numeric user IDs without authentication or authorization. Do not expose it to the public internet or real users until identity, ownership checks, and access controls are implemented.
- Do not log health request/response bodies. Android network logging is set to BASIC in debug and disabled in release.
- Keep `.env`, API keys, local machine configuration, and signing credentials out of Git.
- Health insights are observational and not diagnostic. Avoid deterministic disease claims. High statistical deviations should prompt measurement verification and appropriate professional guidance, not automated diagnosis.
- Production deployments require HTTPS, strict CORS, secrets management, database migrations, backups, retention controls, and a privacy review.
