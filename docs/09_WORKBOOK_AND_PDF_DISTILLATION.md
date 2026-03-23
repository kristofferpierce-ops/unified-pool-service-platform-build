# Workbook and PDF distillation

## PDF 1: Connector-First Unified Operating Core for a Pool Service Business

- pages: 9

- establishes active baseline assignment
- confirms platform_v3 as main backbone
- confirms pricing_v1 and volume tool are selective mines
- marks RPC Root as unrelated
- marks the chemistry workbook as deterministic model source


## PDF 2: AI-Friendly Rollout Plan for a Connector-First Unified Pool Service Operations Core

- pages: 27

- locks in phased rollout
- puts Postgres and Alembic before connector expansion
- makes invoice ingestion the first generalized staged-ingestion refactor
- puts deterministic chemistry and variance before Bayesian work
- sequences connectors as intake, then billing, then operations, then Heritage


## Workbook summary

### Start Here
- size: 19 rows x 5 columns
- preview:

  - ['Start Here', '', '', '', '']

  - ['', '', '', '', '']

  - ['Edit pool gallons here', '10000', 'This is the only cell you need to change on this sheet.', '', '']

  - ['Global adjustment to totals', '0', 'This changes the totals in columns D and E only. The coefficient column stays as the base model.', '', '']

  - ['Chem Clean Express gal per degreasing', '0', 'Annual filter-degreasing maintenance. Model assumes 4 cleanings per year for the Paddock filter.', '', '']

### Assumptions
- size: 34 rows x 4 columns
- preview:

  - ['Assumptions', '', '', '']

  - ['', '', '', '']

  - ['Editable assumptions', '', '', '']

  - ['Pool gallons (linked from Start Here)', "='Start Here'!B3", 'gallons', 'Primary pool size input']

  - ['Liquid chlorine strength', '12', '%', 'User stated 12% liquid chlorine']

### Monthly Detail
- size: 15 rows x 14 columns
- preview:

  - ['Monthly Detail', '', '', '', '', '']

  - ['Month', 'Days', 'Mean temp °F', 'UV index', 'Rainfall in', 'FC demand ppm/day']

  - ['Jan', '31', '70.6', '6', '2.04', '=ROUND(1.55 + 0.12*D3 + 0.03*(C3-78.9), 3)']

  - ['Feb', '28', '72.3', '8', '1.49', '=ROUND(1.55 + 0.12*D4 + 0.03*(C4-78.9), 3)']

  - ['Mar', '31', '74.4', '10', '2.05', '=ROUND(1.55 + 0.12*D5 + 0.03*(C5-78.9), 3)']

### Sources
- size: 16 rows x 3 columns
- preview:

  - ['Sources', '', '']

  - ['Source', 'URL', 'Used for']

  - ['Florida Climate Center Key West normals', 'https://climatecenter.fsu.edu/products-services/data/1991-2020-normals/key-west', 'Monthly mean temperature normals and annual precipitation context']

  - ['NWS Florida Keys normals PDF', 'https://www.weather.gov/media/key/Climate/Normals-EYW_NQX_MTH_TVR.pdf', 'Monthly Key West rainfall by month']

  - ['Weather2Travel Key West climate', 'https://www.weather2travel.com/florida/key-west/climate/', 'Monthly Key West UV index values']


## Modeling instruction
Port workbook logic into versioned code and use the workbook as a regression oracle, not as a permanent runtime engine.
