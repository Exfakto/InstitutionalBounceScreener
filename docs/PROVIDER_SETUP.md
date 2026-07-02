# Premium Provider Setup

This guide explains how to configure optional premium providers and run safe local smoke tests. Provider setup is optional; the application remains local-first and uses the local provider by default.

## Supported Providers

- Polygon.io: price history
- Financial Modeling Prep: company profile, fundamentals, earnings, institutional metrics, insider activity
- Finnhub: company profile, earnings, insider activity
- SEC EDGAR: institutional metrics and insider filings, no API key required

Premium provider coverage is foundational and may expand over time. Do not assume every endpoint is implemented for every provider.

## API Keys

Store API keys only in environment variables. Never commit API keys, paste them into config files, or include them in screenshots, logs, issue reports, or test fixtures.

PowerShell examples:

```powershell
$env:POLYGON_API_KEY = "your-polygon-key"
$env:FMP_API_KEY = "your-fmp-key"
$env:FINNHUB_API_KEY = "your-finnhub-key"
```

For a persistent user-level variable:

```powershell
[Environment]::SetEnvironmentVariable("POLYGON_API_KEY", "your-polygon-key", "User")
[Environment]::SetEnvironmentVariable("FMP_API_KEY", "your-fmp-key", "User")
[Environment]::SetEnvironmentVariable("FINNHUB_API_KEY", "your-finnhub-key", "User")
```

Open a new terminal after setting persistent environment variables.

## Provider Config

Provider selection is controlled by `config/providers.json`.

Default local-first config:

```json
{
  "active_provider": "local",
  "providers": {
    "local": {
      "enabled": true
    },
    "polygon": {
      "enabled": false,
      "api_key_env": "POLYGON_API_KEY"
    }
  }
}
```

Keep secrets out of this file. Store only provider names, enablement flags, and environment variable names.

Example expanded config:

```json
{
  "active_provider": "local",
  "providers": {
    "local": {
      "enabled": true
    },
    "polygon": {
      "enabled": true,
      "api_key_env": "POLYGON_API_KEY"
    },
    "fmp": {
      "enabled": true,
      "api_key_env": "FMP_API_KEY"
    },
    "finnhub": {
      "enabled": true,
      "api_key_env": "FINNHUB_API_KEY"
    },
    "sec": {
      "enabled": true
    }
  }
}
```

## Smoke Tests

The smoke-test harness is safe by default. Without `--live`, it does not perform network calls.

Dry run all providers:

```powershell
python tools/provider_smoke_test.py --provider all --ticker AAPL
```

Dry run one provider:

```powershell
python tools/provider_smoke_test.py --provider polygon --ticker AAPL
```

Live smoke test one provider:

```powershell
python tools/provider_smoke_test.py --provider polygon --ticker AAPL --live
```

Live smoke test all providers:

```powershell
python tools/provider_smoke_test.py --provider all --ticker AAPL --live
```

Live mode performs one safe request per selected provider:

- Polygon: price history
- FMP: company profile
- Finnhub: company profile
- SEC EDGAR: institutional metrics

The harness prints only `Configured` or `Not Configured` for API keys. It never prints key values.

## Troubleshooting

If a provider reports `Not Configured`, verify the matching environment variable is available in the current PowerShell session:

```powershell
Get-ChildItem Env:POLYGON_API_KEY
Get-ChildItem Env:FMP_API_KEY
Get-ChildItem Env:FINNHUB_API_KEY
```

If a live smoke test fails:

- Confirm the provider is enabled in `config/providers.json` if testing through application provider flows.
- Confirm the key has the required provider subscription and endpoint permissions.
- Confirm the ticker is valid and supported by the provider.
- Retry later if the message indicates rate limiting.
- Check local network and firewall settings.

If SEC EDGAR fails:

- Confirm the ticker has an SEC CIK mapping.
- Retry later if SEC throttling or temporary availability is suspected.

## Security Checklist

- Do not commit API keys.
- Do not store API keys in `config/providers.json`.
- Do not hardcode API keys in source or tests.
- Use mocked provider responses in tests.
- Use dry-run smoke tests before live tests.
- Review `git diff` before commits to confirm no secrets are present.
