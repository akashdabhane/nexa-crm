export type UserRole = "admin" | "manager" | "sales_rep";

export interface Profile {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

/** Compact user embedded in other resources (e.g. a record's owner). */
export interface UserSummary {
  id: string;
  full_name: string;
  email: string;
}

/** Minimal reference to a related record (id + display name). */
export interface EntityRef {
  id: string;
  name: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export type SortOrder = "asc" | "desc";

export interface ListParams {
  page?: number;
  page_size?: number;
  search?: string;
  sort_by?: string;
  sort_order?: SortOrder;
  [filter: string]: string | number | boolean | undefined;
}

interface Timestamps {
  created_at: string;
  updated_at: string;
}

// --- Companies & contacts ----------------------------------------------------

export interface Company extends Timestamps {
  id: string;
  name: string;
  industry: string | null;
  website: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  city: string | null;
  country: string | null;
  employee_count: number | null;
  owner: UserSummary | null;
  contact_count: number;
  deal_count: number;
  open_deal_value: number;
}

export interface CompanyInput {
  name: string;
  industry?: string | null;
  website?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  city?: string | null;
  country?: string | null;
  employee_count?: number | null;
  owner_id?: string | null;
}

export const CONTACT_STATUSES = ["active", "customer", "inactive"] as const;
export type ContactStatus = (typeof CONTACT_STATUSES)[number];

export interface Contact extends Timestamps {
  id: string;
  first_name: string;
  last_name: string | null;
  full_name: string;
  email: string | null;
  phone: string | null;
  job_title: string | null;
  website: string | null;
  address: string | null;
  city: string | null;
  country: string | null;
  status: ContactStatus;
  tags: string[];
  company: EntityRef | null;
  owner: UserSummary | null;
}

export interface ContactInput {
  first_name: string;
  last_name?: string | null;
  email?: string | null;
  phone?: string | null;
  job_title?: string | null;
  website?: string | null;
  address?: string | null;
  city?: string | null;
  country?: string | null;
  status?: ContactStatus;
  tags?: string[];
  company_id?: string | null;
  owner_id?: string | null;
}

// --- Leads -------------------------------------------------------------------

export const LEAD_STATUSES = ["new", "contacted", "qualified", "unqualified", "converted"] as const;
export type LeadStatus = (typeof LEAD_STATUSES)[number];

export const LEAD_SOURCES = ["website", "referral", "advertisement", "social_media", "email", "cold_call", "other"] as const;
export type LeadSource = (typeof LEAD_SOURCES)[number];

export interface Lead extends Timestamps {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  company_name: string | null;
  source: LeadSource;
  status: LeadStatus;
  score: number;
  owner: UserSummary | null;
  converted_at: string | null;
  converted_contact_id: string | null;
  converted_company_id: string | null;
  converted_deal_id: string | null;
}

export interface LeadInput {
  name: string;
  email?: string | null;
  phone?: string | null;
  company_name?: string | null;
  source?: LeadSource;
  status?: LeadStatus;
  score?: number;
  owner_id?: string | null;
}

export interface LeadConvertInput {
  company_id?: string | null;
  create_deal: boolean;
  deal_name?: string | null;
  deal_value?: number;
  expected_close_date?: string | null;
}

export interface LeadConvertResult {
  lead: Lead;
  contact_id: string;
  company_id: string | null;
  deal_id: string | null;
}

// --- Pipelines & deals -------------------------------------------------------

export type StageType = "open" | "won" | "lost";
export type DealStatus = StageType;
export const DEAL_STATUSES = ["open", "won", "lost"] as const;
export const CURRENCIES = ["USD", "EUR", "GBP", "INR", "CAD", "AUD"] as const;

export interface Stage {
  id: string;
  name: string;
  position: number;
  probability: number;
  stage_type: StageType;
}

export interface Pipeline {
  id: string;
  name: string;
  is_default: boolean;
  stages: Stage[];
}

export interface Deal extends Timestamps {
  id: string;
  name: string;
  value: number;
  currency: string;
  pipeline_id: string;
  stage: Stage;
  status: DealStatus;
  probability: number;
  expected_close_date: string | null;
  closed_at: string | null;
  company: EntityRef | null;
  contact: EntityRef | null;
  owner: UserSummary | null;
  description: string | null;
}

export interface DealInput {
  name: string;
  value?: number;
  currency?: string;
  pipeline_id?: string | null;
  stage_id?: string | null;
  probability?: number | null;
  expected_close_date?: string | null;
  company_id?: string | null;
  contact_id?: string | null;
  owner_id?: string | null;
  description?: string | null;
}

export interface BoardColumn {
  stage: Stage;
  deals: Deal[];
  count: number;
  total_value: number;
}

export interface DealBoard {
  pipeline_id: string;
  columns: BoardColumn[];
}

// --- Activities, notes, tasks --------------------------------------------------

export const ACTIVITY_TYPES = ["call", "meeting", "email"] as const;
export type ActivityType = (typeof ACTIVITY_TYPES)[number];

/** Which records an activity / note / task is attached to. */
export interface RecordLinks {
  contact_id?: string | null;
  company_id?: string | null;
  lead_id?: string | null;
  deal_id?: string | null;
}

interface LinkedRefs {
  contact: EntityRef | null;
  company: EntityRef | null;
  lead?: EntityRef | null;
  deal: EntityRef | null;
}

export interface Activity extends LinkedRefs {
  id: string;
  type: ActivityType;
  subject: string;
  description: string | null;
  occurred_at: string;
  duration_minutes: number | null;
  owner: UserSummary | null;
  created_at: string;
}

export interface ActivityInput extends RecordLinks {
  type: ActivityType;
  subject: string;
  description?: string | null;
  occurred_at?: string | null;
  duration_minutes?: number | null;
}

export interface Note extends LinkedRefs, Timestamps {
  id: string;
  body: string;
  owner: UserSummary | null;
}

export interface NoteInput extends RecordLinks {
  body: string;
}

export type TimelineItem =
  | { kind: "activity"; occurred_at: string; activity: Activity; note: null }
  | { kind: "note"; occurred_at: string; activity: null; note: Note };

export const TASK_STATUSES = ["pending", "in_progress", "completed", "cancelled"] as const;
export type TaskStatus = (typeof TASK_STATUSES)[number];
export const TASK_PRIORITIES = ["low", "medium", "high", "urgent"] as const;
export type TaskPriority = (typeof TASK_PRIORITIES)[number];

export interface Task extends LinkedRefs, Timestamps {
  id: string;
  title: string;
  description: string | null;
  due_date: string | null;
  priority: TaskPriority;
  status: TaskStatus;
  is_overdue: boolean;
  completed_at: string | null;
  owner: UserSummary | null;
}

export interface TaskInput {
  title: string;
  description?: string | null;
  due_date?: string | null;
  priority?: TaskPriority;
  status?: TaskStatus;
  owner_id?: string | null;
  contact_id?: string | null;
  company_id?: string | null;
  deal_id?: string | null;
}

// --- Notifications & audit log ----------------------------------------------------

export type NotificationType = "lead_assigned" | "deal_assigned" | "task_assigned" | "task_due" | "deal_won" | "deal_lost";

export interface AppNotification {
  id: string;
  type: NotificationType;
  title: string;
  message: string | null;
  entity_type: string | null;
  entity_id: string | null;
  is_read: boolean;
  created_at: string;
}

export interface AuditLog {
  id: string;
  user: UserSummary | null;
  action: string;
  entity_type: string;
  entity_id: string;
  details: { name?: string; changes?: Record<string, [unknown, unknown]>; from?: string; to?: string; [key: string]: unknown };
  created_at: string;
}
