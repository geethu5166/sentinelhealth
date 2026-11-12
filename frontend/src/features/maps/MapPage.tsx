import React, { useEffect, useMemo, useRef, useState } from "react";
import maplibregl, { GeoJSONSource, Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Info, Layers, MapPin } from "lucide-react";
import { useAlerts } from "../../lib/api/hooks";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { PageHeader } from "../../components/ui/page-header";
import { ErrorState } from "../../components/ui/error-state";
import { Skeleton } from "../../components/ui/skeleton";
import { severityBadgeClass, humanizeKey } from "../../lib/utils";

interface GeoDistrict {
  id: string;
  name: string;
  level: string;
  population_estimate: number;
  type: string;
  severity?: string;
  hazard?: string;
}

const SEVERITY_COLORS = {
  advisory: "#0284c7",
  watch: "#d97706",
  warning: "#ea580c",
  critical: "#dc2626",
  emergency: "#991b1b",
  none: "#94a3b8",
} as const;

export const MapPage: React.FC = () => {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [geojson, setGeojson] = useState<GeoJSON.FeatureCollection | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedDistrict, setSelectedDistrict] = useState<GeoDistrict | null>(null);
  const { data: alerts } = useAlerts({ status: "new" });

  const severityByName = useMemo(() => {
    const map = new Map<string, { severity: string; hazard: string }>();
    (alerts || []).forEach((alert) => {
      if (!alert.geography_name) return;
      const existing = map.get(alert.geography_name);
      const rank = ["advisory", "watch", "warning", "critical", "emergency"];
      if (!existing || rank.indexOf(alert.severity) > rank.indexOf(existing.severity)) {
        map.set(alert.geography_name, { severity: alert.severity, hazard: alert.hazard });
      }
    });
    return map;
  }, [alerts]);

  useEffect(() => {
    let cancelled = false;
    fetch("/geojson/districts.geojson")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load geography boundaries");
        return res.json();
      })
      .then((data: GeoJSON.FeatureCollection) => {
        if (cancelled) return;
        setGeojson(data);
        const first = data.features[0]?.properties as GeoDistrict | undefined;
        if (first) setSelectedDistrict(first);
      })
      .catch((err: Error) => {
        if (!cancelled) setLoadError(err.message || "Failed to load map data");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!mapContainerRef.current || !geojson || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          basemap: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [
          {
            id: "basemap",
            type: "raster",
            source: "basemap",
          },
        ],
      },
      center: [79.2, 21.24],
      zoom: 9.2,
      attributionControl: { compact: true },
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

    map.on("load", () => {
      map.addSource("districts", {
        type: "geojson",
        data: geojson,
      });

      map.addLayer({
        id: "district-fill",
        type: "fill",
        source: "districts",
        paint: {
          "fill-color": [
            "match",
            ["get", "severity"],
            "advisory",
            "#0284c7",
            "watch",
            "#d97706",
            "warning",
            "#ea580c",
            "critical",
            "#dc2626",
            "emergency",
            "#991b1b",
            "#94a3b8",
          ],
          "fill-opacity": 0.42,
        },
      });

      map.addLayer({
        id: "district-outline",
        type: "line",
        source: "districts",
        paint: {
          "line-color": "#0f3d3e",
          "line-width": 1.5,
        },
      });

      map.on("click", "district-fill", (e) => {
        const feature = e.features?.[0];
        if (!feature?.properties) return;
        setSelectedDistrict(feature.properties as unknown as GeoDistrict);
      });

      map.on("mouseenter", "district-fill", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "district-fill", () => {
        map.getCanvas().style.cursor = "";
      });
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [geojson]);

  useEffect(() => {
    if (!geojson || !mapRef.current) return;
    const enriched: GeoJSON.FeatureCollection = {
      ...geojson,
      features: geojson.features.map((feature) => {
        const name = String(feature.properties?.name || "");
        const match = severityByName.get(name);
        return {
          ...feature,
          properties: {
            ...feature.properties,
            severity: match?.severity || "none",
            hazard: match?.hazard || null,
          },
        };
      }),
    };

    const source = mapRef.current.getSource("districts") as GeoJSONSource | undefined;
    if (source) {
      source.setData(enriched);
    }

    const selectedName = selectedDistrict?.name;
    if (selectedName) {
      const props = enriched.features.find((f) => f.properties?.name === selectedName)?.properties;
      if (props) setSelectedDistrict(props as unknown as GeoDistrict);
    }
  }, [geojson, severityByName, selectedDistrict?.name]);

  return (
    <div className="mx-auto max-w-7xl animate-fade-in space-y-6">
      <PageHeader
        title="Aggregate geography"
        description="District polygons only — no household points or individual coordinates are collected or plotted."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="shadow-panel lg:col-span-2">
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <Layers className="h-4 w-4 text-primary" aria-hidden /> Severity choropleth
              </CardTitle>
              <span className="rounded border bg-muted px-2 py-0.5 font-mono text-[10px] uppercase">
                EPSG:4326
              </span>
            </div>
            <CardDescription className="text-xs">
              Colours reflect the highest open alert severity overlapping each approved boundary.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loadError ? (
              <ErrorState title="Map data unavailable" description={loadError} />
            ) : !geojson ? (
              <Skeleton className="h-80 w-full" />
            ) : (
              <div className="relative overflow-hidden rounded-lg border">
                <div ref={mapContainerRef} className="h-80 w-full" role="img" aria-label="District severity map" />
                <div className="absolute bottom-3 left-3 rounded border bg-card/95 px-2.5 py-1.5 text-[11px] text-muted-foreground shadow-sm backdrop-blur">
                  <div className="mb-1 font-semibold text-foreground">Severity</div>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(SEVERITY_COLORS)
                      .filter(([k]) => k !== "none")
                      .map(([key, color]) => (
                        <span key={key} className="inline-flex items-center gap-1 capitalize">
                          <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: color }} />
                          {key}
                        </span>
                      ))}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="shadow-panel">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <MapPin className="h-4 w-4 text-primary" aria-hidden /> District profile
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              {selectedDistrict ? (
                <>
                  <div>
                    <span className="text-muted-foreground">Boundary</span>
                    <p className="mt-0.5 text-sm font-semibold">{selectedDistrict.name}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Level</span>
                    <p className="mt-0.5 font-mono text-[11px] uppercase font-semibold">{selectedDistrict.level}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Population estimate</span>
                    <p className="mt-0.5 text-sm font-semibold">
                      {selectedDistrict.population_estimate?.toLocaleString()} residents
                    </p>
                  </div>
                  {selectedDistrict.severity && selectedDistrict.severity !== "none" ? (
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <span className={`rounded border px-2 py-0.5 text-[11px] font-semibold capitalize ${severityBadgeClass(selectedDistrict.severity)}`}>
                        {selectedDistrict.severity}
                      </span>
                      {selectedDistrict.hazard ? (
                        <span className="text-[11px] capitalize text-muted-foreground">
                          {humanizeKey(selectedDistrict.hazard)}
                        </span>
                      ) : null}
                    </div>
                  ) : (
                    <p className="text-muted-foreground">No open alerts on this boundary.</p>
                  )}
                </>
              ) : (
                <p className="text-muted-foreground">Select a polygon to inspect metadata.</p>
              )}
            </CardContent>
          </Card>

          <Card className="border-amber-500/30 bg-amber-500/5 shadow-panel">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-1.5 text-xs font-semibold text-amber-700 dark:text-amber-400">
                <Info className="h-3.5 w-3.5" aria-hidden /> Spatial uncertainty
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1.5 text-[11px] text-muted-foreground">
              <p>
                Environmental models share coarse regional grids. Neighbouring sites in the same ~10 km cell receive
                identical screening metrics.
              </p>
              <p>
                Records missing workplace tags contribute to regional totals but are excluded from boundary mapping.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};
