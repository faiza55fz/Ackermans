import React, { createContext, useContext, useState, useMemo } from "react";

export type SatelliteFilter = "All" | "MODIS" | "VIIRS" | "Terra" | "Aqua" | "N" | "N20" | "N21";
export type ConfidenceFilter = "nominal_high" | "high";
export type RegionFilter =
  | "western_ghats_karnataka"
  | "palisades_la"
  | "punjab_haryana"
  | "nsw_victoria_au"
  | "all";
export type DateRangeFilter = "all" | "2000-2011" | "2012-2024" | "2024-2026";

export interface FiltersState {
  region: RegionFilter;
  satellite: SatelliteFilter;
  confidence: ConfidenceFilter;
  dateRange: DateRangeFilter;
}

export interface RegionOption {
  value: RegionFilter;
  label: string;
  coordinates: [number, number];
  defaultZoom: number;
  disabled?: boolean;
  notes?: string;
}

export const REGION_OPTIONS: RegionOption[] = [
  {
    value: "western_ghats_karnataka",
    label: "Western Ghats, Karnataka (India)",
    coordinates: [14.5, 75.0],
    defaultZoom: 8,
  },
  {
    value: "palisades_la",
    label: "Pacific Palisades, California (USA)",
    coordinates: [34.05, -118.53],
    defaultZoom: 11,
    notes: "Data snapshot predates the full-year Palisades data",
  },
  {
    value: "punjab_haryana",
    label: "Punjab & Haryana (India)",
    coordinates: [30.5, 75.8],
    defaultZoom: 8,
    notes: "Raw map cells omitted for bundle size; aggregated comparison available in Analytics",
  },
  {
    value: "nsw_victoria_au",
    label: "NSW & Victoria (Australia) — Coming soon / data not available yet",
    coordinates: [-35.5, 148.0],
    defaultZoom: 6,
    disabled: true,
    notes: "Data pipeline ingestion pending",
  },
  {
    value: "all",
    label: "All Active Study Regions",
    coordinates: [23.5, 30.0],
    defaultZoom: 3,
  },
];

export const SATELLITE_OPTIONS: { value: SatelliteFilter; label: string; family: "ALL" | "MODIS" | "VIIRS" }[] = [
  { value: "All", label: "All Sensors (MODIS + VIIRS)", family: "ALL" },
  { value: "MODIS", label: "MODIS Family (Terra & Aqua - 1 km)", family: "MODIS" },
  { value: "VIIRS", label: "VIIRS Family (S-NPP, NOAA-20/21 - 375 m)", family: "VIIRS" },
  { value: "Terra", label: "MODIS Terra (EOS AM-1 - 10:30 AM)", family: "MODIS" },
  { value: "Aqua", label: "MODIS Aqua (EOS PM-1 - 1:30 PM)", family: "MODIS" },
  { value: "N", label: "VIIRS Suomi-NPP (Operational 2012)", family: "VIIRS" },
  { value: "N20", label: "VIIRS NOAA-20 / JPSS-1 (Operational 2018)", family: "VIIRS" },
  { value: "N21", label: "VIIRS NOAA-21 / JPSS-2 (Operational 2023)", family: "VIIRS" },
];

export const DATE_RANGE_OPTIONS: { value: DateRangeFilter; label: string; startYear: number; endYear: number }[] = [
  { value: "all", label: "Full Baseline (2000 – 2026)", startYear: 2000, endYear: 2026 },
  { value: "2000-2011", label: "MODIS-Only Era (2000 – 2011)", startYear: 2000, endYear: 2011 },
  { value: "2012-2024", label: "Co-Observation Window (2012 – 2024)", startYear: 2012, endYear: 2024 },
  { value: "2024-2026", label: "Recent / NRT (2024 – 2026)", startYear: 2024, endYear: 2026 },
];

export const CONFIDENCE_OPTIONS: { value: ConfidenceFilter; label: string; note: string }[] = [
  {
    value: "nominal_high",
    label: "Nominal + High (all cleaned data)",
    note: "Low-confidence detections were removed during data cleaning.",
  },
  {
    value: "high",
    label: "High only",
    note: "Strict high-confidence threshold (≥80% for MODIS; algorithm High for VIIRS).",
  },
];

interface FiltersContextType {
  filters: FiltersState;
  setFilters: React.Dispatch<React.SetStateAction<FiltersState>>;
  setRegion: (region: RegionFilter) => void;
  setSatellite: (satellite: SatelliteFilter) => void;
  setConfidence: (confidence: ConfidenceFilter) => void;
  setDateRange: (dateRange: DateRangeFilter) => void;
  resetFilters: () => void;
  currentRegionMeta: RegionOption;
  confidenceNote: string;
}

const defaultFilters: FiltersState = {
  region: "western_ghats_karnataka",
  satellite: "All",
  confidence: "nominal_high",
  dateRange: "all",
};

const FiltersContext = createContext<FiltersContextType | undefined>(undefined);

export function FiltersProvider({ children }: { children: React.ReactNode }) {
  const [filters, setFilters] = useState<FiltersState>(defaultFilters);

  const setRegion = (region: RegionFilter) => {
    const opt = REGION_OPTIONS.find((r) => r.value === region);
    if (opt?.disabled) return;
    setFilters((prev) => ({ ...prev, region }));
  };

  const setSatellite = (satellite: SatelliteFilter) => setFilters((prev) => ({ ...prev, satellite }));
  const setConfidence = (confidence: ConfidenceFilter) => setFilters((prev) => ({ ...prev, confidence }));
  const setDateRange = (dateRange: DateRangeFilter) => setFilters((prev) => ({ ...prev, dateRange }));
  const resetFilters = () => setFilters(defaultFilters);

  const currentRegionMeta = useMemo(() => {
    return REGION_OPTIONS.find((r) => r.value === filters.region) || REGION_OPTIONS[0];
  }, [filters.region]);

  const confidenceNote = useMemo(() => {
    return "Low-confidence detections were removed during data cleaning.";
  }, []);

  return (
    <FiltersContext.Provider
      value={{
        filters,
        setFilters,
        setRegion,
        setSatellite,
        setConfidence,
        setDateRange,
        resetFilters,
        currentRegionMeta,
        confidenceNote,
      }}
    >
      {children}
    </FiltersContext.Provider>
  );
}

export function useFilters() {
  const context = useContext(FiltersContext);
  if (!context) {
    throw new Error("useFilters must be used within a FiltersProvider");
  }
  return context;
}
