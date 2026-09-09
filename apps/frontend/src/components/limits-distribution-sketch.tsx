"use client";



import type P5 from "p5";
import { useEffect, useMemo, useRef, useState } from "react";

import type { LimitsBucketSchema } from "@/lib/types";

interface LimitsDistributionSketchProps {
  buckets: LimitsBucketSchema[];
}

interface ChartBucket {
  range: string;
  count: number;
  percentage: number;
}

const CHART_MIN_WIDTH = 280;
const CHART_DESKTOP_HEIGHT = 260;
const CHART_MOBILE_HEIGHT = 238;
const TICK_COUNT = 5;


function normalizeBuckets(buckets: LimitsBucketSchema[]): ChartBucket[] {
  return buckets.map((bucket, index) => ({
    range: bucket.range || `Faixa ${index + 1}`,
    count: Math.max(0, bucket.count),
    percentage: Number.isFinite(bucket.percentage) ? bucket.percentage : 0,
  }));
}


function chartYMax(maxValue: number): number {
  if (maxValue <= 0) return 1000;
  const step = maxValue > 20000 ? 5000 : maxValue > 5000 ? 2000 : 1000;
  return Math.ceil(maxValue / step) * step;
}


function formatChartTick(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1).replace(".", ",")}M`;
  if (value >= 1000) return `${Math.round(value / 1000)}K`;
  return String(Math.round(value));
}


function formatPercent(value: number): string {
  return `${value.toFixed(1).replace(".", ",")}%`;
}


function truncateLabel(label: string, maxWidth: number): string {
  const maxChars = Math.max(4, Math.floor(maxWidth / 6));
  if (label.length <= maxChars) return label;
  return `${label.slice(0, Math.max(1, maxChars - 3))}...`;
}

/** Resolve canvas width and height from its container. */
function canvasSize(container: HTMLDivElement): { width: number; height: number } {
  const width = Math.max(CHART_MIN_WIDTH, Math.floor(container.clientWidth));
  return {
    width,
    height: width < 460 ? CHART_MOBILE_HEIGHT : CHART_DESKTOP_HEIGHT,
  };
}


function resizeSketch(sketch: P5, container: HTMLDivElement) {
  const { width, height } = canvasSize(container);
  sketch.resizeCanvas(width, height);
}


export function LimitsDistributionSketch({ buckets }: LimitsDistributionSketchProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loadFailed, setLoadFailed] = useState(false);

  const chartBuckets = useMemo(() => normalizeBuckets(buckets), [buckets]);
  const summary = useMemo(
    () =>
      chartBuckets
        .map(
          (bucket) =>
            `${bucket.range}: ${bucket.count.toLocaleString("en-US")} clients (${formatPercent(bucket.percentage)})`,
        )
        .join("; "),
    [chartBuckets],
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let active = true;
    let sketch: P5 | null = null;
    let canvasReady = false;
    let resizeObserver: ResizeObserver | null = null;

    setLoadFailed(false);

    import("p5")
      .then(({ default: P5Constructor }) => {
        if (!active || !container.isConnected) return;

        const maxQuantity = Math.max(...chartBuckets.map((bucket) => bucket.count), 1);
        const yMax = chartYMax(maxQuantity);
        const ticks = Array.from(
          { length: TICK_COUNT + 1 },
          (_, index) => (yMax / TICK_COUNT) * index,
        );

        sketch = new P5Constructor((p: P5) => {
          let progress = 0;

          p.setup = () => {
            const { width, height } = canvasSize(container);
            const canvas = p.createCanvas(width, height);
            canvas.parent(container);
            canvas.elt.setAttribute("role", "img");
            canvas.elt.setAttribute(
              "aria-label",
              `Distribution of suggested limits by value range. ${summary}`,
            );
            p.pixelDensity(Math.min(window.devicePixelRatio || 1, 2));
            p.frameRate(30);
            p.textFont("Inter, Arial, sans-serif");
            canvasReady = true;
          };

          p.draw = () => {
            progress = Math.min(1, progress + 0.045);
            const easedProgress = 1 - (1 - progress) ** 3;

            const width = p.width;
            const height = p.height;
            const plotLeft = 42;
            const plotRight = 12;
            const plotTop = 18;
            const plotBottom = height - 44;
            const plotWidth = width - plotLeft - plotRight;
            const plotHeight = plotBottom - plotTop;

            p.clear();
            p.background("#ffffff");

            p.stroke("#eef2f7");
            p.strokeWeight(1);
            p.textSize(10);
            p.textAlign(p.RIGHT, p.CENTER);
            p.fill("#a0aec0");

            ticks.forEach((tick) => {
              const y = p.map(tick, 0, yMax, plotBottom, plotTop);
              p.line(plotLeft, y, width - plotRight, y);
              p.noStroke();
              p.text(formatChartTick(tick), plotLeft - 8, y);
              p.stroke("#eef2f7");
            });

            p.stroke("#dbe4ef");
            p.line(plotLeft, plotBottom, width - plotRight, plotBottom);
            p.noStroke();

            const slotWidth = plotWidth / chartBuckets.length;
            const barWidth = Math.max(14, Math.min(54, slotWidth * 0.52));
            let hoveredIndex: number | null = null;

            chartBuckets.forEach((bucket, index) => {
              const x = plotLeft + slotWidth * index + slotWidth / 2;
              const rawHeight = p.map(bucket.count, 0, yMax, 0, plotHeight);
              const barHeight = rawHeight * easedProgress;
              const y = plotBottom - barHeight;
              const isHovering =
                bucket.count > 0 &&
                p.mouseX >= x - barWidth / 2 &&
                p.mouseX <= x + barWidth / 2 &&
                p.mouseY >= y &&
                p.mouseY <= plotBottom;

              if (isHovering) hoveredIndex = index;

              p.fill(isHovering ? "#3b82f6" : "#0d1f3c");
              p.rect(
                x - barWidth / 2,
                y,
                barWidth,
                Math.max(bucket.count > 0 ? 2 : 0, barHeight),
                6,
                6,
                0,
                0,
              );

              if (slotWidth >= 46 && bucket.count > 0) {
                const label = formatChartTick(bucket.count);
                const labelY = Math.max(plotTop + 12, y - 6);
                const labelWidth = p.textWidth(label) + 10;
                const labelHeight = 16;

                p.fill("#ffffff");
                p.rect(x - labelWidth / 2, labelY - labelHeight + 3, labelWidth, labelHeight, 6);
                p.fill("#0f172a");
                p.textAlign(p.CENTER, p.BOTTOM);
                p.textSize(10);
                p.text(label, x, labelY);
              }

              p.fill("#6b7a91");
              p.textAlign(p.CENTER, p.TOP);
              p.textSize(10);
              p.text(truncateLabel(bucket.range, slotWidth), x, plotBottom + 10);
            });

            if (hoveredIndex !== null) {
              const bucket = chartBuckets[hoveredIndex];
              const lineOne = bucket.range;
              const lineTwo = `${bucket.count.toLocaleString("en-US")} clients · ${formatPercent(bucket.percentage)}`;
              p.textSize(11);
              const tooltipWidth = Math.min(
                width - 16,
                Math.max(p.textWidth(lineOne), p.textWidth(lineTwo)) + 24,
              );
              const tooltipHeight = 48;
              const x = p.constrain(p.mouseX + 14, 8, width - tooltipWidth - 8);
              const y = p.constrain(p.mouseY - tooltipHeight - 12, 8, height - tooltipHeight - 8);

              p.fill("#0d1f3c");
              p.rect(x, y, tooltipWidth, tooltipHeight, 8);
              p.fill("#ffffff");
              p.textAlign(p.LEFT, p.TOP);
              p.text(lineOne, x + 12, y + 10);
              p.fill("#cbd5e1");
              p.text(lineTwo, x + 12, y + 28);
            }
          };
        });

        resizeObserver = new ResizeObserver(() => {
          if (sketch && canvasReady) resizeSketch(sketch, container);
        });
        resizeObserver.observe(container);
      })
      .catch(() => {
        if (active) setLoadFailed(true);
      });

    return () => {
      active = false;
      resizeObserver?.disconnect();
      sketch?.remove();
    };
  }, [chartBuckets, summary]);

  return (
    <div className="p5-limit-chart-wrap">
      <div ref={containerRef} className="p5-limit-chart">
        {loadFailed && (
          <div className="p5-limit-chart-error">
            The interactive visualization could not be loaded.
          </div>
        )}
      </div>
      <div className="sr-only">{summary}</div>
      <div className="bar-legend">
        <span className="legend-dot" style={{ background: "var(--navy)" }} />
        Clients with a suggested limit
      </div>
    </div>
  );
}
