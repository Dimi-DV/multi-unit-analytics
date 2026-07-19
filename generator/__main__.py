"""Entry point: python -m generator [--outdir data/generated] [--verify]

Pipeline order is fixed and is part of the determinism contract:
dims/seeds -> tickets -> invoices -> labor -> gl -> samples -> manifest.
One PCG64 stream, created here, passed explicitly; no other randomness exists.
"""

import argparse
import os
import sys

import numpy as np

from . import checksums, config, content, dims, gl, invoices, labor, tickets, writers
from .caldata import build_calendar


def main() -> int:
    ap = argparse.ArgumentParser(prog="generator")
    ap.add_argument("--outdir", default=config.OUT_DIR)
    ap.add_argument("--seeds", default=config.SEEDS_DIR)
    ap.add_argument("--verify", action="store_true",
                    help="verify generated facts against the committed manifest and exit")
    args = ap.parse_args()

    if args.verify:
        problems = checksums.verify(args.outdir, args.seeds)
        if problems:
            for p in problems:
                print(f"VERIFY FAIL: {p}")
            return 1
        print(f"VERIFY OK: {len(config.FACT_FILES)} fact files match seeds/manifest.sha256 "
              f"(dataset {config.DATASET_VERSION}, seed {config.SEED})")
        return 0

    os.makedirs(args.outdir, exist_ok=True)
    os.makedirs(f"{args.seeds}/samples", exist_ok=True)

    rng = np.random.Generator(np.random.PCG64(config.SEED))
    print(f"dataset {config.DATASET_VERSION} | seed {config.SEED} | "
          f"{config.START_DATE} .. {config.END_DATE}")

    seed_counts = dims.write_all(args.seeds)
    for name, cnt in seed_counts.items():
        print(f"  seeds/{name}.csv: {cnt} rows")

    cal = build_calendar()
    aggregates = {"daily_net": {}, "week_units": {}, "week_togo": {}}

    tw = writers.TableWriter(f"{args.outdir}/pos_ticket_lines.csv", tickets.TICKET_HEADER,
                             f"{args.seeds}/samples/pos_ticket_lines_sample.csv")
    tickets.generate(rng, tw, cal, aggregates)
    tw.close()
    print(f"  pos_ticket_lines.csv: {tw.count} rows")

    iw = writers.TableWriter(f"{args.outdir}/ap_invoice_lines.csv", invoices.INVOICE_HEADER,
                             f"{args.seeds}/samples/ap_invoice_lines_sample.csv")
    invoices.generate(rng, iw, aggregates)
    iw.close()
    print(f"  ap_invoice_lines.csv: {iw.count} rows")

    lw = writers.TableWriter(f"{args.outdir}/labor_daily.csv", labor.LABOR_HEADER,
                             f"{args.seeds}/samples/labor_daily_sample.csv")
    labor.generate(rng, lw, aggregates)
    lw.close()
    print(f"  labor_daily.csv: {lw.count} rows")

    gw = writers.TableWriter(f"{args.outdir}/gl_daily_sales.csv", gl.GL_HEADER,
                             f"{args.seeds}/samples/gl_daily_sales_sample.csv")
    gl.generate(rng, gw, aggregates)
    gw.close()
    print(f"  gl_daily_sales.csv: {gw.count} rows")

    checksums.write_manifest(args.outdir, args.seeds)
    print("  seeds/manifest.sha256 written")

    # structural invariants (M8 contract)
    n_eras = sum(len(loc.eras) for loc in content.LOCATIONS)
    assert n_eras == 10, "expected 10 location-code eras for 9 locations"
    gc = content.LOCATIONS[2]
    assert gc.eras[1].ticket_seq_start - gc.eras[0].ticket_seq_start > 1_000_000, \
        "re-keyed POS ticket sequence must not collide across the era boundary"
    return 0


if __name__ == "__main__":
    sys.exit(main())
