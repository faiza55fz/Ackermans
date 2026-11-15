import pandas as pd
from grid import assign_grid, cell_to_polygon


def test_grid_edge_cases():
    test_cases = [
        # (latitude, longitude, expected_cell_y, expected_cell_x, expected_cell_id)
        (34.01, -118.43, 3401, -11843, "-11843_3401"),
        (34.05, -118.75, 3405, -11875, "-11875_3405"),
        (34.08, -118.43, 3408, -11843, "-11843_3408"),
        (34.08, -118.75, 3408, -11875, "-11875_3408"),
    ]

    df = pd.DataFrame({
        "latitude": [tc[0] for tc in test_cases],
        "longitude": [tc[1] for tc in test_cases]
    })

    result = assign_grid(df, cell_size=0.01)

    print("Running Grid Assignment Tests:")
    print("-" * 65)
    for idx, (lat, lon, exp_y, exp_x, exp_id) in enumerate(test_cases):
        actual_y = result.loc[idx, "cell_y"]
        actual_x = result.loc[idx, "cell_x"]
        actual_id = result.loc[idx, "cell_id"]

        print(f"Test {idx + 1}: (lat={lat:6.2f}, lon={lon:7.2f}) -> "
              f"cell_x={actual_x:6d} (exp {exp_x:6d}), "
              f"cell_y={actual_y:4d} (exp {exp_y:4d}), "
              f"cell_id='{actual_id}'")

        assert actual_y == exp_y, f"Latitude {lat} mapped to cell_y {actual_y}, expected {exp_y}"
        assert actual_x == exp_x, f"Longitude {lon} mapped to cell_x {actual_x}, expected {exp_x}"
        assert actual_id == exp_id, f"cell_id was '{actual_id}', expected '{exp_id}'"

    # Test polygon corner coordinates rounding
    poly = cell_to_polygon(-11843, 3408, cell_size=0.01)
    minx, miny, maxx, maxy = poly.bounds
    print("\nPolygon bounds test for cell (-11843, 3408):")
    print(f"  minx: {minx:.6f}, miny: {miny:.6f}, maxx: {maxx:.6f}, maxy: {maxy:.6f}")
    assert minx == -118.43, f"Expected minx == -118.43, got {minx}"
    assert miny == 34.08, f"Expected miny == 34.08, got {miny}"
    assert maxx == -118.42, f"Expected maxx == -118.42, got {maxx}"
    assert maxy == 34.09, f"Expected maxy == 34.09, got {maxy}"

    print("-" * 65)
    print("ALL TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_grid_edge_cases()
