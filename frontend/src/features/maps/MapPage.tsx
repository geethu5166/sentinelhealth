import React, { useEffect, useState } from "react";
import { Info, Layers, MapPin } from "lucide-react";
import { useGeographies } from "../../lib/api/hooks";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";

interface GeoDistrict {
  id: string;
  name: string;
  level: string;
  population_estimate: number;
  type: string;
}

export const MapPage: React.FC = () => {
  const [districts, setDistricts] = useState<GeoDistrict[]>([]);
  const [selectedDistrict, setSelectedDistrict] = useState<GeoDistrict | null>(null);
  const { data: geographies } = useGeographies();

  useEffect(() => {
    // Fetch local offline GeoJSON
    fetch("/geojson/districts.geojson")
      .then((res) => res.json())
      .then((data) => {
        const items = data.features.map((f: any) => f.properties);
        setDistricts(items);
        if (items.length > 0) setSelectedDistrict(items[0]);
      })
      .catch(() => {
        // Fallback default
        setDistricts([
          { id: "DIST-DHANPUR", name: "Dhanpur District", level: "district", population_estimate: 850000, type: "administrative_district" },
          { id: "ZONE-LAKSHMI", name: "Lakshmi Industrial Corridor", level: "sub_district", population_estimate: 120000, type: "industrial_zone" },
        ]);
      });
  }, []);

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
              <svg viewBox="0 0 500 300" className="w-full h-full max-h-72">
                {/* District 1: Dhanpur (Elevated Heat Warning - Orange fill) */}
                <polygon
                  points="50,50 250,50 250,250 50,250"
                  fill="rgba(249, 115, 22, 0.25)"
                  stroke="#ea580c"
                  strokeWidth="2.5"
                  className="cursor-pointer hover:opacity-80 transition-opacity"
                  onClick={() => setSelectedDistrict(districts[0] || null)}
                />
                <text x="110" y="140" fill="currentColor" fontSize="13" fontWeight="bold">
                  Dhanpur District
                </text>
                <text x="120" y="160" fill="#ea580c" fontSize="11" fontWeight="bold">
                  Warning: Heat Risk
                </text>

                {/* District 2: Lakshmi Zone (Watch - Amber fill) */}
                <polygon
                  points="250,50 450,50 450,250 250,250"
                  fill="rgba(234, 179, 8, 0.2)"
                  stroke="#ca8a04"
                  strokeWidth="2"
                  className="cursor-pointer hover:opacity-80 transition-opacity"
                  onClick={() => setSelectedDistrict(districts[1] || null)}
                />
                <text x="280" y="140" fill="currentColor" fontSize="13" fontWeight="bold">
                  Lakshmi Industrial Corridor
                </text>
                <text x="320" y="160" fill="#ca8a04" fontSize="11" fontWeight="semibold">
                  Watch Active
                </text>
              </svg>

              <div className="absolute bottom-3 left-3 bg-card/90 backdrop-blur-sm border rounded px-2.5 py-1 text-[11px] text-muted-foreground">
                Click a polygon to view district metadata
              </div>
            </div>

            <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
              <span>Projection: Equirectangular offline projection</span>
              <span>Grid resolution: 10km model grid</span>
            </div>
          </CardContent>
        </Card>

        {/* Selected Area Details & Uncertainty Notice */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <MapPin className="h-4 w-4 text-primary" /> District Surveillance Profile
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
                  <div>
                    <span className="text-muted-foreground">Location Basis:</span>
                    <p className="mt-0.5">Municipal Catchment & Industrial Zoning Registry</p>
                  </div>
                </>
              ) : (
                <p className="text-muted-foreground">Select an area on the map to view data.</p>
              )}
            </CardContent>
          </Card>

          <Card className="border-amber-500/30 bg-amber-500/5">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-semibold text-amber-700 dark:text-amber-400 flex items-center gap-1.5">
                <Info className="h-3.5 w-3.5" /> Spatial Uncertainty Notice
              </CardTitle>
            </CardHeader>
            <CardContent className="text-[11px] text-muted-foreground space-y-1.5">
              <p>
                Environmental atmospheric models share coarse regional grids. Neighbouring sites within the same 10km grid receive identical screening metrics.
              </p>
              <p>
                Unlocated health records with missing workplace tags contribute to regional totals but are excluded from boundary mapping.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

