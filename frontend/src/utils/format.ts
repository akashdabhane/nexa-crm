const dateFormatter = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" });
const dateTimeFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});
const relativeFormatter = new Intl.RelativeTimeFormat("en-US", { numeric: "auto" });

/** Parses "YYYY-MM-DD" as a local date (not UTC midnight) so it doesn't shift a day. */
function toDate(value: string | Date) {
  if (value instanceof Date) return value;
  return /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value);
}

export function formatDate(value?: string | Date | null) {
  return value ? dateFormatter.format(toDate(value)) : "—";
}

export function formatDateTime(value?: string | Date | null) {
  return value ? dateTimeFormatter.format(toDate(value)) : "—";
}

export function formatRelative(value?: string | Date | null) {
  if (!value) return "—";
  const seconds = (toDate(value).getTime() - Date.now()) / 1000;
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31_536_000],
    ["month", 2_592_000],
    ["week", 604_800],
    ["day", 86_400],
    ["hour", 3_600],
    ["minute", 60],
  ];
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return relativeFormatter.format(Math.round(seconds / size), unit);
  }
  return "just now";
}

export function formatCurrency(value?: number | string | null, currency = "USD", compact = false) {
  if (value === null || value === undefined || value === "") return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    notation: compact ? "compact" : "standard",
    maximumFractionDigits: compact ? 1 : 0,
  }).format(Number(value));
}

export function formatNumber(value?: number | null) {
  return value === null || value === undefined ? "—" : new Intl.NumberFormat("en-US").format(value);
}

/** "social_media" -> "Social media" */
export function humanize(value?: string | null) {
  if (!value) return "—";
  const text = value.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Today's date as "YYYY-MM-DD" in local time. */
export function todayISO() {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}
