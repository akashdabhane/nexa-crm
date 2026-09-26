import { api } from "@/lib/api-client";
import type { Activity, ActivityInput, Note, NoteInput, RecordLinks, Task, TaskInput, TimelineItem } from "@/types";

import { createCrudService } from "./crud";

export const activitiesService = createCrudService<Activity, ActivityInput>("/activities");
export const notesService = createCrudService<Note, NoteInput>("/notes");
export const tasksService = createCrudService<Task, TaskInput>("/tasks");

export const timelineService = {
  get: (links: RecordLinks) => api.get<TimelineItem[]>("/timeline", { params: links }).then((r) => r.data),
};
