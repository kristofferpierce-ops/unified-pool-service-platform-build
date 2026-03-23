# volume_tool python index

## `main_example.py`
- lines: 11
- classes: none
- top-level functions: root

## `pool_volume_tool/__init__.py`
- lines: 3
- classes: none
- top-level functions: none

## `pool_volume_tool/connectors/base.py`
- lines: 16
- classes: PermitConnector, ImageryConnector
- top-level functions: none

## `pool_volume_tool/connectors/mock_connectors.py`
- lines: 71
- classes: MockPermitConnector, MockImageryConnector
- top-level functions: none

## `pool_volume_tool/live_sources.py`
- lines: 445
- classes: LiveLookupResult, LiveDataResolver
- top-level functions: lonlat_to_web_mercator, mercator_to_pixel, detect_pool_surface_area, _largest_component, monroe_search_links

## `pool_volume_tool/router.py`
- lines: 30
- classes: none
- top-level functions: health_check, inspect_live, estimate_pool_volume

## `pool_volume_tool/schemas.py`
- lines: 46
- classes: ManualOverrides, EstimateRequest, EvidenceItem, EstimateResult, HealthResponse
- top-level functions: none

## `pool_volume_tool/service.py`
- lines: 187
- classes: PoolVolumeService
- top-level functions: none
