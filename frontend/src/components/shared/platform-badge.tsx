import {
  AtSign,
  Briefcase,
  Camera,
  MessageCircle,
  Music2,
  Play,
  Share2,
  ThumbsUp,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { SocialPlatform } from "@/types";

export const PLATFORM_LABELS: Record<SocialPlatform, string> = {
  facebook: "Facebook",
  instagram: "Instagram",
  twitter: "X (Twitter)",
  linkedin: "LinkedIn",
  tiktok: "TikTok",
  youtube: "YouTube",
  whatsapp: "WhatsApp",
  other: "Other social",
};

const PLATFORM_STYLES: Record<SocialPlatform, { icon: LucideIcon; className: string }> = {
  facebook: { icon: ThumbsUp, className: "bg-blue-600 text-white" },
  instagram: { icon: Camera, className: "bg-gradient-to-br from-amber-400 via-pink-500 to-purple-600 text-white" },
  twitter: { icon: AtSign, className: "bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900" },
  linkedin: { icon: Briefcase, className: "bg-sky-700 text-white" },
  tiktok: { icon: Music2, className: "bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900" },
  youtube: { icon: Play, className: "bg-red-600 text-white" },
  whatsapp: { icon: MessageCircle, className: "bg-emerald-600 text-white" },
  other: { icon: Share2, className: "bg-slate-500 text-white" },
};

/** Small colored tile identifying a social platform. */
export function PlatformIcon({ platform, className }: { platform: SocialPlatform; className?: string }) {
  const { icon: Icon, className: tone } = PLATFORM_STYLES[platform];
  return (
    <span
      className={cn("inline-flex size-5 shrink-0 items-center justify-center rounded-md", tone, className)}
      title={PLATFORM_LABELS[platform]}
      aria-hidden
    >
      <Icon className="size-3" />
    </span>
  );
}

/** Icon + platform name, e.g. in the leads table. */
export function PlatformBadge({ platform, className }: { platform: SocialPlatform; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-sm", className)}>
      <PlatformIcon platform={platform} />
      {PLATFORM_LABELS[platform]}
    </span>
  );
}
