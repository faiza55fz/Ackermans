import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import {
  Circle,
  MapContainer,
  Marker,
  TileLayer,
  Tooltip,
  useMap,
  useMapEvents,
} from "react-leaflet";
import { Crosshair, Layers3, LocateFixed, Maximize2, Minus, Plus, Search } from "lucide-react";
import type { Hotspot } from "../data";
import "leaflet/dist/leaflet.css";

type FireMapProps = {
  hotspots: Hotspot[];
  height?: number | string;
  compact?: boolean;
  family?: "MODIS" | "VIIRS";
  heatmap?: boolean;
  drawMode?: boolean;
  onDrawPoint?: (point: [number, number]) => void;
  onSelect?: (hotspot: Hotspot) => void;
  selected?: Hotspot | null;
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

function MapController({ target }: { target: [number, number, number] | null }) {
  const map = useMap();
  useEffect(() => {
    if (target) map.flyTo([target[0], target[1]], target[2], { duration: 0.8 });
  }, [map, target]);
  return null;
}

function makeIcon(family: "MODIS" | "VIIRS", selected = false, count?: number) {
  const color = family === "MODIS" ? "#ff7b45" : "#3ac8f4";
  return L.divIcon({
    className: "fire-div-icon",
    html: count
      ? `<span class="cluster-marker" style="--marker:${color}">${count}</span>`
      : `<span class="hotspot-marker ${selected ? "is-selected" : ""}" style="--marker:${color}"><i></i></span>`,
    iconSize: count ? [40, 40] : [26, 26],
    iconAnchor: count ? [20, 20] : [13, 13],
  });
}

const locations: Record<string, [number, number, number]> = {
  california: [37.4, -120.3, 6],
  oregon: [44.0, -120.5, 6],
  washington: [47.4, -120.7, 6],
  arizona: [34.2, -111.7, 6],
  montana: [46.9, -110.3, 6],
};

export function FireMap({
  hotspots,
  height = 430,
  compact,
  family,
  heatmap,
  drawMode,
  onDrawPoint,
  onSelect,
  selected,
}: FireMapProps) {
  const [zoom, setZoom] = useState(compact ? 4 : 5);
  const [layer, setLayer] = useState<"dark" | "street">("dark");
  const [layerOpen, setLayerOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [target, setTarget] = useState<[number, number, number] | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const visible = family ? hotspots.filter((point) => point.family === family) : hotspots;
  const clustered = zoom < 5 && visible.length > 5;
  const familyCount = useMemo(
    () => ({
      MODIS: visible.filter((point) => point.family === "MODIS").length,
      VIIRS: visible.filter((point) => point.family === "VIIRS").length,
    }),
    [visible],
  );

  function searchLocation() {
    const match = Object.entries(locations).find(([name]) => query.toLowerCase().includes(name));
    if (match) setTarget(match[1]);
  }

  return (
    <div ref={wrapperRef} className={`map-shell ${drawMode ? "draw-mode" : ""}`} style={{ height }}>
      <MapContainer
        center={[39.6, -116.5]}
        zoom={compact ? 4 : 5}
        minZoom={3}
        maxZoom={12}
        zoomControl={false}
        scrollWheelZoom
      >
        <TileLayer
          key={layer}
          attribution="&copy; OpenStreetMap contributors &copy; CARTO"
          url={
            layer === "dark"
              ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              : "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          }
        />
        <MapEvents onZoom={setZoom} drawMode={drawMode} onDrawPoint={onDrawPoint} />
        <MapController target={target} />
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
        {clustered ? (
          <>
            {familyCount.MODIS > 0 && (
              <Marker position={[40.2, -119.8]} icon={makeIcon("MODIS", false, familyCount.MODIS)}>
                <Tooltip>MODIS demo observation group</Tooltip>
              </Marker>
            )}
            {familyCount.VIIRS > 0 && (
              <Marker position={[38.2, -115.3]} icon={makeIcon("VIIRS", false, familyCount.VIIRS)}>
                <Tooltip>VIIRS demo observation group</Tooltip>
              </Marker>
            )}
          </>
        ) : (
          visible.map((point) => (
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
          ))
        )}
      </MapContainer>

      {!compact && (
        <form
          className="map-search"
          onSubmit={(event) => {
            event.preventDefault();
            searchLocation();
          }}
        >
          <Search size={15} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search a location"
            aria-label="Search location"
          />
        </form>
      )}
      <div className="map-controls">
        <button title="Zoom in" onClick={() => setTarget([39.6, -116.5, Math.min(zoom + 1, 12)])}>
          <Plus size={16} />
        </button>
        <button title="Zoom out" onClick={() => setTarget([39.6, -116.5, Math.max(zoom - 1, 3)])}>
          <Minus size={16} />
        </button>
        <button title="Reset map" onClick={() => setTarget([39.6, -116.5, compact ? 4 : 5])}>
          <LocateFixed size={16} />
        </button>
        {!compact && (
          <button title="Full screen" onClick={() => wrapperRef.current?.requestFullscreen()}>
            <Maximize2 size={16} />
          </button>
        )}
      </div>
      <div className="layer-control">
        <button title="Map layers" onClick={() => setLayerOpen(!layerOpen)}>
          <Layers3 size={16} />
        </button>
        {layerOpen && (
          <div className="layer-menu">
            <button className={layer === "dark" ? "active" : ""} onClick={() => setLayer("dark")}>
              Dark terrain
            </button>
            <button
              className={layer === "street" ? "active" : ""}
              onClick={() => setLayer("street")}
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
        <b>DEMO OBSERVATIONS</b>
      </div>
    </div>
  );
}
