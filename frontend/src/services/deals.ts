import { api } from "@/lib/api-client";
import type { Deal, DealBoard, DealInput, Pipeline, Stage } from "@/types";

import { createCrudService } from "./crud";

export const dealsService = {
  ...createCrudService<Deal, DealInput>("/deals"),
  board: (params: { pipeline_id?: string; search?: string; owner_id?: string }) =>
    api.get<DealBoard>("/deals/board", { params }).then((r) => r.data),
  move: (id: string, stageId: string) => api.patch<Deal>(`/deals/${id}/stage`, { stage_id: stageId }).then((r) => r.data),
};

export const pipelinesService = {
  list: () => api.get<Pipeline[]>("/pipelines").then((r) => r.data),
  updateStage: (id: string, data: { name?: string; probability?: number }) =>
    api.patch<Stage>(`/pipelines/stages/${id}`, data).then((r) => r.data),
};
