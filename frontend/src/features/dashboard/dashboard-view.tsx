"use client";

import { useQuery } from "@tanstack/react-query";
import { Building2, CheckSquare, Handshake, History, Target, TrendingUp, Trophy, Users, XCircle } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/layout/page-header";
import { ActivityTimeline } from "@/components/shared/activity-timeline";
import { BarChart } from "@/components/shared/bar-chart";
import { StatCard, StatCardSkeleton } from "@/components/shared/stat-card";
import { EmptyState, ErrorState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TaskItem } from "@/features/tasks/task-item";
import { useCurrentUser } from "@/hooks/use-current-user";
import { monthLabel, reportsService } from "@/services/reports";
import type { TimelineItem } from "@/types";
import { formatCurrency, formatNumber, humanize } from "@/utils/format";

const money = (value: number) => formatCurrency(value);
const compactMoney = (value: number) => formatCurrency(value, "USD", true);

export function DashboardView() {
  const { user } = useCurrentUser();
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ["dashboard"], queryFn: reportsService.dashboard });
  const totals = data?.totals;

  const greeting = (() => {
    const hour = new Date().getHours();
    return hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  })();

  if (error) return <ErrorState error={error} onRetry={refetch} />;

  const activityItems: TimelineItem[] = (data?.recent_activities ?? []).map((activity) => ({
    kind: "activity",
    occurred_at: activity.occurred_at,
    activity,
    note: null,
  }));

  return (
    <>
      <PageHeader
        title={user ? `${greeting}, ${user.full_name.split(" ")[0]}` : "Dashboard"}
        description="Here's what's happening across your pipeline."
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {!totals ? (
          Array.from({ length: 8 }).map((_, i) => <StatCardSkeleton key={i} />)
        ) : (
          <>
            <StatCard label="Contacts" value={formatNumber(totals.contacts)} icon={Users} href="/contacts" />
            <StatCard label="Companies" value={formatNumber(totals.companies)} icon={Building2} href="/companies" />
            <StatCard label="Leads" value={formatNumber(totals.leads)} hint={`${totals.open_leads} open`} icon={Target} href="/leads" />
            <StatCard
              label="Lead conversion"
              value={`${totals.lead_conversion_rate}%`}
              hint={`${totals.converted_leads} of ${totals.leads} leads converted`}
              icon={TrendingUp}
              href="/reports"
            />
            <StatCard
              label="Active deals"
              value={formatNumber(totals.active_deals)}
              hint={`${money(totals.pipeline_value)} in pipeline`}
              icon={Handshake}
              href="/pipeline"
            />
            <StatCard
              label="Weighted pipeline"
              value={compactMoney(totals.weighted_pipeline_value)}
              hint="Deal value × stage probability"
              icon={TrendingUp}
            />
            <StatCard label="Won deals" value={formatNumber(totals.won_deals)} hint={`${money(totals.won_value)} revenue`} icon={Trophy} href="/deals?status=won" />
            <StatCard label="Lost deals" value={formatNumber(totals.lost_deals)} hint={`${totals.win_rate}% win rate`} icon={XCircle} href="/deals?status=lost" />
          </>
        )}
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Pipeline by stage</CardTitle>
            <CardDescription>Value of open deals in each stage</CardDescription>
          </CardHeader>
          <CardContent>
            {data ? (
              <BarChart
                data={data.pipeline}
                categoryKey="stage"
                series={[{ key: "value", label: "Open value", color: "var(--chart-1)" }]}
                format={money}
                axisFormat={compactMoney}
                tooltipExtra={(row) => `${row.count} deals`}
              />
            ) : (
              <Skeleton className="h-64" />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Revenue</CardTitle>
            <CardDescription>Won deal value per month, last 6 months</CardDescription>
          </CardHeader>
          <CardContent>
            {!data ? (
              <Skeleton className="h-64" />
            ) : data.revenue.length ? (
              <BarChart
                data={data.revenue.map((row) => ({ ...row, label: monthLabel(row.month) }))}
                categoryKey="label"
                series={[{ key: "revenue", label: "Revenue", color: "var(--chart-1)" }]}
                format={money}
                axisFormat={compactMoney}
                tooltipExtra={(row) => `${row.deals} deals won`}
              />
            ) : (
              <EmptyState icon={Trophy} title="No won deals yet" description="Revenue appears here when deals are won." />
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
            <CardAction>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/activities">View all</Link>
              </Button>
            </CardAction>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-64" />
            ) : activityItems.length ? (
              <ActivityTimeline items={activityItems} />
            ) : (
              <EmptyState icon={History} title="No activity yet" />
            )}
          </CardContent>
        </Card>
        <div className="space-y-6">
          <Card className="gap-3">
            <CardHeader>
              <CardTitle>My upcoming tasks</CardTitle>
              <CardDescription>Due in the next 14 days</CardDescription>
              <CardAction>
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/tasks">View all</Link>
                </Button>
              </CardAction>
            </CardHeader>
            <CardContent className="px-2">
              {isLoading ? (
                <Skeleton className="h-40" />
              ) : data?.upcoming_tasks.length ? (
                <div className="divide-y">
                  {data.upcoming_tasks.map((task) => (
                    <TaskItem key={task.id} task={task} />
                  ))}
                </div>
              ) : (
                <EmptyState icon={CheckSquare} title="You're all caught up" />
              )}
            </CardContent>
          </Card>
          <Card className="gap-3">
            <CardHeader>
              <CardTitle>Lead sources</CardTitle>
              <CardDescription>Leads and conversion rate by source</CardDescription>
            </CardHeader>
            <CardContent>
              {data?.lead_sources.length ? (
                <ul className="space-y-3">
                  {data.lead_sources.map((row) => {
                    const max = Math.max(...data.lead_sources.map((r) => r.leads));
                    return (
                      <li key={row.source} className="space-y-1 text-sm">
                        <div className="flex justify-between gap-2">
                          <span>{humanize(row.source)}</span>
                          <span className="text-muted-foreground tabular-nums">
                            {row.leads} · {row.conversion_rate}% converted
                          </span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                          <div className="h-full rounded-full bg-(--chart-1)" style={{ width: `${(row.leads / max) * 100}%` }} />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <EmptyState icon={Target} title="No leads yet" />
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
