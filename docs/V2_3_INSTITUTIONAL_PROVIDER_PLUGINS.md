# v2.3 Institutional Provider Plug-ins

Future institutional data providers should plug in at `providers/institutional_provider.py`.

Implement `InstitutionalProvider` and return the provider-neutral dataclasses:

- `InstitutionalOwnership`
- `OwnershipTrend`
- `ThirteenFActivity`
- `InsiderActivity`
- `ShortInterest`

Then pass the adapter to `InstitutionalAnalyticsService(provider=adapter)` or to `CandidateDetailDataService(institutional_provider=adapter)`.

Provider-specific response parsing should stay inside the provider adapter. UI, Candidate Detail, and analytics code should consume only normalized models or the `InstitutionalAnalytics` metrics dictionary.

When no provider is configured, `NoInstitutionalProvider` is used and Candidate Detail displays `Provider not configured` without exceptions or fabricated data.
