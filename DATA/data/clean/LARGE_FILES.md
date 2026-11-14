# Large and Excluded Data Files

The following data files for region `punjab_haryana` are excluded from the main branch to keep repository size lean and adhere to the 50 MB GitHub file limit.

| File Name | Size (MB) | Row Count | How to Obtain / Restore |
| :--- | :--- | :--- | :--- |
| `punjab_haryana_combined.csv` | 383.49 MB | 2,732,329 | Run python data/punjab_parts/rejoin_punjab.py after checking out the branch punjab-data-parts |
| `punjab_haryana_VIIRS.csv` | 312.70 MB | 2,228,846 | Run python data/punjab_parts/rejoin_punjab.py after checking out the branch punjab-data-parts |
| `punjab_haryana_MODIS.csv` | 70.79 MB | 503,483 | Run python data/punjab_parts/rejoin_punjab.py after checking out the branch punjab-data-parts |
| `punjab_haryana_combined.parquet` | 53.00 MB | 2,732,329 | Run python data/punjab_parts/rejoin_punjab.py after checking out the branch punjab-data-parts |
| `dropped_low_confidence_punjab_haryana_VIIRS.csv` | 52.58 MB | 364,374 | Run python data/punjab_parts/rejoin_punjab.py after checking out the branch punjab-data-parts |
| `punjab_haryana_VIIRS.parquet` | 47.53 MB | 2,228,846 | Run python data/punjab_parts/rejoin_punjab.py after checking out the branch punjab-data-parts |
| `punjab_haryana_MODIS.parquet` | 5.48 MB | 503,483 | Run python data/punjab_parts/rejoin_punjab.py after checking out the branch punjab-data-parts |
| `dropped_low_confidence_punjab_haryana_MODIS.csv` | 2.25 MB | 15,551 | Run python data/punjab_parts/rejoin_punjab.py after checking out the branch punjab-data-parts |

All binary parts and the automated SHA-256 verification rejoin script are hosted on the [`punjab-data-parts`](https://github.com/faiza55fz/Ackermans/tree/punjab-data-parts) branch.
