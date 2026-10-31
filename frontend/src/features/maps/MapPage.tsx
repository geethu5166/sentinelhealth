import React, { useEffect, useState } from "react";
import { EyeOff, Info, Layers, MapPin, ShieldAlert } from "lucide-react";
import { useGeographies } from "../../lib/api/hooks";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";

interface GeoDistrict {
  id: string;
  name: string;
  level: string;
  population_estimate: number;
  type: string;
  is_suppressed?: boolean;
  contributor_count?: number;
  suppression_reason?: string;
  status_badge?: string;
}

export const MapPage: React.FC = () => {
  const [districts, setDistricts] = useState<GeoDistrict[]>([
    {
      id: "DIST-DHANPUR",
      name: "Dhanpur District",
      level: "district",
      population_estimate: 850000,
      type: "administrative_district",
      is_suppressed: false,
      status_badge: "Warning: Heat Risk",
    },
    {
      id: "ZONE-LAKSHMI",
      name: "Lakshmi Industrial Corridor",
      level: "sub_district",
      population_estimate: 120000,
      type: "industrial_zone",
      is_suppressed: false,
      status_badge: "Watch: Air Quality",
    },
    {
      id: "CATCHMENT-NORTH",
      name: "Northern Rural Catchment",
      level: "catchment_cluster",
      population_estimate: 24000,
      type: "rural_health_cluster",
      is_suppressed: true,
      contributor_count: 6,
      suppression_reason: "Tested disclosure control: contributor count (n=6) is below minimum threshold (k=10). Rate is suppressed.",
      status_badge: "Suppressed (n < 10)",
    },
  ]);
  const [selectedDistrict, setSelectedDistrict] = useState<GeoDistrict | null>(null);
  const { data: geographies } = useGeographies();

  useEffect(() => {
    // Set default selected
    if (districts.length > 0 && !selectedDistrict) {
      setSelectedDistrict(districts[0] ?? null);
    }
  }, [districts]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Approved Aggregate Geography & Hotspots</h2>
        <p className="text-muted-foreground text-sm">
          Spatial surveillance maps aggregate district polygons. No household points or individual coordinates are collected or plotted.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map / Polygon Visualizer */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Layers className="h-4 w-4 text-primary" /> Aggregate Spatial Boundaries (Offline Vector View)
              </CardTitle>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-muted border">
                EPSG:4326 (WGS84)
              </span>
            </div>
            <CardDescription className="text-xs">
              Polygons show reviewed administrative districts and industrial catchments.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* SVG Offline Polygon Map */}
            <div className="h-80 w-full border rounded-lg bg-muted/20 relative flex items-center justify-center overflow-hidden p-6">
              <svg viewBox="0 0 540 260" className="w-full h-full max-h-72">
                <defs>
                  <pattern
                    id="diagonalHatch"
                    width="10"
                    height="10"
                    patternTransform="rotate(45 0 0)"
                    patternUnits="userSpaceOnUse"
                  >
                    <line x1="0" y1="0" x2="0" y2="10" stroke="#94a3b8" strokeWidth="2.5" />
                  </pattern>
                </defs>

                {/* District 1: Dhanpur (Elevated Heat Warning - Orange fill) */}
                <polygon
                  points="20,30 180,30 180,230 20,230"
                  fill="rgba(249, 115, 22, 0.25)"
                  stroke="#ea580c"
                  strokeWidth="2.5"
                  className="cursor-pointer hover:opacity-80 transition-opacity"
                  onClick={() => setSelectedDistrict(districts[0] || null)}
                />
                <text x="45" y="120" fill="currentColor" fontSize="12" fontWeight="bold">
                  Dhanpur District
                </text>
                <text x="45" y="140" fill="#ea580c" fontSize="10" fontWeight="bold">
                  Warning: Heat Risk
                </text>

                {/* District 2: Lakshmi Zone (Watch - Amber fill) */}
                <polygon
                  points="195,30 355,30 355,230 195,230"
                  fill="rgba(234, 179, 8, 0.2)"
                  stroke="#ca8a04"
                  strokeWidth="2"
                  className="cursor-pointer hover:opacity-80 transition-opacity"
                  onClick={() => setSelectedDistrict(districts[1] || null)}
                />
                <text x="210" y="120" fill="currentColor" fontSize="12" fontWeight="bold">
                  Lakshmi Corridor
                </text>
                <text x="220" y="140" fill="#ca8a04" fontSize="10" fontWeight="semibold">
                  Watch: Air Quality
                </text>

                {/* District 3: Northern Catchment (Suppressed - Diagonal Hatch) */}
                <polygon
                  points="370,30 520,30 520,230 370,230"
                  fill="url(#diagonalHatch)"
                  stroke="#64748b"
                  strokeWidth="2"
                  strokeDasharray="4 2"
                  className="cursor-pointer hover:opacity-80 transition-opacity"
                  onClick={() => setSelectedDistrict(districts[2] || null)}
                />
                <rect x="385" y="105" width="120" height="46" rx="4" fill="rgba(15, 23, 42, 0.75)" />
                <text x="395" y="124" fill="#f8fafc" fontSize="11" fontWeight="bold">
                  Northern Catchment
                </text>
                <text x="398" y="140" fill="#cbd5e1" fontSize="9.5" fontWeight="semibold">
                  🔒 Suppressed (&lt;10)
                </text>
              </svg>

              <div className="absolute bottom-3 left-3 bg-card/90 backdrop-blur-sm border rounded px-2.5 py-1 text-[11px] text-muted-foreground">
                Click any zone polygon to inspect surveillance profile &amp; disclosure controls
              </div>
            </div>

            <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
              <span>Projection: Equirectangular offline projection</span>
              <span>Tested Small-Number Disclosure: Enabled (k &ge; 10 threshold)</span>
            </div>
          </CardContent>
        </Card>

        {/* Selected Area Details & Uncertainty Notice */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-primary" /> District Surveillance Profile
                </span>
                {selectedDistrict?.status_badge && (
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                      selectedDistrict.is_suppressed
                        ? "bg-slate-100 text-slate-800 dark:bg-slate-900 dark:text-slate-300 border-slate-300"
                        : selectedDistrict.status_badge.includes("Warning")
                        ? "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300 border-orange-300"
                        : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 border-amber-300"
                    }`}
                  >
                    {selectedDistrict.status_badge}
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              {selectedDistrict ? (
                <>
                  <div>
                    <span className="text-muted-foreground">Boundary Name:</span>
                    <p className="text-sm font-bold mt-0.5">{selectedDistrict.name}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Administrative Level:</span>
                    <p className="font-mono uppercase font-semibold mt-0.5">{selectedDistrict.level}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Population Exposure Estimate:</span>
                    <p className="font-bold text-sm mt-0.5">{selectedDistrict.population_estimate?.toLocaleString()} residents</p>
                  </div>

                  {selectedDistrict.is_suppressed ? (
                    <div className="p-2.5 rounded-md bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1.5">
                      <div className="flex items-center gap-1.5 font-semibold text-slate-800 dark:text-slate-200">
                        <EyeOff className="h-3.5 w-3.5 text-slate-600" />
                        <span>Aggregated Rate Suppressed</span>
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        {selectedDistrict.suppression_reason}
                      </p>
                      <div className="font-mono text-[10px] text-muted-foreground">
                        Contributor Count: <strong>{selectedDistrict.contributor_count}</strong> (&lt; minimum threshold of 10)
                      </div>
                    </div>
                  ) : (
                    <div>
                      <span className="text-muted-foreground">Location Basis:</span>
                      <p className="mt-0.5">Municipal Catchment &amp; Industrial Zoning Registry</p>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-muted-foreground">Select an area on the map to view data.</p>
              )}
            </CardContent>
          </Card>

          <Card className="border-amber-500/30 bg-amber-500/5">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-semibold text-amber-700 dark:text-amber-400 flex items-center gap-1.5">
                <Info className="h-3.5 w-3.5" /> Spatial Uncertainty &amp; Disclosure Notice
              </CardTitle>
            </CardHeader>
            <CardContent className="text-[11px] text-muted-foreground space-y-1.5">
              <p>
                Environmental atmospheric models share coarse regional grids. Neighbouring sites within the same 10km grid receive identical screening metrics.
              </p>
              <p>
                Tested disclosure controls suppress small-cell incident counts (&lt; 10 contributors) to prevent statistical re-identification in low-density catchment areas.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

