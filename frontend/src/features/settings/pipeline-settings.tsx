"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useDefaultPipeline } from "@/features/deals/hooks";
import { getErrorMessage } from "@/lib/api-client";
import { pipelinesService } from "@/services/deals";
import type { Stage } from "@/types";

function StageRow({ stage }: { stage: Stage }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState(stage.name);
  const [probability, setProbability] = useState(String(stage.probability));
  const save = useMutation({
    mutationFn: () => pipelinesService.updateStage(stage.id, { name: name.trim(), probability: Number(probability) }),
    onSuccess: () => {
      toast.success("Stage updated");
      return Promise.all(["pipelines", "board", "deals"].map((key) => queryClient.invalidateQueries({ queryKey: [key] })));
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
  const probabilityNumber = Number(probability);
  const valid = name.trim() && /^\d+$/.test(probability) && probabilityNumber <= 100;
  const dirty = name !== stage.name || probability !== String(stage.probability);

  return (
    <div className="flex flex-wrap items-center gap-2 py-2">
      <span className="w-6 text-sm text-muted-foreground">{stage.position + 1}.</span>
      <Input className="w-44" value={name} onChange={(e) => setName(e.target.value)} aria-label="Stage name" />
      <div className="flex items-center gap-1">
        <Input
          className="w-20"
          inputMode="numeric"
          value={probability}
          onChange={(e) => setProbability(e.target.value)}
          aria-label="Default probability"
          disabled={stage.stage_type !== "open"}
        />
        <span className="text-sm text-muted-foreground">%</span>
      </div>
      <StatusBadge value={stage.stage_type} label={stage.stage_type === "open" ? "Open" : stage.stage_type === "won" ? "Won" : "Lost"} />
      <Button size="sm" variant="outline" disabled={!dirty || !valid || save.isPending} onClick={() => save.mutate()}>
        Save
      </Button>
    </div>
  );
}

export function PipelineSettings() {
  const { pipeline, isLoading } = useDefaultPipeline();
  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline stages</CardTitle>
        <CardDescription>
          Rename stages or change the default win probability. Changing a probability also updates open deals in that stage.
        </CardDescription>
      </CardHeader>
      <CardContent className="divide-y">
        {isLoading || !pipeline ? <Skeleton className="h-48" /> : pipeline.stages.map((stage) => <StageRow key={stage.id} stage={stage} />)}
      </CardContent>
    </Card>
  );
}
