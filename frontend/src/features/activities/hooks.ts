import { useQuery } from "@tanstack/react-query";

import { createResourceHooks } from "@/hooks/use-resource";
import { activitiesService, notesService, tasksService, timelineService } from "@/services/activities";
import type { RecordLinks } from "@/types";

export const activityHooks = createResourceHooks("activities", activitiesService, { label: "Activity" });
export const noteHooks = createResourceHooks("notes", notesService, { label: "Note" });
export const taskHooks = createResourceHooks("tasks", tasksService, { label: "Task" });

export function useTimeline(links: RecordLinks) {
  return useQuery({ queryKey: ["timeline", links], queryFn: () => timelineService.get(links) });
}
