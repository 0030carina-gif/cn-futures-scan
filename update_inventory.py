#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch warehouse-receipt history, cache CSV, render seasonal SVG charts.

Usage:
  /tmp/mdenv/bin/python update_inventory.py              # refresh + charts
  /tmp/mdenv/bin/python update_inventory.py --charts-only
  /tmp/mdenv/bin/python update_inventory.py --fetch-only
"""
from __future__ import annotations

import argparse
import json
import math
import time
import warnings
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "inventory"
CHARTS = ROOT / "scans" / "charts"
META_PATH = DATA / "symbols.json"

YEAR_COLORS = {
    2026: "#c0392b",
    2025: "#7d3c98",
    2024: "#d4a017",
    2023: "#1e7a52",
    2022: "#2f6fed",
}
OLDER = "#9a9488"

NAME_99 = {
    "CU": "铜", "AL": "铝", "RB": "螺纹钢", "HC": "热轧卷板",
    "I": "铁矿石", "JM": "焦煤", "J": "焦炭",
    "P": "棕榈油", "Y": "豆油",
    "MA": "甲醇", "TA": "PTA", "EG": "乙二醇", "V": "聚氯乙烯",
    "FU": "燃料油", "BU": "石油沥青", "SC": "原油",
    "PG": "液化石油气", "EB": "苯乙烯", "LH": "生猪",
}
NAME_EM = {
    "LC": "碳酸锂", "CU": "沪铜", "AL": "沪铝", "RB": "螺纹钢", "HC": "热卷",
    "FU": "燃油", "BU": "沥青", "P": "棕榈", "Y": "豆油", "MA": "甲醇",
    "TA": "PTA", "EG": "乙二醇", "V": "PVC", "I": "铁矿石", "JM": "焦煤",
    "J": "焦炭", "PG": "液化石油气", "EB": "苯乙烯", "LH": "生猪",
}
SHFE_INE = ["CU", "AL", "RB", "HC", "FU", "BU", "SC"]


def load_meta() -> dict:
    return json.loads(META_PATH.read_text(encoding="utf-8"))


def fetch_99(code: str) -> pd.DataFrame | None:
    import akshare as ak
    name = NAME_99.get(code)
    if not name:
        return None
    df = ak.futures_inventory_99(symbol=name)
    df = df.rename(columns={"日期": "date", "库存": "value"})
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["source"] = "99qh"
    return df[["date", "value", "source"]].dropna(subset=["value"])


def fetch_em(code: str) -> pd.DataFrame | None:
    import akshare as ak
    name = NAME_EM.get(code)
    if not name:
        return None
    try:
        df = ak.futures_inventory_em(symbol=name)
    except Exception:
        return None
    df = df.rename(columns={"日期": "date", "库存": "value"})
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["source"] = "em"
    return df[["date", "value", "source"]].dropna(subset=["value"])


def fetch_receipt_recent(codes: list[str], months_back: int = 4) -> pd.DataFrame:
    """Daily SHFE/INE receipts for recent months (akshare loops day-by-day)."""
    import akshare as ak
    today = date(2026, 11, 9)
    start = (today.replace(day=1) - timedelta(days=30 * (months_back - 1))).replace(day=1)
    rows = []
    cur = start
    while cur <= today:
        if cur.month == 12:
            nxt = date(cur.year + 1, 1, 1)
            end = date(cur.year, 12, 31)
        else:
            nxt = date(cur.year, cur.month + 1, 1)
            end = nxt - timedelta(days=1)
        end = min(end, today)
        s, e = cur.strftime("%Y%m%d"), end.strftime("%Y%m%d")
        try:
            df = ak.futures_receipt(start_date=s, end_date=e, vars_list=codes)
            if df is not None and len(df):
                rows.append(df)
                print(f"  receipt {s}-{e}: {len(df)}")
        except Exception as ex:
            print(f"  receipt fail {s}-{e}: {ex}")
        cur = nxt
        time.sleep(0.2)
    if not rows:
        return pd.DataFrame(columns=["date", "value", "source", "var"])
    out = pd.concat(rows, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"].astype(str))
    out = out.rename(columns={"receipt": "value", "var": "var"})
    out["source"] = "receipt"
    return out[["var", "date", "value", "source"]]


def merge_series(code: str, meta: dict, receipt_all: pd.DataFrame | None) -> pd.DataFrame:
    """Build preferred series for one symbol."""
    info = meta["symbols"][code]
    frames = []
    p99 = DATA / f"{code}_99.csv"
    if p99.exists():
        df = pd.read_csv(p99)
        df = df.rename(columns={"日期": "date", "库存": "value"})
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df["source"] = "99qh"
        frames.append(df[["date", "value", "source"]])
    pem = DATA / f"{code}_em_full.csv"
    if not pem.exists():
        pem = DATA / f"{code}_em.csv"
    if pem.exists():
        df = pd.read_csv(pem)
        df = df.rename(columns={"日期": "date", "库存": "value"})
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df["source"] = "em"
        frames.append(df[["date", "value", "source"]])
    if receipt_all is not None and len(receipt_all) and code in set(receipt_all["var"]):
        df = receipt_all[receipt_all["var"] == code][["date", "value", "source"]].copy()
        frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["date", "value", "source"])

    pref = info.get("source_pref") or ["99", "receipt", "em"]
    source_rank = []
    for p in pref:
        if p in ("99", "99qh"):
            source_rank.append("99qh")
        elif p == "receipt":
            source_rank.append("receipt")
        elif p == "em":
            source_rank.append("em")
    # Special case RB: 99qh absolute level diverges from exchange; drop 99qh from 2026
    # when receipt exists, to avoid false YoY jump. Keep 99qh for earlier years only.
    all_df = pd.concat(frames, ignore_index=True)
    all_df["date"] = pd.to_datetime(all_df["date"]).dt.normalize()
    if code == "RB" and receipt_all is not None and (receipt_all["var"] == "RB").any():
        rmin = pd.to_datetime(receipt_all.loc[receipt_all["var"] == "RB", "date"]).min()
        all_df = all_df[~((all_df["source"] == "99qh") & (all_df["date"] >= rmin))]
    if code == "BU" and receipt_all is not None and (receipt_all["var"] == "BU").any():
        # Prefer receipt (includes factory warehouse) over 99qh/em warehouse-only
        rmin = pd.to_datetime(receipt_all.loc[receipt_all["var"] == "BU", "date"]).min()
        all_df = all_df[~((all_df["source"].isin(["99qh", "em"])) & (all_df["date"] >= rmin))]
    # LC: prefer anchor/备忘 21720 over em 23760 on asof; keep em history otherwise
    rank = {s: i for i, s in enumerate(source_rank)}
    all_df["rank"] = all_df["source"].map(lambda s: rank.get(s, 50))
    all_df = all_df.sort_values(["date", "rank"])
    out = all_df.drop_duplicates("date", keep="first")[["date", "value", "source"]]

    anchor = info.get("anchor")
    asof = pd.Timestamp(meta.get("asof", "2026-11-09"))
    if anchor is not None:
        out = out[out["date"] != asof]
        out = pd.concat([
            out,
            pd.DataFrame([{"date": asof, "value": float(anchor), "source": "anchor"}]),
        ], ignore_index=True)
    return out.sort_values("date").reset_index(drop=True)


def to_doy_series(df: pd.DataFrame, unit_scale: float = 1.0) -> dict[int, list[tuple[int, float]]]:
    """Map year -> list of (day_of_year, value)."""
    by: dict[int, list[tuple[int, float]]] = {}
    for _, row in df.iterrows():
        d: pd.Timestamp = row["date"]
        if pd.isna(row["value"]):
            continue
        y = int(d.year)
        doy = int(d.dayofyear)
        # leap day -> 365 slot for alignment simplicity: keep actual doy, x uses month
        val = float(row["value"]) / unit_scale
        by.setdefault(y, []).append((doy, val, d.month, d.day))
    # sort
    for y in by:
        by[y] = sorted(by[y], key=lambda t: t[0])
    return by


def nice_ticks(vmax: float, n: int = 5) -> list[float]:
    if vmax <= 0:
        return [0, 1]
    raw = vmax * 1.08
    exp = 10 ** math.floor(math.log10(raw))
    step = raw / n
    for m in [1, 2, 2.5, 5, 10]:
        s = m * exp
        if s >= step * 0.8:
            step = s
            break
    ticks = []
    v = 0.0
    while v <= raw + step * 0.01:
        ticks.append(v)
        v += step
    return ticks


def svg_chart(
    code: str,
    title: str,
    series: dict,
    unit: str,
    source_note: str,
    end_note: str,
    width: int = 720,
    height: int = 340,
) -> str:
    pad_l, pad_r, pad_t, pad_b = 58, 18, 36, 58
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    # x: day of year 1..366 -> month positions
    def x_of(doy: int) -> float:
        return pad_l + (doy - 1) / 365.0 * plot_w

    all_vals = [v for pts in series.values() for v in (p[1] for p in pts)]
    vmax = max(all_vals) if all_vals else 1.0
    if vmax <= 0:
        vmax = 1.0
    ticks = nice_ticks(vmax)
    ymax = ticks[-1] if ticks else vmax

    def y_of(val: float) -> float:
        return pad_t + plot_h - (val / ymax) * plot_h

    # years newest first for drawing order (older under)
    years = sorted(series.keys())
    focus = [y for y in years if y >= 2022]
    older = [y for y in years if y < 2022]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" height="auto" class="season-svg" role="img" '
        f'aria-label="{title}">',
        f"<title>{title}</title>",
        # background
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="var(--chart-bg,#fbf7f0)" rx="12"/>',
        # grid
    ]
    # horizontal grid + y labels
    for t in ticks:
        y = y_of(t)
        parts.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width-pad_r}" y2="{y:.1f}" '
            f'stroke="var(--chart-grid,#e5ddcf)" stroke-width="1"/>'
        )
        label = f"{t:,.0f}" if t >= 10 or t == 0 else f"{t:g}"
        parts.append(
            f'<text x="{pad_l-8}" y="{y+4:.1f}" text-anchor="end" '
            f'font-size="11" fill="var(--chart-muted,#6e675c)" '
            f'font-family="Noto Sans CJK SC, Noto Sans SC, sans-serif">{label}</text>'
        )
    # month ticks
    month_doy = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    month_lab = ["1月", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
    for doy, lab in zip(month_doy, month_lab):
        x = x_of(doy)
        parts.append(
            f'<line x1="{x:.1f}" y1="{pad_t}" x2="{x:.1f}" y2="{pad_t+plot_h}" '
            f'stroke="var(--chart-grid,#e5ddcf)" stroke-width="1" stroke-dasharray="2 3"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{pad_t+plot_h+18}" text-anchor="middle" '
            f'font-size="11" fill="var(--chart-muted,#6e675c)" '
            f'font-family="Noto Sans CJK SC, Noto Sans SC, sans-serif">{lab}</text>'
        )

    # older years as faint gray
    if older:
        for y in older:
            pts = series[y]
            if len(pts) < 2:
                continue
            d = "M " + " L ".join(f"{x_of(p[0]):.1f},{y_of(p[1]):.1f}" for p in pts)
            parts.append(
                f'<path d="{d}" fill="none" stroke="{OLDER}" stroke-width="1" opacity="0.35"/>'
            )

    # focus years oldest first so newest on top
    for y in focus:
        pts = series[y]
        if len(pts) < 2:
            # single point
            if len(pts) == 1:
                p = pts[0]
                color = YEAR_COLORS.get(y, OLDER)
                parts.append(
                    f'<circle cx="{x_of(p[0]):.1f}" cy="{y_of(p[1]):.1f}" r="3" fill="{color}"/>'
                )
            continue
        color = YEAR_COLORS.get(y, OLDER)
        sw = 2.6 if y == max(focus) else 1.6
        d = "M " + " L ".join(f"{x_of(p[0]):.1f},{y_of(p[1]):.1f}" for p in pts)
        parts.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        # end marker for current year
        if y == max(focus):
            p = pts[-1]
            parts.append(
                f'<circle cx="{x_of(p[0]):.1f}" cy="{y_of(p[1]):.1f}" r="3.5" '
                f'fill="{color}" stroke="var(--chart-bg,#fbf7f0)" stroke-width="1.5"/>'
            )

    # title
    parts.append(
        f'<text x="{pad_l}" y="22" font-size="14" font-weight="650" '
        f'fill="var(--chart-ink,#1c1915)" '
        f'font-family="Noto Sans CJK SC, Noto Sans SC, sans-serif">{title}</text>'
    )
    # unit
    parts.append(
        f'<text x="{pad_l}" y="{pad_t-6}" font-size="10" fill="var(--chart-muted,#6e675c)" '
        f'font-family="Noto Sans CJK SC, Noto Sans SC, sans-serif">单位：{unit}</text>'
    )

    # legend
    lx = pad_l
    ly = height - 14
    legend_items = [(y, YEAR_COLORS[y]) for y in sorted(YEAR_COLORS.keys(), reverse=True) if y in series]
    if older:
        legend_items.append(("其他", OLDER))
    for label, color in legend_items:
        parts.append(f'<rect x="{lx}" y="{ly-8}" width="12" height="3" rx="1" fill="{color}"/>')
        parts.append(
            f'<text x="{lx+16}" y="{ly-1}" font-size="11" fill="var(--chart-ink,#1c1915)" '
            f'font-family="Noto Sans CJK SC, Noto Sans SC, sans-serif">{label}</text>'
        )
        lx += 58 if label != "其他" else 52

    parts.append("</svg>")
    return "\n".join(parts)


def render_all(meta: dict) -> dict:
    CHARTS.mkdir(parents=True, exist_ok=True)
    receipt_frames = []
    for path in [DATA / "shfe_ine_receipt.csv", DATA / "shfe_ine_receipt_recent.csv"]:
        if path.exists():
            df = pd.read_csv(path)
            df["date"] = pd.to_datetime(df["date"].astype(str))
            if "receipt" in df.columns:
                df = df.rename(columns={"receipt": "value"})
            df["source"] = "receipt"
            receipt_frames.append(df[["var", "date", "value", "source"]])
    receipt_all = pd.concat(receipt_frames, ignore_index=True).drop_duplicates(["var", "date"]) if receipt_frames else None

    manifest = {}
    for code, info in meta["symbols"].items():
        series_df = merge_series(code, meta, receipt_all)
        # save merged
        series_df.to_csv(DATA / f"{code}_merged.csv", index=False)
        if series_df.empty or series_df["value"].notna().sum() < 5:
            manifest[code] = {"ok": False, "reason": "序列过短或缺失"}
            print(f"SKIP {code}: too short")
            continue
        # JM often all zeros - still plot but flag
        by = to_doy_series(series_df, info.get("unit_scale") or 1)
        # keep from 2018+
        by = {y: pts for y, pts in by.items() if y >= 2018 and pts}
        if not by:
            manifest[code] = {"ok": False, "reason": "2018年后无点"}
            continue

        # source note
        sources = sorted(series_df["source"].unique())
        src_map = {"99qh": "99期货网", "em": "东方财富", "receipt": "交易所仓单日报", "anchor": "备忘核对点"}
        src_txt = "、".join(src_map.get(s, s) for s in sources)
        years = sorted(by.keys())
        last = series_df.dropna(subset=["value"]).iloc[-1]
        last_val = float(last["value"]) / (info.get("unit_scale") or 1)
        note = info.get("note") or info.get("口径") or ""
        end_note = (
            f"口径：交易所注册仓单｜来源：{src_txt}｜"
            f"{years[0]}–{years[-1]}｜截至 {pd.Timestamp(last['date']).date()} "
            f"约 {last_val:,.0f} {info['unit']}"
        )
        if note:
            end_note += f"：{note}" if False else f"。{note}"

        svg = svg_chart(
            code,
            info["title"],
            by,
            info["unit"],
            src_txt,
            end_note,
        )
        svg_path = CHARTS / f"{code}_season.svg"
        svg_path.write_text(svg, encoding="utf-8")
        # also a small html fragment
        frag = (
            f'<figure class="season-chart" data-symbol="{code}" id="chart-{code}">'
            f"{svg}"
            f'<figcaption>{end_note}</figcaption>'
            f"</figure>\n"
        )
        (CHARTS / f"{code}_season.html").write_text(frag, encoding="utf-8")
        manifest[code] = {
            "ok": True,
            "years": f"{years[0]}-{years[-1]}",
            "n": int(len(series_df)),
            "unit": info["unit"],
            "last": last_val,
            "sources": sources,
            "svg": str(svg_path.relative_to(ROOT)),
        }
        print(f"OK {code}: {years[0]}-{years[-1]} n={len(series_df)} last={last_val:.0f} {info['unit']}")
    (DATA / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def refresh_fetch(meta: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    print("== fetch 99qh ==")
    for code in meta["symbols"]:
        if code not in NAME_99:
            continue
        try:
            df = fetch_99(code)
            if df is not None and len(df):
                raw = df.rename(columns={"date": "日期", "value": "库存"})
                # keep close if present from previous? just date/value
                out = pd.DataFrame({"日期": raw["日期"].dt.date, "收盘价": float("nan"), "库存": raw["库存"]})
                # try preserve close from old file
                old = DATA / f"{code}_99.csv"
                if old.exists():
                    prev = pd.read_csv(old)
                    if "收盘价" in prev.columns:
                        prev["日期"] = pd.to_datetime(prev["日期"])
                        merged = pd.merge(
                            out.assign(日期=pd.to_datetime(out["日期"])),
                            prev[["日期", "收盘价"]],
                            on="日期",
                            how="left",
                            suffixes=("", "_old"),
                        )
                        if "收盘价_old" in merged:
                            merged["收盘价"] = merged["收盘价_old"].fillna(merged["收盘价"])
                            merged = merged.drop(columns=["收盘价_old"])
                        out = merged
                        out["日期"] = out["日期"].dt.date
                out.to_csv(DATA / f"{code}_99.csv", index=False)
                print(f"  99 {code}: {len(out)}")
        except Exception as e:
            print(f"  99 FAIL {code}: {e}")
        time.sleep(0.15)

    print("== fetch EM ==")
    for code in meta["symbols"]:
        if code not in NAME_EM:
            continue
        try:
            df = fetch_em(code)
            if df is not None and len(df):
                out = pd.DataFrame({
                    "日期": df["date"].dt.date,
                    "库存": df["value"],
                    "增减": float("nan"),
                })
                out.to_csv(DATA / f"{code}_em.csv", index=False)
                print(f"  em {code}: {len(out)} last={out.iloc[-1]['库存']}")
        except Exception as e:
            print(f"  em FAIL {code}: {e}")
        time.sleep(0.1)

    print("== fetch SHFE/INE receipt recent ==")
    try:
        rec = fetch_receipt_recent(SHFE_INE, months_back=3)
        if len(rec):
            # normalize columns for csv
            save = rec.rename(columns={"value": "receipt"})
            save["date"] = save["date"].dt.strftime("%Y%m%d")
            save.to_csv(DATA / "shfe_ine_receipt_recent.csv", index=False)
            print(f"  receipt rows={len(rec)}")
    except Exception as e:
        print(f"  receipt FAIL: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--charts-only", action="store_true")
    ap.add_argument("--fetch-only", action="store_true")
    args = ap.parse_args()
    meta = load_meta()
    if not args.charts_only:
        refresh_fetch(meta)
    if not args.fetch_only:
        render_all(meta)


if __name__ == "__main__":
    main()
