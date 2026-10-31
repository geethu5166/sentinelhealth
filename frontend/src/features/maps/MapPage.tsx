import React, { useState } from "react";
import { AlertCircle, EyeOff, Info, Layers, MapPin, RefreshCw, ShieldAlert } from "lucide-react";
import { useMapLayer } from "../../lib/api/hooks";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";

interface FictionalBoundary {
  id: string;
  code: string;
  name: string;
  level: string;
  population_estimate: number;
  type: string;
}

const FICTIONAL_BOUNDARIES: FictionalBoundary[] = [
  {
    id: "DIST-DHANPUR",
    code: "DIST-DHANPUR",
    name: "Dhanpur District",
    level: "district",
    population_estimate: 850000,
    type: "administrative_district",
  },
  {
    id: "ZONE-LAKSHMI",
    code: "ZONE-LAKSHMI",
    name: "Lakshmi Industrial Corridor",
    level: "sub_district",
    population_estimate: 120000,
    type: "industrial_zone",
  },
  {
    id: "CATCHMENT-NORTH",
    code: "CATCHMENT-NORTH",
    name: "Northern Rural Catchment",
    level: "catchment_cluster",
    population_estimate: 24000,
    type: "rural_health_cluster",
  },
];

export const MapPage: React.FC = () => {
  const [selectedMetric, setSelectedMetric] = useState<string>("pm25_concentration");
  const [selectedPeriod, setSelectedPeriod] = useState<string>("24h");
  const [selectedBoundaryCode, setSelectedBoundaryCode] = useState<string>("DIST-DHANPUR");

  // Genuinely fetch API-backed privacy-safe surveillance layer from backend
  const {
    data: mapLayer,
    isLoading,
    isError,
    refetch,
  } = useMapLayer(selectedMetric, selectedPeriod);

  // Map features by geography code
  const featuresByCode = React.useMemo(() => {
    const map = new Map<string, any>();
    if (mapLayer?.features) {
      for (const feat of mapLayer.features) {
        if (feat.properties?.geography_code) {
          map.set(feat.properties.geography_code, feat);
        }
      }
    }
    return map;
  }, [mapLayer]);

  const selectedBoundary: FictionalBoundary =
    FICTIONAL_BOUNDARIES.find((b) => b.code === selectedBoundaryCode) ?? FICTIONAL_BOUNDARIES[0]!;
  const selectedFeature = featuresByCode.get(selectedBoundary.code);

  const getStatusForBoundary = (code: string) => {
    if (isLoading) return "loading";
    if (isError || !mapLayer) return "unavailable";
    const feat = featuresByCode.get(code);
    return feat ? feat.properties.status : "unavailable";
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Aggregate Spatial Surveillance &amp; Risk Zones</h2>
          <p className="text-muted-foreground text-sm">
            Displays administrative district catchments. No household coordinates or point-level patient locations are ingested or displayed.
          </p>
        </div>

        {/* Dynamic Metric & Observation Window Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1.5 text-xs bg-card border rounded-lg p-1">
            <span className="text-muted-foreground pl-2 font-medium">Metric:</span>
            <select
              value={selectedMetric}
              onChange={(e) => setSelectedMetric(e.target.value)}
              className="bg-background text-xs border rounded px-2 py-1 focus:outline-none"
            >
              <option value="pm25_concentration">PM2.5 Ambient Concentration (24h Mean)</option>
              <option value="apparent_temperature">Apparent Temperature (Screening Proxy)</option>
              <option value="emergency_respiratory_admissions">Primary Care Respiratory Encounters</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-xs bg-card border rounded-lg p-1">
            <span className="text-muted-foreground pl-2 font-medium">Window:</span>
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value)}
              className="bg-background text-xs border rounded px-2 py-1 focus:outline-none"
            >
              <option value="24h">Rolling 24 Hours</option>
              <option value="7d">Past 7 Days</option>
            </select>
          </div>

          <Button size="sm" variant="outline" className="h-8 text-xs" onClick={() => refetch()}>
            <RefreshCw className="h-3.5 w-3.5 mr-1" /> Refresh
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map / Vector Visualizer */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Layers className="h-4 w-4 text-primary" /> Aggregate Catchment Boundaries (Server-State Driven)
              </CardTitle>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-muted border">
                EPSG:4326 (WGS84)
              </span>
            </div>
            <CardDescription className="text-xs">
              Polygons reflect real-time API surveillance states: elevated, baseline, suppressed, insufficient data, or unavailable.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* SVG Offline Polygon Map with Server-Driven Styling */}
            <div className="h-80 w-full border rounded-lg bg-muted/20 relative flex items-center justify-center overflow-hidden p-6">
              <svg viewBox="0 0 540 260" className="w-full h-full max-h-72">
                <defs>
                  {/* Diagonal Hatch Pattern for Privacy Suppressed Polygons */}
                  <pattern
                    id="diagonalHatch"
                    width="10"
                    height="10"
                    patternTransform="rotate(45 0 0)"
                    patternUnits="userSpaceOnUse"
                  >
                    <line x1="0" y1="0" x2="0" y2="10" stroke="#64748b" strokeWidth="2.5" />
                  </pattern>
                </defs>

                {/* Polygon 1: Dhanpur District */}
                {(() => {
                  const status = getStatusForBoundary("DIST-DHANPUR");
                  const isSel = selectedBoundaryCode === "DIST-DHANPUR";
                  let fill = "rgba(100, 116, 139, 0.1)";
                  let stroke = "#94a3b8";
                  let dash = "";
                  if (status === "elevated") {
                    fill = "rgba(249, 115, 22, 0.25)";
                    stroke = "#ea580c";
                  } else if (status === "valid_non_elevated") {
                    fill = "rgba(34, 197, 94, 0.15)";
                    stroke = "#16a34a";
                  } else if (status === "suppressed") {
                    fill = "url(#diagonalHatch)";
                    stroke = "#64748b";
                    dash = "4 2";
                  } else if (status === "insufficient_data") {
                    fill = "rgba(148, 163, 184, 0.2)";
                    stroke = "#94a3b8";
                    dash = "2 2";
                  }

                  return (
                    <g onClick={() => setSelectedBoundaryCode("DIST-DHANPUR")} className="cursor-pointer">
                      <polygon
                        points="20,30 180,30 180,230 20,230"
                        fill={fill}
                        stroke={stroke}
                        strokeWidth={isSel ? 3.5 : 2}
                        strokeDasharray={dash}
                        className="transition-all hover:opacity-85"
                      />
                      <text x="35" y="120" fill="currentColor" fontSize="12" fontWeight="bold">
                        Dhanpur District
                      </text>
                      <text x="35" y="140" fill={stroke} fontSize="10.5" fontWeight="semibold" className="capitalize">
                        State: {status.replace(/_/g, " ")}
                      </text>
                    </g>
                  );
                })()}

                {/* Polygon 2: Lakshmi Zone */}
                {(() => {
                  const status = getStatusForBoundary("ZONE-LAKSHMI");
                  const isSel = selectedBoundaryCode === "ZONE-LAKSHMI";
                  let fill = "rgba(100, 116, 139, 0.1)";
                  let stroke = "#94a3b8";
                  let dash = "";
                  if (status === "elevated") {
                    fill = "rgba(234, 179, 8, 0.25)";
                    stroke = "#ca8a04";
                  } else if (status === "valid_non_elevated") {
                    fill = "rgba(34, 197, 94, 0.15)";
                    stroke = "#16a34a";
                  } else if (status === "suppressed") {
                    fill = "url(#diagonalHatch)";
                    stroke = "#64748b";
                    dash = "4 2";
                  } else if (status === "insufficient_data") {
                    fill = "rgba(148, 163, 184, 0.2)";
                    stroke = "#94a3b8";
                    dash = "2 2";
                  }

                  return (
                    <g onClick={() => setSelectedBoundaryCode("ZONE-LAKSHMI")} className="cursor-pointer">
                      <polygon
                        points="195,30 355,30 355,230 195,230"
                        fill={fill}
                        stroke={stroke}
                        strokeWidth={isSel ? 3.5 : 2}
                        strokeDasharray={dash}
                        className="transition-all hover:opacity-85"
                      />
                      <text x="210" y="120" fill="currentColor" fontSize="12" fontWeight="bold">
                        Lakshmi Corridor
                      </text>
                      <text x="210" y="140" fill={stroke} fontSize="10.5" fontWeight="semibold" className="capitalize">
                        State: {status.replace(/_/g, " ")}
                      </text>
                    </g>
                  );
                })()}

                {/* Polygon 3: Northern Catchment */}
                {(() => {
                  const status = getStatusForBoundary("CATCHMENT-NORTH");
                  const isSel = selectedBoundaryCode === "CATCHMENT-NORTH";
                  let fill = "rgba(100, 116, 139, 0.1)";
                  let stroke = "#94a3b8";
                  let dash = "";
                  if (status === "elevated") {
                    fill = "rgba(249, 115, 22, 0.25)";
                    stroke = "#ea580c";
                  } else if (status === "valid_non_elevated") {
                    fill = "rgba(34, 197, 94, 0.15)";
                    stroke = "#16a34a";
                  } else if (status === "suppressed") {
                    fill = "url(#diagonalHatch)";
                    stroke = "#64748b";
                    dash = "4 2";
                  } else if (status === "insufficient_data") {
                    fill = "rgba(148, 163, 184, 0.2)";
                    stroke = "#94a3b8";
                    dash = "2 2";
                  }

                  return (
                    <g onClick={() => setSelectedBoundaryCode("CATCHMENT-NORTH")} className="cursor-pointer">
                      <polygon
                        points="370,30 520,30 520,230 370,230"
                        fill={fill}
                        stroke={stroke}
                        strokeWidth={isSel ? 3.5 : 2}
                        strokeDasharray={dash}
                        className="transition-all hover:opacity-85"
                      />
                      <rect x="382" y="105" width="126" height="46" rx="4" fill="rgba(15, 23, 42, 0.75)" />
                      <text x="390" y="123" fill="#f8fafc" fontSize="11" fontWeight="bold">
                        Northern Catchment
                      </text>
                      <text x="390" y="139" fill="#cbd5e1" fontSize="9.5" fontWeight="semibold" className="capitalize">
                        State: {status.replace(/_/g, " ")}
                      </text>
                    </g>
                  );
                })()}
              </svg>

              <div className="absolute bottom-3 left-3 bg-card/90 backdrop-blur-sm border rounded px-2.5 py-1 text-[11px] text-muted-foreground">
                Click any zone to inspect API response properties &amp; disclosure controls
              </div>
            </div>

            <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
              <span>Projection: Equirectangular offline projection</span>
              <span>
                Server API State: {isLoading ? "Querying backend..." : isError ? "Service Unavailable" : "Active Feed"}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Selected Area Details & Disclosure Notice */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-primary" /> District Surveillance Profile
                </span>
                <span
                  className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border capitalize ${
                    selectedFeature?.properties?.status === "suppressed"
                      ? "bg-slate-100 text-slate-800 dark:bg-slate-900 dark:text-slate-300 border-slate-300"
                      : selectedFeature?.properties?.status === "elevated"
                      ? "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300 border-orange-300"
                      : "bg-muted text-muted-foreground border-border"
                  }`}
                >
                  {selectedFeature ? selectedFeature.properties.status.replace(/_/g, " ") : "Unavailable"}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div>
                <span className="text-muted-foreground">Boundary Name:</span>
                <p className="text-sm font-bold mt-0.5">{selectedBoundary.name}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Administrative Level:</span>
                <p className="font-mono uppercase font-semibold mt-0.5">{selectedBoundary.level}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Catchment Exposure Denominator:</span>
                <p className="font-bold text-sm mt-0.5">{selectedBoundary.population_estimate.toLocaleString()} residents</p>
              </div>

              {/* Server-Driven Status Details */}
              {selectedFeature?.properties?.status === "suppressed" ? (
                <div className="p-3 rounded-md bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-2">
                  <div className="flex items-center gap-1.5 font-semibold text-slate-800 dark:text-slate-200">
                    <EyeOff className="h-4 w-4 text-slate-600" />
                    <span>Suppressed: this group does not meet the minimum reporting threshold.</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    To prevent statistical re-identification, the server disclosure control engine masks both the aggregate
                    encounter count and contributor count. Encounter rates are withheld when the numerator is suppressed.
                  </p>
                  <div className="font-mono text-[10px] text-muted-foreground border-t pt-1.5 border-slate-200 dark:border-slate-800">
                    Protected quantities: Encounter count and contributor count withheld by server API.
                  </div>
                </div>
              ) : selectedFeature?.properties?.status === "unavailable" || !selectedFeature ? (
                <div className="p-3 rounded-md bg-muted/60 border space-y-1.5">
                  <div className="flex items-center gap-1.5 font-semibold text-muted-foreground">
                    <AlertCircle className="h-4 w-4" />
                    <span>Data Unavailable</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    No active surveillance records were ingested for this spatial catchment during the selected period.
                    Estimated or fabricated values are never displayed on failure.
                  </p>
                </div>
              ) : selectedFeature?.properties?.status === "insufficient_data" ? (
                <div className="p-3 rounded-md bg-amber-500/10 border border-amber-500/30 space-y-1.5">
                  <div className="flex items-center gap-1.5 font-semibold text-amber-700 dark:text-amber-400">
                    <Info className="h-4 w-4" />
                    <span>Insufficient Ingestion Coverage</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    Ingestion coverage fell below 75% for this period; screening thresholds are suspended.
                  </p>
                </div>
              ) : (
                <div className="p-3 rounded-md bg-primary/5 border border-primary/20 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Observed Value:</span>
                    <span className="font-bold font-mono text-sm">
                      {selectedFeature.properties.value} {selectedFeature.properties.unit}
                    </span>
                  </div>
                  {selectedFeature.properties.encounter_rate_per_100k != null && (
                    <div className="flex items-center justify-between border-t pt-1.5 border-primary/10">
                      <span className="text-muted-foreground">Encounter Rate:</span>
                      <span className="font-bold font-mono text-xs">
                        {selectedFeature.properties.encounter_rate_per_100k} / 100k
                      </span>
                    </div>
                  )}
                  {selectedFeature.properties.rate_label && (
                    <p className="text-[10px] text-muted-foreground italic border-t pt-1 border-primary/10">
                      {selectedFeature.properties.rate_label}
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-amber-500/30 bg-amber-500/5">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-semibold text-amber-700 dark:text-amber-400 flex items-center gap-1.5">
                <Info className="h-3.5 w-3.5" /> Spatial Uncertainty &amp; Disclosure Standards
              </CardTitle>
            </CardHeader>
            <CardContent className="text-[11px] text-muted-foreground space-y-1.5">
              <p>
                Atmospheric screening metrics share coarse regional model grids (10km). Neighbouring facilities within the same model cell receive identical screening baselines.
              </p>
              <p>
                Server-enforced disclosure controls mask cells falling below the minimum reporting threshold to prevent individual re-identification in low-density catchment areas.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};
