/**
 * Pipeline totals from the cleaned data, 2026-11-14. Replace with API values.
 */

export interface RegionVerifiedMeta {
  total: number;
  modis: number;
  viirs: number;
  cells_025: number;
  cells_005: number;
  cells_001?: number;
  meanFrp: number;
  label: string;
  source: string;
  isAvailable: boolean;
}

export const VERIFIED_TOTALS: Record<string, RegionVerifiedMeta> = {
  all: {
    total: 2872017,
    modis: 522191,
    viirs: 2349826,
    cells_025: 94,
    cells_005: 6994,
    meanFrp: 18.2,
    label: "All Analyzed Fire Regimes",
    source: "Verified multi-region callsets (2,872,017 total detections)",
    isAvailable: true,
  },
  western_ghats_karnataka: {
    total: 133605,
    modis: 18131,
    viirs: 115474,
    cells_025: 92,
    cells_005: 1732,
    cells_001: 22975,
    meanFrp: 14.2,
    label: "Western Ghats, Karnataka (India)",
    source: "Verified cleaned dataset (western_ghats_karnataka.csv)",
    isAvailable: true,
  },
  palisades_la: {
    total: 6083,
    modis: 577,
    viirs: 5506,
    cells_025: 2,
    cells_005: 27,
    cells_001: 361,
    meanFrp: 12.1,
    label: "Pacific Palisades, California (USA)",
    source: "Verified full-year Palisades dataset (6,083 rows; pre-full-year snapshot had 4,560 rows)",
    isAvailable: true,
  },
  punjab_haryana: {
    total: 2732329,
    modis: 503483,
    viirs: 2228846,
    cells_025: 0,
    cells_005: 6810,
    cells_001: 120664,
    meanFrp: 21.4,
    label: "Punjab & Haryana (India)",
    source: "Verified agricultural fire callset (raw parts on punjab-data-parts)",
    isAvailable: true,
  },
  nsw_victoria_au: {
    total: 0,
    modis: 0,
    viirs: 0,
    cells_025: 0,
    cells_005: 0,
    meanFrp: 0,
    label: "NSW & Victoria (Australia)",
    source: "Data not available yet (pipeline download pending)",
    isAvailable: false,
  },
};

export const SENSOR_SUM_NOTE = "Sum of two sensors with different resolution; not harmonised.";
export const PIPELINE_STATIC_BADGE = "Pipeline totals (static)";
