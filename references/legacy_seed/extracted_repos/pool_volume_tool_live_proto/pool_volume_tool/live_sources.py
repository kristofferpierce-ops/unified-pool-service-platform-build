from __future__ import annotations

import json
import math
from collections import deque
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any
from urllib.parse import quote_plus

import numpy as np
import requests
from PIL import Image, ImageDraw


CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
CENSUS_GEOGRAPHIES_URL = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
FLORIDA_CADASTRAL_URL = (
    "https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/Florida_Statewide_Cadastral/FeatureServer/0/query"
)
USGS_NAIP_EXPORT_URL = "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer/exportImage"
MONROE_OPAL_URL = "https://fa-ettl-saasfaprod1.fa.ocs.oraclecloud.com/fscmUI/publicSector.html?root=PSCHM_GIS_MAP"
MONROE_MCESEARCH_URL = "https://mcesearch.monroecounty-fl.gov"


@dataclass
class LiveLookupResult:
    geocode: dict[str, Any] | None = None
    parcel: dict[str, Any] | None = None
    imagery_measurement: dict[str, Any] | None = None
    permit_records: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class LiveDataResolver:
    def __init__(self, timeout_seconds: int = 25) -> None:
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "pool-volume-tool/0.2 (+local prototype)",
                "Accept": "application/json,image/*,*/*",
            }
        )

    def resolve(self, address: str | None = None, parcel_id: str | None = None) -> LiveLookupResult:
        result = LiveLookupResult()
        try:
            geocode = self._geocode_address(address) if address else None
            result.geocode = geocode
        except Exception as exc:
            result.errors.append(f"Geocoding failed: {exc}")
            geocode = None

        try:
            parcel = self._lookup_parcel(parcel_id=parcel_id, geocode=geocode)
            result.parcel = parcel
        except Exception as exc:
            result.errors.append(f"Parcel lookup failed: {exc}")
            parcel = None

        try:
            county_name = self._county_name(geocode, parcel)
            result.permit_records = self._build_permit_records(address=address, parcel=parcel, county_name=county_name)
        except Exception as exc:
            result.errors.append(f"Permit link generation failed: {exc}")

        try:
            imagery_measurement = self._detect_pool_from_imagery(parcel=parcel, geocode=geocode)
            if imagery_measurement:
                result.imagery_measurement = imagery_measurement
            else:
                result.warnings.append("No pool candidate was confidently detected from live imagery.")
        except Exception as exc:
            result.errors.append(f"Imagery analysis failed: {exc}")

        return result

    def inspect(self, address: str | None = None, parcel_id: str | None = None) -> dict[str, Any]:
        result = self.resolve(address=address, parcel_id=parcel_id)
        return {
            "address": address,
            "parcel_id": parcel_id,
            "geocode": result.geocode,
            "parcel": result.parcel,
            "imagery_measurement": result.imagery_measurement,
            "permit_records": result.permit_records,
            "warnings": result.warnings,
            "errors": result.errors,
        }

    def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        response = self.session.get(url, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.json()

    def _geocode_address(self, address: str) -> dict[str, Any] | None:
        params = {
            "address": address,
            "benchmark": "Public_AR_Current",
            "format": "json",
        }
        payload = self._get_json(CENSUS_GEOCODER_URL, params)
        matches = payload.get("result", {}).get("addressMatches", [])
        if not matches:
            return None

        best = matches[0]
        geographies = self._get_json(
            CENSUS_GEOGRAPHIES_URL,
            {
                "address": address,
                "benchmark": "Public_AR_Current",
                "vintage": "Current_Current",
                "format": "json",
            },
        )
        geo_matches = geographies.get("result", {}).get("addressMatches", [])
        county_name = None
        county_fips = None
        if geo_matches:
            counties = geo_matches[0].get("geographies", {}).get("Counties", [])
            if counties:
                county_name = counties[0].get("NAME")
                county_fips = counties[0].get("COUNTY")

        return {
            "matched_address": best.get("matchedAddress"),
            "coordinates": {
                "lon": best.get("coordinates", {}).get("x"),
                "lat": best.get("coordinates", {}).get("y"),
            },
            "tiger_line": best.get("tigerLine", {}),
            "county_name": county_name,
            "county_fips": county_fips,
        }

    def _lookup_parcel(self, parcel_id: str | None, geocode: dict[str, Any] | None) -> dict[str, Any] | None:
        if parcel_id:
            return self._lookup_parcel_by_id(parcel_id)
        if geocode and geocode.get("coordinates"):
            return self._lookup_parcel_by_point(
                lon=float(geocode["coordinates"]["lon"]),
                lat=float(geocode["coordinates"]["lat"]),
            )
        return None

    def _lookup_parcel_by_id(self, parcel_id: str) -> dict[str, Any] | None:
        params = {
            "where": f"PARCEL_ID = '{parcel_id.replace("'", "''")}'",
            "outFields": "PARCEL_ID,CO_NO,OWN_NAME,OWN_ADDR1,OWN_CITY,OWN_STATE,OWN_ZIPCD,ACT_YR_BLT,LND_SQFOOT,TOT_LVG_AR,DOR_UC,SPEC_FEAT_",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json",
        }
        payload = self._get_json(FLORIDA_CADASTRAL_URL, params)
        features = payload.get("features", [])
        if not features:
            return None
        return self._normalize_parcel_feature(features[0])

    def _lookup_parcel_by_point(self, lon: float, lat: float) -> dict[str, Any] | None:
        params = {
            "where": "1=1",
            "geometry": json.dumps({"x": lon, "y": lat, "spatialReference": {"wkid": 4326}}),
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "PARCEL_ID,CO_NO,OWN_NAME,OWN_ADDR1,OWN_CITY,OWN_STATE,OWN_ZIPCD,ACT_YR_BLT,LND_SQFOOT,TOT_LVG_AR,DOR_UC,SPEC_FEAT_",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json",
        }
        payload = self._get_json(FLORIDA_CADASTRAL_URL, params)
        features = payload.get("features", [])
        if not features:
            return None
        return self._normalize_parcel_feature(features[0])

    def _normalize_parcel_feature(self, feature: dict[str, Any]) -> dict[str, Any]:
        attrs = feature.get("attributes", {})
        geometry = feature.get("geometry", {})
        rings = geometry.get("rings", [])
        bbox = self._bbox_from_rings(rings)
        centroid = self._centroid_from_rings(rings)
        return {
            "parcel_id": attrs.get("PARCEL_ID"),
            "county_code": attrs.get("CO_NO"),
            "owner_name": attrs.get("OWN_NAME"),
            "owner_address": {
                "line1": attrs.get("OWN_ADDR1"),
                "city": attrs.get("OWN_CITY"),
                "state": attrs.get("OWN_STATE"),
                "zip": attrs.get("OWN_ZIPCD"),
            },
            "year_built": attrs.get("ACT_YR_BLT"),
            "land_sqft": attrs.get("LND_SQFOOT"),
            "living_sqft": attrs.get("TOT_LVG_AR"),
            "dor_use_code": attrs.get("DOR_UC"),
            "special_feature_count": attrs.get("SPEC_FEAT_"),
            "geometry": {"rings": rings},
            "bbox": bbox,
            "centroid": centroid,
        }

    def _county_name(self, geocode: dict[str, Any] | None, parcel: dict[str, Any] | None) -> str | None:
        if geocode and geocode.get("county_name"):
            return geocode["county_name"]
        return None

    def _build_permit_records(self, address: str | None, parcel: dict[str, Any] | None, county_name: str | None) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        parcel_id = parcel.get("parcel_id") if parcel else None
        if county_name and "Monroe" in county_name:
            records.append(
                {
                    "source": "monroe_county_online_permitting",
                    "notes": "Live Monroe County permit search links generated. This prototype does not yet parse permit dimensions automatically.",
                    "search_url": MONROE_OPAL_URL,
                    "legacy_search_url": MONROE_MCESEARCH_URL,
                    "address": address,
                    "parcel_id": parcel_id,
                }
            )
        return records

    def _detect_pool_from_imagery(self, parcel: dict[str, Any] | None, geocode: dict[str, Any] | None) -> dict[str, Any] | None:
        if parcel and parcel.get("bbox"):
            min_lon, min_lat, max_lon, max_lat = parcel["bbox"]
            minx, miny = lonlat_to_web_mercator(min_lon, min_lat)
            maxx, maxy = lonlat_to_web_mercator(max_lon, max_lat)
            pad_m = max(8.0, 0.15 * max(maxx - minx, maxy - miny))
            bbox = (minx - pad_m, miny - pad_m, maxx + pad_m, maxy + pad_m)
            rings_merc = [
                [lonlat_to_web_mercator(lon, lat) for lon, lat, *_ in ring]
                for ring in parcel.get("geometry", {}).get("rings", [])
            ]
        elif geocode and geocode.get("coordinates"):
            lon = float(geocode["coordinates"]["lon"])
            lat = float(geocode["coordinates"]["lat"])
            cx, cy = lonlat_to_web_mercator(lon, lat)
            pad_m = 70.0
            bbox = (cx - pad_m, cy - pad_m, cx + pad_m, cy + pad_m)
            rings_merc = []
        else:
            return None

        image = self._fetch_naip_image(bbox)
        measurement = detect_pool_surface_area(image=image, bbox_mercator=bbox, parcel_rings_mercator=rings_merc)
        if not measurement:
            return None

        measurement.update(
            {
                "source": "usgs_naip_live",
                "imagery_bbox_mercator": bbox,
            }
        )
        return measurement

    def _fetch_naip_image(self, bbox_mercator: tuple[float, float, float, float]) -> Image.Image:
        params = {
            "bbox": ",".join(f"{v:.3f}" for v in bbox_mercator),
            "bboxSR": "3857",
            "imageSR": "3857",
            "size": "1024,1024",
            "format": "jpgpng",
            "transparent": "false",
            "interpolation": "+RSP_BilinearInterpolation",
            "renderingRule": json.dumps({"rasterFunction": "NaturalColor"}),
            "f": "image",
        }
        response = self.session.get(USGS_NAIP_EXPORT_URL, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGB")

    @staticmethod
    def _bbox_from_rings(rings: list[list[list[float]]]) -> tuple[float, float, float, float] | None:
        points = [(pt[0], pt[1]) for ring in rings for pt in ring if len(pt) >= 2]
        if not points:
            return None
        xs, ys = zip(*points)
        return (min(xs), min(ys), max(xs), max(ys))

    @staticmethod
    def _centroid_from_rings(rings: list[list[list[float]]]) -> tuple[float, float] | None:
        points = [(pt[0], pt[1]) for ring in rings for pt in ring if len(pt) >= 2]
        if not points:
            return None
        xs, ys = zip(*points)
        return (sum(xs) / len(xs), sum(ys) / len(ys))


def lonlat_to_web_mercator(lon: float, lat: float) -> tuple[float, float]:
    origin_shift = 20037508.342789244
    mx = lon * origin_shift / 180.0
    lat = max(min(lat, 89.5), -89.5)
    my = math.log(math.tan((90.0 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
    my = my * origin_shift / 180.0
    return mx, my


def mercator_to_pixel(x: float, y: float, bbox: tuple[float, float, float, float], size: tuple[int, int]) -> tuple[float, float]:
    minx, miny, maxx, maxy = bbox
    width, height = size
    px = (x - minx) / (maxx - minx) * width
    py = (maxy - y) / (maxy - miny) * height
    return px, py


def detect_pool_surface_area(
    image: Image.Image,
    bbox_mercator: tuple[float, float, float, float],
    parcel_rings_mercator: list[list[tuple[float, float]]] | None = None,
) -> dict[str, Any] | None:
    width, height = image.size
    arr = np.asarray(image).astype(np.int16)

    parcel_mask_img = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(parcel_mask_img)
    if parcel_rings_mercator:
        for ring in parcel_rings_mercator:
            if len(ring) < 3:
                continue
            pix_ring = [mercator_to_pixel(x, y, bbox_mercator, image.size) for x, y in ring]
            draw.polygon(pix_ring, fill=255)
    else:
        draw.rectangle([0, 0, width, height], fill=255)
    parcel_mask = np.asarray(parcel_mask_img) > 0

    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    max_rgb = np.maximum(np.maximum(r, g), b)
    min_rgb = np.minimum(np.minimum(r, g), b)
    chroma = max_rgb - min_rgb

    water_like = (
        (parcel_mask)
        & (b >= 70)
        & (b >= r + 8)
        & (b >= g - 10)
        & (chroma >= 12)
        & (max_rgb <= 245)
        & ((b - r) + (b - g) >= 18)
    )

    if not water_like.any():
        return None

    meter_per_px_x = (bbox_mercator[2] - bbox_mercator[0]) / width
    meter_per_px_y = (bbox_mercator[3] - bbox_mercator[1]) / height
    sqft_per_pixel = abs(meter_per_px_x * meter_per_px_y) * 10.7639104167

    min_pixels = max(20, int(40.0 / max(sqft_per_pixel, 0.001)))
    max_pixels = max(min_pixels + 1, int(15000.0 / max(sqft_per_pixel, 0.001)))

    best = _largest_component(water_like, min_pixels=min_pixels, max_pixels=max_pixels)
    if not best:
        return None

    component_mask, pixel_count, bbox_px = best
    area_sqft = pixel_count * sqft_per_pixel
    if area_sqft < 40 or area_sqft > 15000:
        return None

    bx0, by0, bx1, by1 = bbox_px
    bbox_area = max(1, (bx1 - bx0 + 1) * (by1 - by0 + 1))
    fill_ratio = pixel_count / bbox_area
    mean_blueness = float(np.mean((b - np.maximum(r, g))[component_mask]))

    confidence = 0.55
    if 0.35 <= fill_ratio <= 0.95:
        confidence += 0.12
    if mean_blueness >= 20:
        confidence += 0.1
    if area_sqft <= 5000:
        confidence += 0.08
    confidence = max(0.45, min(confidence, 0.9))

    return {
        "measured_surface_area_sqft": round(float(area_sqft), 2),
        "shape": "detected_from_live_imagery",
        "confidence": round(confidence, 2),
        "component_pixels": int(pixel_count),
        "component_fill_ratio": round(fill_ratio, 3),
        "mean_blueness": round(mean_blueness, 2),
    }


def _largest_component(mask: np.ndarray, min_pixels: int, max_pixels: int) -> tuple[np.ndarray, int, tuple[int, int, int, int]] | None:
    h, w = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    best_coords: list[tuple[int, int]] = []
    best_bbox = (0, 0, 0, 0)

    for y in range(h):
        for x in range(w):
            if not mask[y, x] or visited[y, x]:
                continue
            coords: list[tuple[int, int]] = []
            q: deque[tuple[int, int]] = deque([(x, y)])
            visited[y, x] = True
            minx = maxx = x
            miny = maxy = y
            while q:
                cx, cy = q.popleft()
                coords.append((cx, cy))
                if cx < minx:
                    minx = cx
                if cx > maxx:
                    maxx = cx
                if cy < miny:
                    miny = cy
                if cy > maxy:
                    maxy = cy
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        q.append((nx, ny))

            size = len(coords)
            if size < min_pixels or size > max_pixels:
                continue
            if size > len(best_coords):
                best_coords = coords
                best_bbox = (minx, miny, maxx, maxy)

    if not best_coords:
        return None

    component_mask = np.zeros_like(mask, dtype=bool)
    for x, y in best_coords:
        component_mask[y, x] = True
    return component_mask, len(best_coords), best_bbox


def monroe_search_links(address: str | None, parcel_id: str | None) -> dict[str, str]:
    q = quote_plus(address or parcel_id or "")
    return {
        "online_permitting": MONROE_OPAL_URL,
        "legacy_mcesearch": MONROE_MCESEARCH_URL,
        "query_hint": q,
    }
