export type Hotspot = {
  id: number;
  lat: number;
  lng: number;
  place: string;
  sensor: "MODIS Terra" | "MODIS Aqua" | "VIIRS S-NPP" | "VIIRS NOAA-20" | "VIIRS NOAA-21";
  family: "MODIS" | "VIIRS";
  date: string;
  time: string;
  confidence: number;
  frp: number;
  period: "Day" | "Night";
  type: "Vegetation" | "Agricultural" | "Unknown";
};

export type MapCell = {
  region: string;
  cell_id: string;
  latitude: number;
  longitude: number;
  detections: number;
  mean_frp: number | null;
  max_frp: number | null;
  night_detections: number;
  modis_detections: number;
  viirs_detections: number;
  first_date: string;
  last_date: string;
};

export const pageNames = [
  "Overview",
  "MODIS",
  "VIIRS",
  "Harmonisation",
  "Wildfire Map",
  "Analytics",
  "Fire Explorer",
  "Sensor Comparison",
  "Harmonized Activity",
  "Regional Comparison",
] as const;

export type PageName = (typeof pageNames)[number];
