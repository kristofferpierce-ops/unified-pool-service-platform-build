from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from .connectors.base import ImageryConnector, PermitConnector
from .connectors.mock_connectors import MockImageryConnector, MockPermitConnector
from .live_sources import LiveDataResolver
from .schemas import EstimateRequest, EstimateResult, EvidenceItem

GALLONS_PER_CUBIC_FOOT = 7.48052


@dataclass
class PoolVolumeService:
    permit_connector: PermitConnector
    imagery_connector: ImageryConnector
    live_resolver: LiveDataResolver

    @classmethod
    def build_default(cls) -> "PoolVolumeService":
        return cls(
            permit_connector=MockPermitConnector(),
            imagery_connector=MockImageryConnector(),
            live_resolver=LiveDataResolver(),
        )

    def inspect_live(self, request: EstimateRequest) -> dict:
        return self.live_resolver.inspect(address=request.address, parcel_id=request.parcel_id)

    def estimate(self, request: EstimateRequest) -> EstimateResult:
        permit_records = [*self.permit_connector.fetch(request.address, request.parcel_id), *request.permit_records]
        imagery_measurements = [*self.imagery_connector.fetch(request.address, request.parcel_id), *request.imagery_measurements]

        evidence: list[EvidenceItem] = []
        assumptions: list[str] = []

        if request.use_live_sources and request.address and not permit_records and not imagery_measurements:
            live = self.live_resolver.resolve(address=request.address, parcel_id=request.parcel_id)
            if live.parcel:
                evidence.append(
                    EvidenceItem(
                        source="florida_statewide_parcels_live",
                        evidence_type="parcel",
                        summary="Live parcel geometry and property metadata were found for the requested address.",
                        raw=live.parcel,
                    )
                )
            if live.geocode:
                evidence.append(
                    EvidenceItem(
                        source="census_geocoder_live",
                        evidence_type="geocode",
                        summary=f"Address geocoded to {live.geocode.get('matched_address')}.",
                        raw=live.geocode,
                    )
                )
            if live.permit_records:
                permit_records.extend(live.permit_records)
            if live.imagery_measurement:
                imagery_measurements.append(live.imagery_measurement)
            assumptions.extend(live.warnings)
            assumptions.extend(live.errors)

        for permit in permit_records:
            evidence.append(
                EvidenceItem(
                    source=permit.get("source", "permit"),
                    evidence_type="permit",
                    summary=permit.get("notes", "Permit-derived dimensional evidence found."),
                    raw=permit,
                )
            )

        for image in imagery_measurements:
            evidence.append(
                EvidenceItem(
                    source=image.get("source", "imagery"),
                    evidence_type="imagery",
                    summary=f"Imagery measured surface area at about {image.get('measured_surface_area_sqft')} sq ft.",
                    raw=image,
                )
            )

        overrides = request.manual_overrides
        property_type = overrides.property_type if overrides and overrides.property_type else "unknown"

        authoritative_volume = next(
            (float(p["design_volume_gallons"]) for p in permit_records if p.get("design_volume_gallons")),
            None,
        )
        if authoritative_volume is not None:
            surface_area = self._resolve_surface_area(permit_records, imagery_measurements)
            avg_depth = self._resolve_average_depth(permit_records, overrides)
            return EstimateResult(
                gallons_estimate=round(authoritative_volume, 2),
                gallons_low=round(authoritative_volume * 0.98, 2),
                gallons_high=round(authoritative_volume * 1.02, 2),
                confidence="high",
                method="authoritative_permit_volume",
                average_depth_ft=round(avg_depth, 2),
                surface_area_sqft=surface_area,
                evidence=evidence,
                assumptions=assumptions,
            )

        surface_area = self._resolve_surface_area(permit_records, imagery_measurements)
        avg_depth = self._resolve_average_depth(permit_records, overrides)

        if surface_area is None:
            raise ValueError("No surface area evidence found. Provide permit records, imagery measurements, or manual inputs.")

        method = "permit_and_imagery_depth_model"
        confidence = "medium"

        if not permit_records and not (overrides and (overrides.avg_depth_ft or (overrides.shallow_depth_ft and overrides.deep_depth_ft))):
            avg_depth = self._default_average_depth(property_type)
            assumptions.append(
                f"No permit depth evidence found, so default average depth {avg_depth:.1f} ft was used for property type '{property_type}'."
            )
            method = "imagery_only_depth_template"
            confidence = "low"

        gallons = surface_area * avg_depth * GALLONS_PER_CUBIC_FOOT
        low_factor, high_factor = self._uncertainty_band(confidence)

        if overrides and overrides.attached_spa_gallons:
            gallons += overrides.attached_spa_gallons
            assumptions.append(f"Attached spa volume of {overrides.attached_spa_gallons:.0f} gallons added by manual override.")

        return EstimateResult(
            gallons_estimate=round(gallons, 2),
            gallons_low=round(gallons * low_factor, 2),
            gallons_high=round(gallons * high_factor, 2),
            confidence=confidence,
            method=method,
            average_depth_ft=round(avg_depth, 2),
            surface_area_sqft=round(surface_area, 2),
            evidence=evidence,
            assumptions=assumptions,
        )

    def _resolve_surface_area(self, permit_records: list[dict], imagery_measurements: list[dict]) -> float | None:
        permit_areas = [float(p["water_surface_area_sqft"]) for p in permit_records if p.get("water_surface_area_sqft")]
        image_areas = [float(i["measured_surface_area_sqft"]) for i in imagery_measurements if i.get("measured_surface_area_sqft")]

        if permit_areas and image_areas:
            return mean([permit_areas[0], image_areas[0]])
        if permit_areas:
            return permit_areas[0]
        if image_areas:
            return image_areas[0]
        return None

    def _resolve_average_depth(self, permit_records: list[dict], overrides) -> float:
        if overrides:
            if overrides.avg_depth_ft is not None:
                return float(overrides.avg_depth_ft)
            if overrides.shallow_depth_ft is not None and overrides.deep_depth_ft is not None:
                return (float(overrides.shallow_depth_ft) + float(overrides.deep_depth_ft)) / 2.0

        for permit in permit_records:
            shallow = permit.get("shallow_depth_ft")
            deep = permit.get("deep_depth_ft")
            avg = permit.get("average_depth_ft")
            if avg is not None:
                return float(avg)
            if shallow is not None and deep is not None:
                return (float(shallow) + float(deep)) / 2.0

        return 4.5

    def _default_average_depth(self, property_type: str) -> float:
        defaults = {
            "residential": 4.75,
            "commercial": 4.5,
            "public": 5.0,
            "unknown": 4.5,
        }
        return defaults.get(property_type, 4.5)

    def _uncertainty_band(self, confidence: str) -> tuple[float, float]:
        if confidence == "high":
            return 0.98, 1.02
        if confidence == "medium":
            return 0.9, 1.1
        return 0.8, 1.2
