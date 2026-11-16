#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ingest Mysteel (钢联) Excel exports and render social/port inventory seasonal charts.

Usage (from repo root):
  python3 ingest_mysteel.py
  python3 ingest_mysteel.py --charts-only
  python3 ingest_mysteel.py --src /workspace/vendor-data/mysteel

Looks for 钢联 workbooks in /workspace/vendor-data/mysteel/*.xlsx
  (sheet '导出数据': row1 title, row2 指标名称, row3 单位, then dates in col A).

Writes processed CSVs and a latest-value snapshot to
  /workspace/vendor-data/mysteel/csv/  — outside the public repo. Do not commit
  raw xlsx or these CSVs; they are paid Mysteel series.

Writes public SVG/HTML fragments to scans/charts/:
  RB_social_season.svg/.html
  I_port_season.svg/.html
  JM_port_season.svg/.html
  J_port_season.svg/.html

Evening routine: if a new 钢联 export has been dropped into the vendor folder,
run this (or update_inventory.py, which calls render_if_available) before
build_scan_html.py. build_scan_html auto-appends these charts after the
warehouse-receipt chart when it sees [[chart:RB]], [[chart:I]], [[chart:JM]]
or [[chart:J]].
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from update_inventory import svg_chart, to_doy_series

ROOT = Path(__file__).resolve().parent
CHARTS = ROOT / "scans" / "charts"
DEFAULT_VENDOR = Path("/workspace/vendor-data/mysteel")
CSV_SUBDIR = "csv"

# Stable keys for caches and the latest-value snapshot used by the daily writeup.
# match = exact 指标名称 in the 钢联 export.
SERIES_CATALOG: list[dict] = [
    # --- rebar ---
    dict(key="RB_output", match="螺纹钢：建筑钢材钢铁企业：实际产量：中国（周）", product="RB"),
    dict(key="RB_operating_rate", match="螺纹钢：建筑钢材钢铁企业：开工率：中国（周）", product="RB"),
    dict(key="RB_utilization", match="螺纹钢：建筑钢材钢铁企业：产能利用率：中国（周）", product="RB"),
    dict(key="RB_total_inventory", match="螺纹钢：库存：中国（周）", product="RB"),
    dict(key="RB_mill_inventory", match="螺纹钢：建筑钢材钢铁企业：厂内库存：中国（周）", product="RB"),
    dict(key="RB_social_35city", match="螺纹钢：35个城市：社会库存：中国（周）", product="RB"),
    dict(key="RB_social_26city", match="螺纹钢：26个城市：社会库存：中国（周）", product="RB"),
    dict(key="RB_bf_cash_profit", match="Mysteel：螺纹钢：高炉：现金利润：中国（日）", product="RB"),
    dict(key="hot_metal_output_247", match="247家钢铁企业：铁水：日均产量：中国（周）", product="RB"),
    dict(key="hot_metal_cost_jiangsu_tax", match="铁水：含税成本：江苏（日）", product="RB"),
    dict(key="hot_metal_cost_jiangsu_ex_tax", match="铁水：不含税成本：江苏（日）", product="RB"),
    # --- iron ore ---
    dict(key="I_arrival_26port", match="铁矿：到港量：26个港口（周）", product="I"),
    dict(key="I_arrival_45port", match="铁矿：到港量：45个港口（周）", product="I"),
    dict(key="I_arrival_47port", match="铁矿：到港量：47个港口（周）", product="I"),
    dict(key="I_arrival_north", match="铁矿：到港量：北方港口（周）", product="I"),
    dict(key="I_discharge_47port", match="铁矿：进口：日均疏港量合计：47个港口（周）", product="I"),
    dict(key="I_discharge_45port", match="铁矿：进口：日均疏港量合计：45个港口（周）", product="I"),
    dict(key="I_discharge_41port", match="铁矿：进口：日均疏港量合计：41个港口（周）", product="I"),
    dict(key="I_port_47", match="铁矿：进口：库存：47个港口（周）", product="I"),
    dict(key="I_port_47_lump", match="块矿：进口：库存：47个港口（周）", product="I"),
    dict(key="I_port_47_pellet", match="球团：进口：库存：47个港口（周）", product="I"),
    dict(key="I_port_47_concentrate", match="铁精粉：进口：库存：47个港口（周）", product="I"),
    dict(key="I_port_47_australia", match="铁矿：澳大利亚产：库存：47个港口（周）", product="I"),
    dict(key="I_port_47_brazil", match="铁矿：巴西产：库存：47个港口（周）", product="I"),
    # --- coking coal ---
    dict(key="JM_mine_clean_523", match="精煤：523家样本矿山：库存（周）", product="JM"),
    dict(key="JM_mine_raw_523", match="原煤：523家样本矿山：库存（周）", product="JM"),
    dict(key="JM_coke_plant_full", match="炼焦煤：全样本：独立焦化企业：库存：中国（周）", product="JM"),
    dict(key="JM_coke_plant_230", match="炼焦煤：230家独立焦化厂：库存：中国（周）", product="JM"),
    dict(key="JM_steel_mill_247_old", match="炼焦煤：247家钢铁企业：库存：中国：老口径（周）", product="JM",
         note="老口径"),
    dict(key="JM_coke_plant_full_days", match="炼焦煤：全样本：独立焦化企业：库存可用天数：中国（周）", product="JM"),
    dict(key="JM_coke_plant_230_days", match="炼焦煤：230家独立焦化厂：库存可用天数：中国（周）", product="JM"),
    dict(key="JM_steel_mill_247_days_old", match="炼焦煤：247家钢铁企业：库存可用天数：中国：老口径（周）", product="JM",
         note="老口径"),
    dict(key="JM_port_import", match="炼焦煤：进口：港口库存（周）", product="JM"),
    # --- coke ---
    dict(key="J_coke_plant_230", match="焦炭：230家独立焦化厂：库存：中国（周）", product="J"),
    dict(key="J_steel_mill_247", match="焦炭：247家钢铁企业：库存：中国（周）", product="J"),
    dict(key="J_steel_mill_247_days", match="焦炭：247家钢铁企业：库存可用天数：中国（周）", product="J"),
    dict(key="J_port", match="焦炭：港口库存：中国（周）", product="J"),
    dict(key="J_coke_plant_230_util", match="焦炭：230家独立焦化厂：产能利用率：中国（周）", product="J"),
    dict(key="J_coke_profit", match="独立焦化企业：吨焦平均利润：中国（周）", product="J"),
]

# One primary seasonal chart per product. Optional extras omitted to avoid clutter.
CHART_SPECS: list[dict] = [
    dict(
        code="RB",
        kind="social",
        series_key="RB_social_35city",
        title="螺纹钢 35 城市社会库存季节性",
        unit="万吨",
        extra_note="",
    ),
    dict(
        code="I",
        kind="port",
        series_key="I_port_47",
        title="铁矿 47 港进口库存季节性",
        unit="万吨",
        extra_note="该序列自 2021 年 12 月起，季节对比大约只有五年。",
    ),
    dict(
        code="JM",
        kind="port",
        series_key="JM_port_import",
        title="焦煤进口港口库存季节性",
        unit="万吨",
        extra_note="",
    ),
    dict(
        code="J",
        kind="port",
        series_key="J_port",
        title="焦炭港口库存季节性",
        unit="万吨",
        extra_note="",
    ),
]


def _parse_date(v) -> date | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, pd.Timestamp):
        if pd.isna(v):
            return None
        return v.date()
    s = str(v).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(s[:10].replace("/", "-") if fmt != "%Y%m%d" else s[:8], fmt).date()
        except ValueError:
            continue
    try:
        return pd.to_datetime(v).date()
    except Exception:
        return None


def _to_float(v) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if pd.isna(v):
            return None
        return float(v)
    s = str(v).strip().replace(",", "")
    if not s or s in {"--", "—", "na", "NA", "N/A"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_mysteel_workbook(path: Path) -> dict[str, dict]:
    """Parse one 钢联 '导出数据' sheet into {indicator_name: {unit, points}}.

    points is a list of (date, value) with missing cells dropped, not filled.
    """
    xl = pd.ExcelFile(path, engine="openpyxl")
    sheet = "导出数据" if "导出数据" in xl.sheet_names else xl.sheet_names[0]
    raw = pd.read_excel(xl, sheet_name=sheet, header=None, engine="openpyxl")
    if raw.empty or raw.shape[0] < 4:
        raise ValueError(f"{path.name}: sheet too short")
    title = raw.iat[0, 0]
    names = [raw.iat[1, j] for j in range(raw.shape[1])]
    units = [raw.iat[2, j] for j in range(raw.shape[1])]
    if names[0] not in ("指标名称", None) and title != "钢联数据":
        # still accept, but flag
        pass
    out: dict[str, dict] = {}
    for j, name in enumerate(names):
        if j == 0 or not isinstance(name, str) or not name.strip():
            continue
        pts = []
        for i in range(3, len(raw)):
            d = _parse_date(raw.iat[i, 0])
            v = _to_float(raw.iat[i, j])
            if d is None or v is None:
                continue
            pts.append((d, v))
        unit = units[j] if j < len(units) and isinstance(units[j], str) else ""
        out[name.strip()] = {
            "indicator": name.strip(),
            "unit": unit,
            "points": pts,
            "source_file": path.name,
        }
    return out


def load_all_workbooks(vendor_dir: Path) -> dict[str, dict]:
    files = sorted(
        p for p in vendor_dir.glob("*.xlsx")
        if not p.name.startswith("~$")
    )
    if not files:
        raise FileNotFoundError(f"no .xlsx in {vendor_dir}")
    merged: dict[str, dict] = {}
    for path in files:
        parsed = parse_mysteel_workbook(path)
        print(f"  read {path.name}: {len(parsed)} series")
        merged.update(parsed)
    return merged


def catalog_by_match() -> dict[str, dict]:
    return {s["match"]: s for s in SERIES_CATALOG}


def points_to_df(points: list[tuple[date, float]], unit: str, indicator: str) -> pd.DataFrame:
    df = pd.DataFrame(points, columns=["date", "value"])
    df["date"] = pd.to_datetime(df["date"])
    df["unit"] = unit
    df["indicator"] = indicator
    df["source"] = "mysteel"
    return df.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)


def yoy_point(df: pd.DataFrame, asof: pd.Timestamp, window_days: int = 10):
    target = asof - pd.DateOffset(years=1)
    if df.empty:
        return None
    tmp = df.copy()
    tmp["delta"] = (tmp["date"] - target).abs()
    row = tmp.loc[tmp["delta"].idxmin()]
    if row["delta"] > timedelta(days=window_days):
        return None
    return row


def fmt_num(v: float) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if abs(v) >= 1000:
        s = f"{v:,.2f}"
    else:
        s = f"{v:.3f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def snapshot_row(df: pd.DataFrame, meta: dict) -> dict:
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else None
    asof = pd.Timestamp(last["date"])
    yoy = yoy_point(df, asof)
    wow = None if prev is None else float(last["value"]) - float(prev["value"])
    yoy_pct = None
    yoy_date = None
    yoy_val = None
    if yoy is not None and float(yoy["value"]) != 0:
        yoy_val = float(yoy["value"])
        yoy_date = pd.Timestamp(yoy["date"]).date().isoformat()
        yoy_pct = (float(last["value"]) - yoy_val) / yoy_val * 100.0
    note = meta.get("note") or ""
    return {
        "key": meta["key"],
        "indicator": meta["match"],
        "product": meta["product"],
        "unit": df.iloc[0]["unit"],
        "first_date": pd.Timestamp(df.iloc[0]["date"]).date().isoformat(),
        "last_date": asof.date().isoformat(),
        "last": float(last["value"]),
        "n": int(len(df)),
        "prev_date": None if prev is None else pd.Timestamp(prev["date"]).date().isoformat(),
        "prev": None if prev is None else float(prev["value"]),
        "wow": wow,
        "yoy_date": yoy_date,
        "yoy_value": yoy_val,
        "yoy_pct": None if yoy_pct is None else round(yoy_pct, 1),
        "note": note,
        "source": "Mysteel/钢联",
    }


def write_caches(frames: dict[str, pd.DataFrame], snapshots: list[dict], csv_dir: Path) -> None:
    csv_dir.mkdir(parents=True, exist_ok=True)
    for key, df in frames.items():
        out = csv_dir / f"{key}.csv"
        save = df.copy()
        save["date"] = save["date"].dt.strftime("%Y-%m-%d")
        save.to_csv(out, index=False)
    latest = {
        "generated": date.today().isoformat(),
        "source": "Mysteel/钢联",
        "vendor_dir": str(csv_dir.parent),
        "series": {row["key"]: row for row in snapshots},
    }
    (csv_dir / "latest.json").write_text(
        json.dumps(latest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  wrote {len(frames)} csv + latest.json -> {csv_dir}")


def load_cached_frames(csv_dir: Path) -> dict[str, pd.DataFrame]:
    frames = {}
    for meta in SERIES_CATALOG:
        path = csv_dir / f"{meta['key']}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path)
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        frames[meta["key"]] = df.dropna(subset=["value"])
    return frames


def render_chart(spec: dict, df: pd.DataFrame, meta: dict) -> dict:
    CHARTS.mkdir(parents=True, exist_ok=True)
    series_df = df[["date", "value"]].copy()
    by = to_doy_series(series_df, 1.0)
    by = {y: pts for y, pts in by.items() if pts}
    if not by:
        raise ValueError(f"{spec['series_key']}: no points to plot")
    years = sorted(by.keys())
    last = series_df.dropna(subset=["value"]).iloc[-1]
    last_val = float(last["value"])
    last_d = pd.Timestamp(last["date"]).date()
    indicator = meta["match"]
    end_note = (
        f"口径：钢联（Mysteel）{indicator}｜"
        f"{years[0]}–{years[-1]}｜截至 {last_d} 约 {fmt_num(last_val)} {spec['unit']}"
    )
    extra = (spec.get("extra_note") or "").strip()
    if extra:
        end_note = end_note + "。" + extra
    note = (meta.get("note") or "").strip()
    if note and note not in end_note:
        end_note = end_note + f"。{note}"
    frag_id = f"{spec['code']}_{spec['kind']}"
    title = spec["title"]
    svg = svg_chart(
        frag_id,
        title,
        by,
        spec["unit"],
        "钢联（Mysteel）",
        end_note,
    )
    svg_path = CHARTS / f"{frag_id}_season.svg"
    svg_path.write_text(svg, encoding="utf-8")
    frag = (
        f'<figure class="season-chart" data-symbol="{frag_id}" '
        f'data-kind="{spec["kind"]}" id="chart-{frag_id}">'
        f"{svg}"
        f"<figcaption>{end_note}</figcaption>"
        f"</figure>\n"
    )
    html_path = CHARTS / f"{frag_id}_season.html"
    html_path.write_text(frag, encoding="utf-8")
    print(
        f"OK {frag_id}: {years[0]}-{years[-1]} n={len(series_df)} "
        f"last={fmt_num(last_val)} {spec['unit']}"
    )
    return {
        "ok": True,
        "id": frag_id,
        "years": f"{years[0]}-{years[-1]}",
        "n": int(len(series_df)),
        "last": last_val,
        "last_date": last_d.isoformat(),
        "svg": str(svg_path.relative_to(ROOT)),
        "indicator": indicator,
    }


def ingest(vendor_dir: Path) -> tuple[dict[str, pd.DataFrame], list[dict]]:
    raw = load_all_workbooks(vendor_dir)
    by_match = catalog_by_match()
    frames: dict[str, pd.DataFrame] = {}
    snapshots: list[dict] = []
    missing = []
    unmatched_extra = [name for name in raw if name not in by_match]
    for name, payload in raw.items():
        meta = by_match.get(name)
        if not meta:
            continue
        df = points_to_df(payload["points"], payload["unit"], name)
        if df.empty:
            missing.append(name)
            continue
        frames[meta["key"]] = df
        snapshots.append(snapshot_row(df, meta))
    for meta in SERIES_CATALOG:
        if meta["key"] not in frames:
            missing.append(meta["match"])
    if unmatched_extra:
        print(f"  stored-as-csv skipped (not in catalog, {len(unmatched_extra)}):")
        for name in unmatched_extra:
            # still write a sidecar csv under a slug so future writeups can use them
            slug = "extra_" + re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", name).strip("_")[:80]
            df = points_to_df(raw[name]["points"], raw[name]["unit"], name)
            frames[slug] = df
            print(f"    extra {name} -> {slug}.csv n={len(df)}")
    if missing:
        print("  missing catalog series:")
        for name in missing:
            print(f"    - {name}")
    return frames, snapshots


def render_charts(frames: dict[str, pd.DataFrame]) -> dict:
    by_key = {s["key"]: s for s in SERIES_CATALOG}
    manifest = {}
    for spec in CHART_SPECS:
        df = frames.get(spec["series_key"])
        if df is None or df.empty:
            print(f"SKIP {spec['code']}_{spec['kind']}: no cached series {spec['series_key']}")
            manifest[spec["series_key"]] = {"ok": False, "reason": "missing series"}
            continue
        manifest[spec["series_key"]] = render_chart(spec, df, by_key[spec["series_key"]])
    return manifest


def render_if_available(vendor_dir: Path | None = None) -> dict | None:
    """Hook for update_inventory.py: no-op if vendor workbooks/CSVs are absent."""
    vendor_dir = vendor_dir or DEFAULT_VENDOR
    csv_dir = vendor_dir / CSV_SUBDIR
    xlsx = list(vendor_dir.glob("*.xlsx")) if vendor_dir.exists() else []
    xlsx = [p for p in xlsx if not p.name.startswith("~$")]
    if xlsx:
        print("== mysteel social/port charts (from workbooks) ==")
        frames, snapshots = ingest(vendor_dir)
        write_caches(frames, snapshots, csv_dir)
        return render_charts(frames)
    if csv_dir.exists() and any(csv_dir.glob("*.csv")):
        print("== mysteel social/port charts (from cached csv) ==")
        frames = load_cached_frames(csv_dir)
        return render_charts(frames)
    print("  mysteel vendor data not found, skip social/port charts")
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest Mysteel exports and render social/port seasonal charts")
    ap.add_argument("--src", type=Path, default=DEFAULT_VENDOR, help="folder of 钢联 .xlsx exports")
    ap.add_argument("--charts-only", action="store_true", help="reuse cached CSVs, do not re-read xlsx")
    args = ap.parse_args()
    vendor_dir: Path = args.src
    csv_dir = vendor_dir / CSV_SUBDIR
    if args.charts_only:
        frames = load_cached_frames(csv_dir)
        if not frames:
            raise SystemExit(f"no cached csv in {csv_dir}")
        render_charts(frames)
        return
    render_if_available(vendor_dir)


if __name__ == "__main__":
    main()
