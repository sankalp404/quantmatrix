import React, { useEffect, useRef } from 'react';
import { Box } from '@chakra-ui/react';
import { useColorMode } from '../theme/colorMode';

type Bar = { time: string; open: number; high: number; low: number; close: number; volume?: number };
type TradeMarker = { time: string; price: number; type: 'BUY' | 'SELL'; label?: string };
type DividendMarker = { time: string; amount: number; label?: string };

interface Props {
  height?: number;
  bars: Bar[];
  buys: TradeMarker[];
  sells: TradeMarker[];
  dividends: DividendMarker[];
  showTrades?: boolean;
  showDividends?: boolean;
  onHoverDaySec?: (daySec: number | null) => void;
  onClickDaySec?: (daySec: number | null) => void;
  showLine?: boolean;
  avgPrice?: number;
  pinnedDaySec?: number | null;
  zoomYears?: number | 'all';
}

declare global {
  interface Window {
    LightweightCharts?: any;
  }
}

const loadScript = (src: string) =>
  new Promise<void>((resolve, reject) => {
    const s = document.createElement('script');
    s.src = src;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject();
    document.body.appendChild(s);
  });

const SymbolChartWithMarkers: React.FC<Props> = ({ height = 520, bars, buys, sells, dividends, showTrades = true, showDividends = true, onHoverDaySec, onClickDaySec, showLine = false, avgPrice, pinnedDaySec, zoomYears }) => {
  const ref = useRef<HTMLDivElement>(null);
  const { colorMode } = useColorMode();
  const isDark = colorMode === 'dark';
  const bg = isDark ? '#070B12' : '#FFFFFF';
  const text = isDark ? '#E5E7EB' : '#0B1220';
  const grid = isDark ? '#1F2937' : '#E5E7EB';

  useEffect(() => {
    let chart: any;
    let series: any;
    (async () => {
      if (!window.LightweightCharts) {
        try {
          await loadScript('https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js');
        } catch {
          return;
        }
      }
      if (!ref.current) return;
      ref.current.innerHTML = '';
      chart = window.LightweightCharts.createChart(ref.current, {
        height,
        rightPriceScale: { borderVisible: false },
        layout: { background: { color: bg }, textColor: text },
        grid: { vertLines: { color: grid }, horzLines: { color: grid } },
        timeScale: { rightOffset: 5, barSpacing: 6, fixLeftEdge: false, lockVisibleTimeRangeOnResize: false },
        crosshair: { mode: 1 },
      });
      if (showLine) {
        series = chart.addLineSeries({ color: '#38bdf8', lineWidth: 2 });
      } else {
        series = chart.addCandlestickSeries({ upColor: '#22c55e', downColor: '#ef4444', borderDownColor: '#ef4444', borderUpColor: '#22c55e', wickDownColor: '#ef4444', wickUpColor: '#22c55e' });
      }
      // Normalize bar times to UTC midnight seconds for stable grouping
      const toDaySec = (iso: string) => {
        const d = new Date(iso);
        return Math.floor(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()) / 1000);
      };
      if (showLine) {
        const ldata = bars.map(b => ({ time: toDaySec(b.time), value: b.close }));
        series.setData(ldata);
      } else {
        const cdata = bars.map(b => ({
          time: toDaySec(b.time),
          open: b.open, high: b.high, low: b.low, close: b.close,
        }));
        series.setData(cdata);
      }
      if (avgPrice && Number.isFinite(avgPrice)) {
        series.createPriceLine({
          price: avgPrice,
          color: '#a78bfa',
          lineWidth: 1,
          lineStyle: window.LightweightCharts.LineStyle.Dashed,
          axisLabelVisible: true,
          title: 'AVG',
        });
      }

      // Build raw markers
      const raw: Array<{ time: number; text: string; kind: 'B' | 'S' | 'D' }> = [];
      if (showTrades) {
        for (const m of buys) {
          raw.push({ time: toDaySec(m.time), text: m.label || `Buy @ ${m.price.toFixed(2)}`, kind: 'B' });
        }
        for (const m of sells) {
          raw.push({ time: toDaySec(m.time), text: m.label || `Sell @ ${m.price.toFixed(2)}`, kind: 'S' });
        }
      }
      if (showDividends) {
        for (const d of dividends) {
          raw.push({ time: toDaySec(d.time), text: d.label || `Div $${d.amount.toFixed(2)}`, kind: 'D' });
        }
      }
      // Aggregate multiple events on same time
      const grouped = new Map<number, { texts: string[]; buys: string[]; sells: string[]; divs: string[]; hasB: boolean; hasS: boolean; hasD: boolean }>();
      for (const r of raw) {
        const g = grouped.get(r.time) || { texts: [], buys: [], sells: [], divs: [], hasB: false, hasS: false, hasD: false };
        g.texts.push(r.text);
        if (r.kind === 'B') { g.hasB = true; g.buys.push(r.text); }
        if (r.kind === 'S') { g.hasS = true; g.sells.push(r.text); }
        if (r.kind === 'D') { g.hasD = true; g.divs.push(r.text); }
        grouped.set(r.time, g);
      }
      const markers: any[] = [];
      for (const [t, g] of grouped.entries()) {
        const pos = g.hasS ? 'aboveBar' : 'belowBar';
        const color = g.hasB && g.hasS ? '#a855f7' : g.hasS ? '#dc2626' : g.hasB ? '#16a34a' : '#3b82f6';
        const shape = g.hasS ? 'arrowDown' : g.hasB ? 'arrowUp' : 'circle';
        // Keep labels off the chart to reduce clutter; show details in hover tooltip
        markers.push({ time: t, position: pos, color, shape, text: '' });
      }
      markers.sort((a, b) => a.time - b.time);
      series.setMarkers(markers);
      // Floating tooltip with aggregated details
      const tooltip = document.createElement('div');
      Object.assign(tooltip.style, {
        position: 'absolute',
        zIndex: 10,
        pointerEvents: 'none',
        padding: '8px 10px',
        borderRadius: '6px',
        border: `1px solid ${grid}`,
        background: bg,
        color: text,
        fontSize: '12px',
        boxShadow: '0 4px 10px rgba(0,0,0,0.25)',
        display: 'none',
        maxWidth: '240px',
      } as any);
      ref.current.appendChild(tooltip);
      const onCrosshairMove = (param: any) => {
        if (!param?.time || !param.point) {
          tooltip.style.display = 'none';
          onHoverDaySec && onHoverDaySec(null);
          return;
        }
        const t = typeof param.time === 'number'
          ? param.time
          : (param.time.year ? Math.floor(Date.UTC(param.time.year, param.time.month - 1, param.time.day) / 1000) : 0);
        const g = grouped.get(t);
        if (!g) {
          tooltip.style.display = 'none';
          onHoverDaySec && onHoverDaySec(null);
          return;
        }
        const blocks: string[] = [];
        if (g.buys.length) blocks.push(`<strong>Buys</strong>`, ...g.buys.slice(0, 4), g.buys.length > 4 ? `… ${g.buys.length - 4} more` : '');
        if (g.sells.length) blocks.push(`<strong>Sells</strong>`, ...g.sells.slice(0, 4), g.sells.length > 4 ? `… ${g.sells.length - 4} more` : '');
        if (g.divs.length) blocks.push(`<strong>Dividends</strong>`, ...g.divs.slice(0, 4), g.divs.length > 4 ? `… ${g.divs.length - 4} more` : '');
        tooltip.innerHTML = blocks.filter(Boolean).map(b => `<div>${b}</div>`).join('');
        const pad = 12;
        const parent = ref.current!.getBoundingClientRect();
        const x = Math.min(Math.max(param.point.x + pad, 0), parent.width - 260);
        const y = Math.min(Math.max(param.point.y + pad, 0), parent.height - 140);
        tooltip.style.left = `${x}px`;
        tooltip.style.top = `${y}px`;
        tooltip.style.display = 'block';
        onHoverDaySec && onHoverDaySec(t);
      };
      chart.subscribeCrosshairMove(onCrosshairMove);
      const onClick = (param: any) => {
        if (!param?.time) {
          onClickDaySec && onClickDaySec(null);
          return;
        }
        const t = typeof param.time === 'number'
          ? param.time
          : (param.time.year ? Math.floor(Date.UTC(param.time.year, param.time.month - 1, param.time.day) / 1000) : 0);
        onClickDaySec && onClickDaySec(t);
      };
      chart.subscribeClick(onClick);
      // Pinned vertical line overlay
      let pinEl: HTMLDivElement | null = document.createElement('div');
      Object.assign(pinEl.style, {
        position: 'absolute',
        top: '0',
        bottom: '0',
        width: '1px',
        background: '#a78bfa',
        opacity: '0.7',
        display: 'none',
        pointerEvents: 'none',
      } as any);
      ref.current.appendChild(pinEl);
      const updatePin = () => {
        if (!pinnedDaySec) { pinEl!.style.display = 'none'; return; }
        const x = chart.timeScale().timeToCoordinate(pinnedDaySec as any);
        if (x === null || x === undefined) { pinEl!.style.display = 'none'; return; }
        pinEl!.style.transform = `translateX(${x}px)`;
        pinEl!.style.display = 'block';
      };
      updatePin();
      chart.timeScale().subscribeVisibleTimeRangeChange(updatePin);
      chart.timeScale().subscribeSizeChange(updatePin);
      // Apply initial zoom
      try {
        if (zoomYears && zoomYears !== 'all' && bars?.length) {
          const lastIso = bars[bars.length - 1]?.time;
          const last = new Date(lastIso);
          const to = Math.floor(Date.UTC(last.getUTCFullYear(), last.getUTCMonth(), last.getUTCDate()) / 1000);
          const fromDate = new Date(Date.UTC(last.getUTCFullYear() - zoomYears, last.getUTCMonth(), last.getUTCDate()));
          const from = Math.floor(fromDate.getTime() / 1000);
          chart.timeScale().setVisibleRange({ from, to });
        } else {
          chart.timeScale().fitContent();
        }
      } catch { }
    })();

    return () => {
      try {
        // Remove all children (tooltip) and chart
        if (ref.current) ref.current.innerHTML = '';
        chart && chart.remove();
      } catch { }
    };
  }, [bars, buys, sells, dividends, showTrades, showDividends, bg, text, grid, height, onHoverDaySec, onClickDaySec, pinnedDaySec, zoomYears]);

  return <Box ref={ref} h={`${height}px`} />;
};

export default SymbolChartWithMarkers;


