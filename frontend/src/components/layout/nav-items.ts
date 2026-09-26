import {
  Activity,
  BarChart3,
  Bell,
  Building2,
  CheckSquare,
  Handshake,
  KanbanSquare,
  LayoutDashboard,
  Settings,
  Target,
  Users,
  type LucideIcon,
} from "lucide-react";

export type NavItem = { title: string; href: string; icon: LucideIcon };

export const navGroups: { label: string; items: NavItem[] }[] = [
  {
    label: "Overview",
    items: [
      { title: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      { title: "Reports", href: "/reports", icon: BarChart3 },
    ],
  },
  {
    label: "CRM",
    items: [
      { title: "Contacts", href: "/contacts", icon: Users },
      { title: "Companies", href: "/companies", icon: Building2 },
      { title: "Leads", href: "/leads", icon: Target },
      { title: "Deals", href: "/deals", icon: Handshake },
      { title: "Pipeline", href: "/pipeline", icon: KanbanSquare },
    ],
  },
  {
    label: "Work",
    items: [
      { title: "Activities", href: "/activities", icon: Activity },
      { title: "Tasks", href: "/tasks", icon: CheckSquare },
      { title: "Notifications", href: "/notifications", icon: Bell },
    ],
  },
  {
    label: "Account",
    items: [{ title: "Settings", href: "/settings", icon: Settings }],
  },
];
