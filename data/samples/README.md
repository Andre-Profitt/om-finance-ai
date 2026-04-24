# Sample CMS data

These are **representative samples** for reproducible demos. They are hand-curated to match the schema and approximate price magnitude of the public CMS files. They are **not** the authoritative CMS files.

## Production path

The ingestion modules in `oaifinance.ingest.cms_asp` and `oaifinance.ingest.ndc_hcpcs` will attempt a live fetch from CMS when run with `--live` and fall back to these samples otherwise. For production or real demo use, run with `--live` to pull the current quarter's files from:

- ASP Drug Pricing Files: https://www.cms.gov/medicare/medicare-part-b-drug-average-sales-price/asp-pricing-files
- NDC-HCPCS Crosswalk: published alongside the ASP file each quarter

## Schema

### `cms_asp_sample.csv`

| Column                 | Type   | Notes                                               |
| ---------------------- | ------ | --------------------------------------------------- |
| hcpcs_code             | string | HCPCS Level II code (J-code for oncology biologics) |
| short_description      | string | CMS short description                               |
| dosage_per_unit_mg     | int    | mg per billable unit                                |
| payment_limit_per_unit | float  | Medicare payment limit in $ per unit                |
| effective_date         | date   | Quarter start                                       |
| biosimilar_reference   | bool   | Originator has biosimilar competition               |

### `ndc_hcpcs_sample.csv`

| Column                   | Type   | Notes                      |
| ------------------------ | ------ | -------------------------- |
| ndc_code                 | string | 11-digit NDC               |
| hcpcs_code               | string | HCPCS Level II code        |
| labeler_name             | string | Manufacturer               |
| brand_name               | string | Trade name                 |
| package_size_mg          | int    | mg per package             |
| billed_units_per_package | int    | billable units per package |

## Disclaimer

No PHI. No proprietary data. Prices are order-of-magnitude approximations of publicly referenced Medicare payment rates and should not be used for any actual billing, pricing, or reimbursement decision.
