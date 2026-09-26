"use client";

import { Bar, BarChart as RechartsBarChart, CartesianGrid, XAxis, YAxis } from "recharts";

import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, type ChartConfig } from "@/components/ui/chart";

export type Series = { key: string; label: string; color: string };

type TooltipRow = { dataKey?: string | number; value?: number | string; color?: string; payload?: Record<string, unknown> };

/** Tooltip: value first (strong), series name second, keyed by a short line of the series color. */
function ValueTooltip({
  active,
  payload,
  label,
  series,
  format,
  extra,
}: {
  active?: boolean;
  payload?: TooltipRow[];
  label?: string | number;
  series: Series[];
  format: (value: number) => string;
  extra?: (row: Record<string, unknown>) => string | null;
}) {
  if (!active || !payload?.length) return null;
  const note = extra && payload[0].payload ? extra(payload[0].payload) : null;
  return (
    <div className="min-w-36 rounded-lg border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="mb-1 font-medium text-muted-foreground">{label}</p>
      {payload.map((row) => {
        const s = series.find((item) => item.key === row.dataKey);
        return (
          <div key={String(row.dataKey)} className="flex items-center gap-2">
            <span className="h-0.5 w-3 rounded" style={{ background: s?.color }} />
            <span className="font-semibold text-foreground tabular-nums">{format(Number(row.value ?? 0))}</span>
            <span className="text-muted-foreground">{s?.label}</span>
          </div>
        );
      })}
      {note && <p className="mt-1 text-muted-foreground">{note}</p>}
    </div>
  );
}

type BarChartProps = {
  data: object[];
  categoryKey: string;
  series: Series[];
  format?: (value: number) => string;
  /** Compact axis tick formatter. */
  axisFormat?: (value: number) => string;
  horizontal?: boolean;
  height?: number;
  /** Extra line in the tooltip, e.g. "12 deals". */
  tooltipExtra?: (row: Record<string, unknown>) => string | null;
};

/**
 * Bar chart with the app's conventions: thin rounded bars anchored to the
 * baseline, recessive grid, one axis, hover tooltip, legend only for 2+ series.
 */
export function BarChart({
  data,
  categoryKey,
  series,
  format = (v) => String(v),
  axisFormat = format,
  horizontal = false,
  height = 260,
  tooltipExtra,
}: BarChartProps) {
  const config = Object.fromEntries(series.map((s) => [s.key, { label: s.label, color: s.color }])) satisfies ChartConfig;
  const radius: [number, number, number, number] = horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0];

  return (
    <ChartContainer config={config} className="w-full" style={{ height }}>
      <RechartsBarChart
        data={data}
        layout={horizontal ? "vertical" : "horizontal"}
        margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
        barGap={2}
        barCategoryGap="28%"
        accessibilityLayer
      >
        <CartesianGrid vertical={horizontal} horizontal={!horizontal} strokeDasharray="3 3" strokeOpacity={0.6} />
        {horizontal ? (
          <>
            <XAxis type="number" tickLine={false} axisLine={false} tickFormatter={axisFormat} fontSize={12} />
            <YAxis type="category" dataKey={categoryKey} tickLine={false} axisLine={false} width={96} fontSize={12} />
          </>
        ) : (
          <>
            <XAxis dataKey={categoryKey} tickLine={false} axisLine={false} tickMargin={8} fontSize={12} interval={0} />
            <YAxis tickLine={false} axisLine={false} tickFormatter={axisFormat} width={56} fontSize={12} />
          </>
        )}
        <ChartTooltip cursor={{ fillOpacity: 0.4 }} content={<ValueTooltip series={series} format={format} extra={tooltipExtra} />} />
        {series.length > 1 && <ChartLegend content={<ChartLegendContent />} />}
        {series.map((s) => (
          <Bar key={s.key} dataKey={s.key} fill={s.color} radius={radius} maxBarSize={40} />
        ))}
      </RechartsBarChart>
    </ChartContainer>
  );
}
