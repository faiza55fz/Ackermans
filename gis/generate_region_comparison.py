from pathlib import Path
import pandas as pd

data = [
    {
        "region": "palisades",
        "cell_size": 0.05,
        "rows": 6083,
        "modis_cells_2012_2026": 23,
        "viirs_cells_2012_2026": 27,
        "cells_seen_by_both": 22,
        "modis_cell_days": 66,
        "viirs_also": 55,
        "viirs_only": 262,
        "modis_only": 11,
        "share_modis_seen_by_viirs": 83.33
    },
    {
        "region": "palisades",
        "cell_size": 0.01,
        "rows": 6083,
        "modis_cells_2012_2026": 228,
        "viirs_cells_2012_2026": 361,
        "cells_seen_by_both": 210,
        "modis_cell_days": 332,
        "viirs_also": 260,
        "viirs_only": 579,
        "modis_only": 72,
        "share_modis_seen_by_viirs": 78.31
    },
    {
        "region": "western_ghats_karnataka",
        "cell_size": 0.05,
        "rows": 133605,
        "modis_cells_2012_2026": 1171,
        "viirs_cells_2012_2026": 1732,
        "cells_seen_by_both": 1168,
        "modis_cell_days": 8783,
        "viirs_also": 4352,
        "viirs_only": 59601,
        "modis_only": 4431,
        "share_modis_seen_by_viirs": 49.55
    },
    {
        "region": "western_ghats_karnataka",
        "cell_size": 0.01,
        "rows": 133605,
        "modis_cells_2012_2026": 7000,
        "viirs_cells_2012_2026": 22975,
        "cells_seen_by_both": 6376,
        "modis_cell_days": 11044,
        "viirs_also": 3240,
        "viirs_only": 77925,
        "modis_only": 7804,
        "share_modis_seen_by_viirs": 29.34
    },
    {
        "region": "punjab_haryana",
        "cell_size": 0.05,
        "rows": 2732329,
        "modis_cells_2012_2026": 5708,
        "viirs_cells_2012_2026": 6810,
        "cells_seen_by_both": 5656,
        "modis_cell_days": 202761,
        "viirs_also": 133329,
        "viirs_only": 783639,
        "modis_only": 69432,
        "share_modis_seen_by_viirs": 65.76
    },
    {
        "region": "punjab_haryana",
        "cell_size": 0.01,
        "rows": 2732329,
        "modis_cells_2012_2026": 73350,
        "viirs_cells_2012_2026": 120664,
        "cells_seen_by_both": 71539,
        "modis_cell_days": 285634,
        "viirs_also": 64748,
        "viirs_only": 1641821,
        "modis_only": 220886,
        "share_modis_seen_by_viirs": 22.67
    }
]

df = pd.DataFrame(data)
out_path = Path("gis/output/region_comparison.csv")
out_path.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out_path, index=False)
print("Saved region_comparison.csv:")
print(df.to_string(index=False))
