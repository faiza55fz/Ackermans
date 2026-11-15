import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import { Circle, MapContainer, Marker, TileLayer, Tooltip, useMapEvents } from "react-leaflet";
import {
  Crosshair,
  Layers3,
  Loader2,
  LocateFixed,
  Maximize2,
  Minus,
  Plus,
  Search,
} from "lucide-react";
import type { Hotspot, MapCell } from "../data";
import "leaflet/dist/leaflet.css";

type FireMapProps = {
  hotspots?: Hotspot[];
  cells?: MapCell[];
  height?: number | string;
  compact?: boolean;
  family?: "MODIS" | "VIIRS";
  heatmap?: boolean;
  drawMode?: boolean;
  onDrawPoint?: (point: [number, number]) => void;
  onSelect?: (hotspot: Hotspot) => void;
  selected?: Hotspot | null;
  onSelectCell?: (cell: MapCell) => void;
  selectedCell?: MapCell | null;
  center?: [number, number];
  zoomLevel?: number;
};

function MapEvents({
  onZoom,
  onDrawPoint,
  drawMode,
}: {
  onZoom: (z: number) => void;
  onDrawPoint?: (point: [number, number]) => void;
  drawMode?: boolean;
}) {
  useMapEvents({
    zoomend: (event) => onZoom(event.target.getZoom()),
    click: (event) => {
      if (drawMode) onDrawPoint?.([event.latlng.lat, event.latlng.lng]);
    },
  });
  return null;
}

function makeIcon(family: "MODIS" | "VIIRS" | "MIXED", selected = false, count?: number) {
  let color = "#ff7547"; // MODIS orange
  if (family === "VIIRS") color = "#36c9f4"; // VIIRS cyan
  if (family === "MIXED") color = "#ffb84d"; // Harmonized gold

  return L.divIcon({
    className: "fire-div-icon",
    html: count
      ? `<span class="cluster-marker" style="--marker:${color}">${count}</span>`
      : `<span class="hotspot-marker ${selected ? "is-selected" : ""}" style="--marker:${color}"><i></i></span>`,
    iconSize: count ? [40, 40] : [26, 26],
    iconAnchor: count ? [20, 20] : [13, 13],
  });
}

// Built-in catalog covering all US states, territories, Canadian provinces and key fire regions
const knownLocations: Record<string, [number, number, number]> = {
  // FireTrace Project Study Regions
  "western ghats": [14.5, 75.0, 8],
  "karnataka": [14.5, 75.0, 8],
  "punjab": [30.8, 75.8, 8],
  "haryana": [29.0, 76.0, 8],
  "punjab & haryana": [30.5, 75.8, 8],
  "palisades": [34.05, -118.53, 11],
  "pacific palisades": [34.05, -118.53, 11],
  "india": [20.59, 78.96, 5],

  // Western US Fire Regions & Datasets
  "northern california": [40.0, -121.5, 7],
  "central california": [37.2, -119.8, 7],
  "southern california": [34.5, -118.5, 7],
  "sierra nevada": [38.5, -120.2, 7],
  klamath: [41.3, -123.3, 7],
  california: [37.2, -119.5, 6],
  oregon: [44.0, -120.5, 6],
  washington: [47.4, -120.7, 6],
  arizona: [34.2, -111.7, 6],
  montana: [46.9, -110.3, 6],
  idaho: [44.4, -114.7, 6],
  nevada: [39.8, -117.2, 6],
  "new mexico": [34.5, -106.0, 6],
  colorado: [39.0, -105.5, 6],
  utah: [39.3, -111.7, 6],
  wyoming: [43.0, -107.5, 6],
  alaska: [64.2, -152.5, 5],
  hawaii: [20.8, -156.3, 7],
  texas: [31.5, -99.5, 6],
  "pacific northwest": [45.5, -120.5, 6],
  "great basin": [39.5, -116.0, 6],
  "rocky mountains": [43.5, -110.0, 6],
  yellowstone: [44.4, -110.6, 8],
  yosemite: [37.8, -119.5, 8],

  // Remaining US States
  alabama: [32.8, -86.8, 6],
  arkansas: [34.9, -92.4, 6],
  connecticut: [41.6, -72.7, 8],
  delaware: [39.0, -75.5, 8],
  florida: [28.5, -82.4, 6],
  georgia: [32.8, -83.5, 6],
  illinois: [40.0, -89.2, 6],
  indiana: [39.8, -86.2, 6],
  iowa: [42.0, -93.5, 6],
  kansas: [38.5, -98.3, 6],
  kentucky: [37.8, -85.7, 6],
  louisiana: [31.1, -91.9, 6],
  maine: [45.3, -69.2, 6],
  maryland: [39.0, -76.8, 7],
  massachusetts: [42.2, -71.8, 8],
  michigan: [44.3, -85.6, 6],
  minnesota: [46.3, -94.3, 6],
  mississippi: [32.7, -89.7, 6],
  missouri: [38.5, -92.5, 6],
  nebraska: [41.5, -99.8, 6],
  "new hampshire": [43.7, -71.6, 7],
  "new jersey": [40.1, -74.5, 8],
  "new york": [42.9, -75.5, 6],
  "north carolina": [35.6, -79.4, 6],
  "north dakota": [47.5, -100.5, 6],
  ohio: [40.4, -82.8, 6],
  oklahoma: [35.5, -97.5, 6],
  pennsylvania: [40.9, -77.8, 6],
  "rhode island": [41.7, -71.5, 9],
  "south carolina": [33.9, -80.9, 6],
  "south dakota": [44.4, -100.2, 6],
  tennessee: [35.8, -86.4, 6],
  vermont: [44.0, -72.7, 7],
  virginia: [37.5, -78.9, 6],
  "west virginia": [38.6, -80.6, 7],
  wisconsin: [44.5, -89.8, 6],

  // Canada & Key Global Fire-Prone Regions
  "british columbia": [53.7, -127.6, 5],
  alberta: [53.9, -116.5, 5],
  ontario: [51.2, -85.3, 5],
  quebec: [52.9, -73.5, 5],
  canada: [56.1, -106.3, 4],
  amazon: [-3.4, -62.2, 5],
  brazil: [-14.2, -51.9, 4],
  australia: [-25.2, 133.7, 4],
  indonesia: [-0.7, 113.9, 5],
  siberia: [60.0, 105.0, 4],
  mediterranean: [38.0, 15.0, 5],
};

type ClusterItem =
  | {
      type: "single";
      point: Hotspot;
    }
  | {
      type: "cluster";
      id: string;
      lat: number;
      lng: number;
      points: Hotspot[];
      family: "MODIS" | "VIIRS" | "MIXED";
      modisCount: number;
      viirsCount: number;
    };

function clusterHotspots(points: Hotspot[], zoom: number): ClusterItem[] {
  // At zoom >= 5, show individual hotspot markers
  if (zoom >= 5 || points.length <= 1) {
    return points.map((point) => ({ type: "single", point }));
  }

  // Distance threshold in degrees based on zoom level:
  // Zoom 3: ~7.5 degrees, Zoom 4: ~4.0 degrees
  const threshold = zoom === 3 ? 7.5 : 4.0;
  const groups: Array<{ lat: number; lng: number; points: Hotspot[] }> = [];

  for (const point of points) {
    let closestIndex = -1;
    let minDistance = Infinity;

    for (let i = 0; i < groups.length; i++) {
      const g = groups[i];
      // Great-circle / spherical distance approximation
      const cosLat = Math.cos(((g.lat + point.lat) / 2) * (Math.PI / 180));
      const dist = Math.hypot(g.lat - point.lat, (g.lng - point.lng) * cosLat);
      if (dist < threshold && dist < minDistance) {
        minDistance = dist;
        closestIndex = i;
      }
    }

    if (closestIndex >= 0) {
      groups[closestIndex].points.push(point);
      // Recalculate true centroid of the group
      const count = groups[closestIndex].points.length;
      groups[closestIndex].lat =
        groups[closestIndex].points.reduce((sum, p) => sum + p.lat, 0) / count;
      groups[closestIndex].lng =
        groups[closestIndex].points.reduce((sum, p) => sum + p.lng, 0) / count;
    } else {
      groups.push({
        lat: point.lat,
        lng: point.lng,
        points: [point],
      });
    }
  }

  return groups.map((g, index) => {
    if (g.points.length === 1) {
      return { type: "single", point: g.points[0] };
    }
    const modisCount = g.points.filter((p) => p.family === "MODIS").length;
    const viirsCount = g.points.filter((p) => p.family === "VIIRS").length;
    const family: "MODIS" | "VIIRS" | "MIXED" =
      modisCount > 0 && viirsCount > 0 ? "MIXED" : modisCount > 0 ? "MODIS" : "VIIRS";

    return {
      type: "cluster",
      id: `cluster-${zoom}-${index}`,
      lat: g.lat,
      lng: g.lng,
      points: g.points,
      family,
      modisCount,
      viirsCount,
    };
  });
}

export function FireMap({
  hotspots = [],
  cells,
  height = 430,
  compact,
  family,
  heatmap,
  drawMode,
  onDrawPoint,
  onSelect,
  selected,
  onSelectCell,
  selectedCell,
  center,
  zoomLevel,
}: FireMapProps) {
  const [map, setMap] = useState<L.Map | null>(null);
  const [zoom, setZoom] = useState(zoomLevel ?? (compact ? 4 : 5));
  const [layer, setLayer] = useState<"dark" | "street">("dark");
  const [layerOpen, setLayerOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [searchStatus, setSearchStatus] = useState<"idle" | "searching" | "not-found">("idle");
  const wrapperRef = useRef<HTMLDivElement>(null);

  const defaultCenter: [number, number] = center ?? [39.6, -116.5];
  const defaultZoom = zoomLevel ?? (compact ? 4 : 5);

  useEffect(() => {
    if (map && center) {
      map.flyTo(center, zoomLevel ?? (compact ? 5 : 8), { duration: 0.8 });
    }
  }, [map, center, zoomLevel, compact]);

  const visible = useMemo(
    () => (family ? hotspots.filter((point) => point.family === family) : hotspots),
    [family, hotspots],
  );

  const clusterItems = useMemo(() => clusterHotspots(visible, zoom), [visible, zoom]);

  // Coordinate parser (e.g. "39.42, -121.31" or "39.42 -121.31")
  function parseCoordinates(input: string): [number, number] | null {
    const match = input.trim().match(/^(-?\d+(?:\.\d+)?)[,\s]+(-?\d+(?:\.\d+)?)$/);
    if (!match) return null;
    const lat = parseFloat(match[1]);
    const lng = parseFloat(match[2]);
    if (lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
      return [lat, lng];
    }
    return null;
  }

  async function handleSearch(event: React.FormEvent) {
    event.preventDefault();
    const cleanQuery = query.trim().toLowerCase();
    if (!cleanQuery || !map) return;

    // 1. Check for direct coordinates
    const coords = parseCoordinates(cleanQuery);
    if (coords) {
      map.flyTo(coords, 7, { duration: 0.8 });
      setSearchStatus("idle");
      return;
    }

    // 2. Check hotspot place names in dataset
    const matchedHotspot = hotspots.find((h) => h.place.toLowerCase().includes(cleanQuery));
    if (matchedHotspot) {
      map.flyTo([matchedHotspot.lat, matchedHotspot.lng], 7, { duration: 0.8 });
      onSelect?.(matchedHotspot);
      setSearchStatus("idle");
      return;
    }

    // 3. Check built-in geographic dictionary
    const matchEntry = Object.entries(knownLocations).find(
      ([name]) => cleanQuery.includes(name) || name.includes(cleanQuery),
    );
    if (matchEntry) {
      const [lat, lng, targetZoom] = matchEntry[1];
      map.flyTo([lat, lng], targetZoom, { duration: 0.8 });
      setSearchStatus("idle");
      return;
    }

    // 4. Fallback to open Nominatim geocoding
    setSearchStatus("searching");
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3500);

      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(cleanQuery)}`,
        {
          signal: controller.signal,
          headers: { Accept: "application/json" },
        },
      );
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        if (data && data.length > 0) {
          const lat = parseFloat(data[0].lat);
          const lon = parseFloat(data[0].lon);
          map.flyTo([lat, lon], 7, { duration: 0.8 });
          setSearchStatus("idle");
          return;
        }
      }
      setSearchStatus("not-found");
    } catch {
      setSearchStatus("not-found");
    }
  }

  function handleReset() {
    if (map) {
      map.flyTo(defaultCenter, defaultZoom, { duration: 0.8 });
    }
    setQuery("");
    setSearchStatus("idle");
  }

  function handleZoomIn() {
    if (map) {
      map.zoomIn();
    }
  }

  function handleZoomOut() {
    if (map) {
      map.zoomOut();
    }
  }

  return (
    <div ref={wrapperRef} className={`map-shell ${drawMode ? "draw-mode" : ""}`} style={{ height }}>
      <MapContainer
        ref={setMap}
        center={defaultCenter}
        zoom={defaultZoom}
        minZoom={3}
        maxZoom={12}
        zoomControl={false}
        scrollWheelZoom
      >
        {layer === "dark" ? (
          <>
            <TileLayer
              key="esri-dark-base"
              attribution='&copy; <a href="https://www.esri.com/" target="_blank" rel="noreferrer">Esri</a> &copy; OpenStreetMap contributors'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
              maxZoom={16}
            />
            <TileLayer
              key="esri-dark-ref"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}"
              maxZoom={16}
            />
          </>
        ) : (
          <TileLayer
            key="osm-street"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={19}
          />
        )}

        <MapEvents onZoom={setZoom} drawMode={drawMode} onDrawPoint={onDrawPoint} />

        {cells?.map((cell) => {
          const isSelected = selectedCell?.cell_id === cell.cell_id;
          const isConsensus = cell.modis_detections > 0 && cell.viirs_detections > 0;
          const isViirsOnly = cell.modis_detections === 0 && cell.viirs_detections > 0;
          const fillColor = isConsensus ? "#ffb84d" : isViirsOnly ? "#36c9f4" : "#ff7547";
          const radius = Math.max(3000, Math.min(22000, Math.sqrt(cell.detections) * 1100));

          return (
            <Circle
              key={`grid-cell-${cell.cell_id}`}
              center={[cell.latitude, cell.longitude]}
              radius={radius}
              pathOptions={{
                color: isSelected ? "#ffffff" : fillColor,
                weight: isSelected ? 3 : 1.5,
                fillColor,
                fillOpacity: isSelected ? 0.75 : 0.42,
              }}
              eventHandlers={{
                click: () => onSelectCell?.(cell),
              }}
            >
              <Tooltip direction="top" offset={[0, -10]}>
                <strong>Grid Cell: {cell.cell_id}</strong>
                <br />
                <span>{cell.detections.toLocaleString()} Detections</span>
                <br />
                <span style={{ color: "#ff7547" }}>{cell.modis_detections} MODIS</span>
                <span> · </span>
                <span style={{ color: "#36c9f4" }}>{cell.viirs_detections} VIIRS</span>
                {cell.mean_frp !== null && (
                  <>
                    <br />
                    <span>Mean FRP: {cell.mean_frp} MW</span>
                  </>
                )}
                <br />
                <span style={{ opacity: 0.8, fontSize: "10px" }}>
                  {cell.first_date} to {cell.last_date}
                </span>
              </Tooltip>
            </Circle>
          );
        })}

        {heatmap &&
          visible.map((point) => (
            <Circle
              key={`heat-${point.id}`}
              center={[point.lat, point.lng]}
              radius={point.frp * 1500}
              pathOptions={{
                color: "transparent",
                fillColor: point.family === "MODIS" ? "#ff5c35" : "#ffb23d",
                fillOpacity: 0.14,
              }}
            />
          ))}

        {clusterItems.map((item) => {
          if (item.type === "cluster") {
            return (
              <Marker
                key={item.id}
                position={[item.lat, item.lng]}
                icon={makeIcon(item.family, false, item.points.length)}
                eventHandlers={{
                  click: () => {
                    if (map) {
                      map.flyTo([item.lat, item.lng], Math.max(zoom + 2, 6), { duration: 0.6 });
                    }
                  },
                }}
              >
                <Tooltip direction="top" offset={[0, -10]}>
                  <strong>Observation Group ({item.points.length} detections)</strong>
                  <br />
                  {item.modisCount > 0 && <span>{item.modisCount} MODIS</span>}
                  {item.modisCount > 0 && item.viirsCount > 0 && <span> · </span>}
                  {item.viirsCount > 0 && <span>{item.viirsCount} VIIRS</span>}
                  <br />
                  <span style={{ opacity: 0.8, fontSize: "10px" }}>Click to zoom in</span>
                </Tooltip>
              </Marker>
            );
          }

          const point = item.point;
          return (
            <Marker
              key={point.id}
              position={[point.lat, point.lng]}
              icon={makeIcon(point.family, selected?.id === point.id)}
              eventHandlers={{ click: () => onSelect?.(point) }}
            >
              <Tooltip direction="top" offset={[0, -10]}>
                <strong>{point.place}</strong>
                <br />
                {point.sensor} · {point.frp} MW
              </Tooltip>
            </Marker>
          );
        })}
      </MapContainer>

      {!compact && (
        <form
          className="map-search"
          onSubmit={handleSearch}
          style={{
            borderColor: searchStatus === "not-found" ? "#ff7547" : undefined,
          }}
        >
          {searchStatus === "searching" ? (
            <Loader2 size={15} className="animate-spin text-cyan-400" />
          ) : (
            <Search size={15} />
          )}
          <input
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              if (searchStatus !== "idle") setSearchStatus("idle");
            }}
            placeholder={searchStatus === "not-found" ? "Location not found" : "Search a location"}
            aria-label="Search location"
          />
        </form>
      )}

      <div className="map-controls">
        <button type="button" title="Zoom in" onClick={handleZoomIn}>
          <Plus size={16} />
        </button>
        <button type="button" title="Zoom out" onClick={handleZoomOut}>
          <Minus size={16} />
        </button>
        <button type="button" title="Reset map" onClick={handleReset}>
          <LocateFixed size={16} />
        </button>
        {!compact && (
          <button
            type="button"
            title="Full screen"
            onClick={() => wrapperRef.current?.requestFullscreen()}
          >
            <Maximize2 size={16} />
          </button>
        )}
      </div>

      <div className="layer-control">
        <button type="button" title="Map layers" onClick={() => setLayerOpen(!layerOpen)}>
          <Layers3 size={16} />
        </button>
        {layerOpen && (
          <div className="layer-menu">
            <button
              type="button"
              className={layer === "dark" ? "active" : ""}
              onClick={() => {
                setLayer("dark");
                setLayerOpen(false);
              }}
            >
              Dark terrain
            </button>
            <button
              type="button"
              className={layer === "street" ? "active" : ""}
              onClick={() => {
                setLayer("street");
                setLayerOpen(false);
              }}
            >
              Street map
            </button>
          </div>
        )}
      </div>

      {drawMode && (
        <div className="draw-hint">
          <Crosshair size={14} /> Click map to add AOI vertices
        </div>
      )}

      <div className="map-legend">
        <span>
          <i className="legend-dot modis" /> MODIS
        </span>
        <span>
          <i className="legend-dot viirs" /> VIIRS
        </span>
        <b>OBSERVATIONS</b>
      </div>
    </div>
  );
}
