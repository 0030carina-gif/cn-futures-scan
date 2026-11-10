# 中国商品期货全市场每日扫描

每个交易日收盘后，对国内商品期货重点品种做一次深度扫描，覆盖基本面、分析逻辑和技术面。

## 怎么看

用浏览器打开 [最新一期](https://0030carina-gif.github.io/cn-futures-scan/)，或查看仓库里的 [index.html](./index.html)。历史期次在 [`scans/`](./scans/) 目录，按日期命名。

页面支持浅色 / 深色切换，也可在手机上打开。

目录标题会按**基本面**标注方向，不单看当日涨跌：红色「多」、绿色「空」；基本面明显交织时标「中性」。把鼠标放到标注上可看到简要理由。

各品种正文的库存/仓单段落后附有**仓单季节性图**（内联 SVG）。默认口径为交易所注册仓单；铁矿等注明「非港口社库」。颜色：当年红、前一年紫，再往前黄/绿/蓝，更早合并为灰色「其他」。数据缓存于 [`data/inventory/`](./data/inventory/)：上期所/能源中心用交易所仓单日报，郑商所用官网仓单日报（单位张），大商所长序列来自 99 期货网，广期所近端来自东方财富。正文用 `[[chart:CODE]]` 标记插图位置。

## 本期

- [2026-11-10 深度扫描](https://0030carina-gif.github.io/cn-futures-scan/scans/2026-11-10.html)（日盘收盘；全品种仓单季节图）

## 历史期次

- [2026-11-09](https://0030carina-gif.github.io/cn-futures-scan/scans/2026-11-09.html)（日盘收盘 + 夜盘开盘补记）

## 本地重建

```bash
# 刷新仓单缓存并重绘季节图
/tmp/mdenv/bin/python update_inventory.py

# 仅重绘（用已有 CSV）
/tmp/mdenv/bin/python update_inventory.py --charts-only

# 从备忘 Markdown 生成阅读页（嵌入季节图 + 多空标注）；默认取 scans/ 下最新日期
/tmp/mdenv/bin/python build_scan_html.py --date YYYY-MM-DD
```

生成物：`index.html` 与 `scans/YYYY-MM-DD.html`。
