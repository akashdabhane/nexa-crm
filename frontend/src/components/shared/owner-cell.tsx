import type { UserSummary } from "@/types";

import { UserAvatar } from "./user-avatar";

export function OwnerCell({ owner }: { owner: UserSummary | null }) {
  if (!owner) return <span className="text-muted-foreground">Unassigned</span>;
  return (
    <span className="flex items-center gap-2">
      <UserAvatar name={owner.full_name} className="size-6" />
      <span className="truncate">{owner.full_name}</span>
    </span>
  );
}
