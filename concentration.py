"""How much of Kenya holds half its people? Rank every grid cell by density and add them up.

  python concentration.py data/ken_ppp_2020_1km_Aggregated_UNadj.tif [--blocks 1,5,10,25,50,100]

Prints the share of the land that holds 10, 25, 50, 75 and 90% of the population, the share of people on the
emptiest half, and (with --blocks) the same 50% figure after summing cells into bigger blocks, so you can see
how the answer grows with the size of your units (the modifiable areal unit problem).
"""
import argparse
import json

import numpy as np
import rasterio

R = 6371.0088  # mean Earth radius, km


def cell_areas(transform, shape):
    """True area (km²) of each row of a lon/lat grid: cells shrink away from the equator."""
    rows = np.arange(shape[0])
    top = transform.f + rows * transform.e
    bot = transform.f + (rows + 1) * transform.e
    band = R ** 2 * np.radians(abs(transform.a)) * np.abs(np.sin(np.radians(top)) - np.sin(np.radians(bot)))
    return np.repeat(band[:, None], shape[1], 1)


def concentration(pop, area):
    """Densest cells first; cumulative shares of people (cp) and of area (ca)."""
    dens = pop / area
    o = np.argsort(-dens)
    cp = np.cumsum(pop[o]) / pop.sum()
    ca = np.cumsum(area[o]) / area.sum()
    return cp, ca, dens[o]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("worldpop_tif")
    ap.add_argument("--blocks", default="")
    a = ap.parse_args()
    with rasterio.open(a.worldpop_tif) as ds:
        grid, tr, nod = ds.read(1).astype("float64"), ds.transform, ds.nodata
    valid = (grid != nod) & np.isfinite(grid) & (grid >= 0)
    area_grid = cell_areas(tr, grid.shape)
    pop, area = grid[valid], area_grid[valid]
    cp, ca, dens = concentration(pop, area)
    out = {"cells": int(pop.size), "grid_area_km2": round(float(area.sum()), 1),
           "land_share_holding": {f"{int(s * 100)}%": round(float(ca[np.searchsorted(cp, s)]) * 100, 2)
                                  for s in (0.1, 0.25, 0.5, 0.75, 0.9)},
           "density_at_half_per_km2": round(float(dens[np.searchsorted(cp, 0.5)]), 1),
           "people_on_emptiest_half_%": round(float(1 - cp[np.searchsorted(ca, 0.5)]) * 100, 2)}
    if a.blocks:
        out["half_by_block_size"] = {}
        g = np.where(valid, grid, 0)
        ar = np.where(valid, area_grid, 0)
        for b in (int(x) for x in a.blocks.split(",")):
            h, w = (g.shape[0] // b) * b, (g.shape[1] // b) * b
            P = g[:h, :w].reshape(h // b, b, w // b, b).sum((1, 3)).ravel()
            A = ar[:h, :w].reshape(h // b, b, w // b, b).sum((1, 3)).ravel()
            keep = A > 0
            c1, c2, _ = concentration(P[keep], A[keep])
            out["half_by_block_size"][f"{b} cells"] = round(float(c2[np.searchsorted(c1, 0.5)]) * 100, 2)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
