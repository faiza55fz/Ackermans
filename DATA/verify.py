import pandas as pd
df = pd.read_parquet("data/clean/palisades_la_combined.parquet")

print(df.shape, "\n", list(df.columns))          # expect 23 columns
print(df.dtypes)
print(df.isna().sum())                           # date, lat, lon, frp, confidence must be 0
print("dupes:", df.duplicated().sum())           # expect 0

print(df.groupby("sensor")["datetime_utc"].agg(["min","max","count"]))
print(df.groupby(["sensor","satellite"]).size())
print(df[["latitude","longitude"]].describe().loc[["min","max"]])
# box: lon -118.75..-118.40, lat 33.95..34.20

print("frp min:", df.frp.min())                  # must be >= 0
print(df.groupby(["sensor","confidence_class"]).size())
print(df.groupby(["sensor","processing"]).size())  # SP and NRT both present
print(df.is_vegetation_fire.value_counts())

yr = df.groupby(["year","sensor"]).size().unstack()
print(yr)                                        # MODIS from 2000, VIIRS from 2012
jan = df[df.date.astype(str).str[5:7]=="01"].groupby("year").size()
print(jan)                                       # 2025 should be far above other years
