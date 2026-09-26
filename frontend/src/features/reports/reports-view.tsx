"use client";

import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "@/components/layout/page-header";
import { BarChart } from "@/components/shared/bar-chart";
import { StatCard } from "@/components/shared/stat-card";
import { EmptyState, ErrorState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCurrentUser } from "@/hooks/use-current-user";
import { useListState } from "@/hooks/use-list-state";
import { cn } from "@/lib/utils";
import { monthLabel, reportsService, type DateRangeParams } from "@/services/reports";
import { formatCurrency, formatNumber, humanize, todayISO } from "@/utils/format";

const money = (value: number) => formatCurrency(value);
const compactMoney = (value: number) => formatCurrency(value, "USD", true);

function daysAgo(days: number) {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

const PRESETS = [
  { label: "30 days", start: () => daysAgo(30) },
  { label: "90 days", start: () => daysAgo(90) },
  { label: "This year", start: () => `${new Date().getFullYear()}-01-01` },
  { label: "All time", start: () => "" },
];

function Section({ title, description, children, className }: { title: string; description: string; children: React.ReactNode; className?: string }) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">{children}</CardContent>
    </Card>
  );
}

function useReport<T>(key: string, fn: (p: DateRangeParams) => Promise<T>, range: DateRangeParams, enabled = true) {
  return useQuery({ queryKey: ["reports", key, range], queryFn: () => fn(range), enabled });
}

export function ReportsView() {
  const { isManager } = useCurrentUser();
  const list = useListState({ filters: ["start_date", "end_date"] });
  const range: DateRangeParams = {
    start_date: list.filters.start_date || undefined,
    end_date: list.filters.end_date || undefined,
  };

  const conversion = useReport("conversion", reportsService.leadConversion, range);
  const pipeline = useReport("pipeline", reportsService.pipeline, range);
  const revenue = useReport("revenue", reportsService.revenue, range);
  const winLoss = useReport("win-loss", reportsService.winLoss, range);
  const sources = useReport("sources", reportsService.leadSources, range);
  const reps = useReport("reps", reportsService.repPerformance, range, isManager);
  const firstError = [conversion, pipeline, revenue, winLoss, sources].find((q) => q.error)?.error;

  const activePreset = PRESETS.find((p) => p.start() === (list.filters.start_date ?? "") && !list.filters.end_date)?.label;

  return (
    <>
      <PageHeader title="Reports" description="How your team is converting leads and closing deals." />

      <div className="flex flex-col gap-2 rounded-xl border bg-card p-3 sm:flex-row sm:flex-wrap sm:items-center">
        <div className="flex flex-wrap gap-1">
          {PRESETS.map((preset) => (
            <Button
              key={preset.label}
              size="sm"
              variant={activePreset === preset.label ? "secondary" : "ghost"}
              onClick={() => list.setFilters({ start_date: preset.start(), end_date: "" })}
            >
              {preset.label}
            </Button>
          ))}
        </div>
        <div className="flex items-center gap-2 sm:ml-auto">
          <Input type="date" aria-label="Start date" className="w-38" value={list.filters.start_date} max={list.filters.end_date || todayISO()} onChange={(e) => list.setFilter("start_date", e.target.value)} />
          <span className="text-muted-foreground">–</span>
          <Input type="date" aria-label="End date" className="w-38" value={list.filters.end_date} min={list.filters.start_date} onChange={(e) => list.setFilter("end_date", e.target.value)} />
        </div>
      </div>

      {firstError ? <ErrorState error={firstError} /> : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Lead conversion rate" value={conversion.data ? `${conversion.data.conversion_rate}%` : "…"} hint={conversion.data && `${conversion.data.converted} of ${conversion.data.total_leads} leads`} />
        <StatCard
          label="Avg. time to convert"
          value={conversion.data?.avg_days_to_convert != null ? `${conversion.data.avg_days_to_convert} days` : "—"}
        />
        <StatCard label="Revenue (won)" value={winLoss.data ? money(winLoss.data.won_value) : "…"} hint={winLoss.data && `${winLoss.data.won} deals won`} />
        <StatCard label="Win rate" value={winLoss.data ? `${winLoss.data.win_rate}%` : "…"} hint={winLoss.data && `${winLoss.data.won} won · ${winLoss.data.lost} lost`} />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Section title="Sales pipeline" description="Open deals per stage: total vs probability-weighted value">
          {pipeline.data ? (
            <>
              <BarChart
                data={pipeline.data}
                categoryKey="stage"
                series={[
                  { key: "value", label: "Total value", color: "var(--chart-1)" },
                  { key: "weighted_value", label: "Weighted value", color: "var(--chart-2)" },
                ]}
                format={money}
                axisFormat={compactMoney}
                tooltipExtra={(row) => `${row.count} deals`}
              />
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Stage</TableHead>
                    <TableHead className="text-right">Deals</TableHead>
                    <TableHead className="text-right">Value</TableHead>
                    <TableHead className="text-right">Weighted</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pipeline.data.map((row) => (
                    <TableRow key={row.stage_id}>
                      <TableCell>{row.stage}</TableCell>
                      <TableCell className="text-right tabular-nums">{row.count}</TableCell>
                      <TableCell className="text-right tabular-nums">{money(row.value)}</TableCell>
                      <TableCell className="text-right tabular-nums">{money(row.weighted_value)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </>
          ) : (
            <Skeleton className="h-64" />
          )}
        </Section>

        <Section title="Revenue" description="Value of deals won per month">
          {!revenue.data ? (
            <Skeleton className="h-64" />
          ) : revenue.data.length ? (
            <BarChart
              data={revenue.data.map((row) => ({ ...row, label: monthLabel(row.month) }))}
              categoryKey="label"
              series={[{ key: "revenue", label: "Revenue", color: "var(--chart-1)" }]}
              format={money}
              axisFormat={compactMoney}
              tooltipExtra={(row) => `${row.deals} deals won`}
            />
          ) : (
            <EmptyState title="No revenue in this period" />
          )}
        </Section>

        <Section title="Won vs lost" description="Closed deals per month">
          {!winLoss.data ? (
            <Skeleton className="h-64" />
          ) : winLoss.data.by_month.length ? (
            <BarChart
              data={winLoss.data.by_month.map((row) => ({ ...row, label: monthLabel(row.month) }))}
              categoryKey="label"
              series={[
                { key: "won", label: "Won", color: "var(--chart-1)" },
                { key: "lost", label: "Lost", color: "var(--chart-2)" },
              ]}
              format={(v) => `${v} deals`}
              axisFormat={(v) => String(v)}
            />
          ) : (
            <EmptyState title="No closed deals in this period" />
          )}
        </Section>

        <Section title="Lead conversion" description="Leads created in the period, by current status">
          {conversion.data ? (
            <BarChart
              data={conversion.data.by_status.map((row) => ({ ...row, label: humanize(row.status) }))}
              categoryKey="label"
              series={[{ key: "count", label: "Leads", color: "var(--chart-1)" }]}
              format={(v) => `${v} leads`}
              axisFormat={(v) => String(v)}
            />
          ) : (
            <Skeleton className="h-64" />
          )}
        </Section>

        <Section title="Lead source performance" description="Where leads come from and how well they convert" className="xl:col-span-2">
          {sources.data ? (
            sources.data.length ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Source</TableHead>
                    <TableHead className="text-right">Leads</TableHead>
                    <TableHead className="text-right">Converted</TableHead>
                    <TableHead className="w-1/3">Conversion rate</TableHead>
                    <TableHead className="text-right">Avg. score</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sources.data.map((row) => (
                    <TableRow key={row.source}>
                      <TableCell className="font-medium">{humanize(row.source)}</TableCell>
                      <TableCell className="text-right tabular-nums">{row.leads}</TableCell>
                      <TableCell className="text-right tabular-nums">{row.converted}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                            <div className="h-full rounded-full bg-(--chart-1)" style={{ width: `${row.conversion_rate}%` }} />
                          </div>
                          <span className="w-12 text-right text-xs tabular-nums">{row.conversion_rate}%</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{row.avg_score}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <EmptyState title="No leads in this period" />
            )
          ) : (
            <Skeleton className="h-40" />
          )}
        </Section>

        {isManager && (
          <Section title="Sales rep performance" description="Deals closed and leads converted in the period (open pipeline is current)" className="xl:col-span-2">
            {reps.data ? (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Rep</TableHead>
                      <TableHead className="text-right">Revenue</TableHead>
                      <TableHead className="text-right">Won</TableHead>
                      <TableHead className="text-right">Lost</TableHead>
                      <TableHead className="text-right">Win rate</TableHead>
                      <TableHead className="text-right">Open deals</TableHead>
                      <TableHead className="text-right">Open value</TableHead>
                      <TableHead className="text-right">Leads</TableHead>
                      <TableHead className="text-right">Converted</TableHead>
                      <TableHead className="text-right">Activities</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {reps.data.map((row, index) => (
                      <TableRow key={row.user_id}>
                        <TableCell className={cn("font-medium", index === 0 && row.revenue > 0 && "text-primary")}>
                          {row.name} <span className="text-xs font-normal text-muted-foreground">· {humanize(row.role)}</span>
                        </TableCell>
                        <TableCell className="text-right font-medium tabular-nums">{money(row.revenue)}</TableCell>
                        <TableCell className="text-right tabular-nums">{row.deals_won}</TableCell>
                        <TableCell className="text-right tabular-nums">{row.deals_lost}</TableCell>
                        <TableCell className="text-right tabular-nums">{row.win_rate}%</TableCell>
                        <TableCell className="text-right tabular-nums">{row.open_deals}</TableCell>
                        <TableCell className="text-right tabular-nums">{money(row.open_value)}</TableCell>
                        <TableCell className="text-right tabular-nums">{row.leads}</TableCell>
                        <TableCell className="text-right tabular-nums">{row.leads_converted}</TableCell>
                        <TableCell className="text-right tabular-nums">{formatNumber(row.activities)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <Skeleton className="h-40" />
            )}
          </Section>
        )}
      </div>
    </>
  );
}
