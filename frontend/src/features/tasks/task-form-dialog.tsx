"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { EntityCombobox } from "@/components/shared/entity-combobox";
import { FormField } from "@/components/shared/form-field";
import { UserSelect } from "@/components/shared/user-select";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { taskHooks } from "@/features/activities/hooks";
import { useCurrentUser } from "@/hooks/use-current-user";
import { companiesService } from "@/services/companies";
import { contactsService } from "@/services/contacts";
import { dealsService } from "@/services/deals";
import { TASK_PRIORITIES, TASK_STATUSES, type EntityRef, type Task, type TaskInput } from "@/types";
import { humanize } from "@/utils/format";

const schema = z.object({
  title: z.string().trim().min(1, "Title is required").max(255),
  description: z.string(),
  due_date: z.string(),
  priority: z.enum(TASK_PRIORITIES),
  status: z.enum(TASK_STATUSES),
  owner_id: z.string().nullable(),
  contact_id: z.string().nullable(),
  company_id: z.string().nullable(),
  deal_id: z.string().nullable(),
});
type Values = z.infer<typeof schema>;

export type TaskDefaults = { contact?: EntityRef | null; company?: EntityRef | null; deal?: EntityRef | null };

function toValues(task?: Task, defaults: TaskDefaults = {}): Values {
  return {
    title: task?.title ?? "",
    description: task?.description ?? "",
    due_date: task?.due_date ?? "",
    priority: task?.priority ?? "medium",
    status: task?.status ?? "pending",
    owner_id: task?.owner?.id ?? null,
    contact_id: task?.contact?.id ?? defaults.contact?.id ?? null,
    company_id: task?.company?.id ?? defaults.company?.id ?? null,
    deal_id: task?.deal?.id ?? defaults.deal?.id ?? null,
  };
}

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  task?: Task;
  defaults?: TaskDefaults;
};

function EnumSelect<T extends string>({ id, value, onChange, options }: { id: string; value: T; onChange: (v: T) => void; options: readonly T[] }) {
  return (
    <Select value={value} onValueChange={(v) => onChange(v as T)}>
      <SelectTrigger id={id} className="w-full">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem key={option} value={option}>
            {humanize(option)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function TaskFormDialog({ open, onOpenChange, task, defaults }: Props) {
  const { isManager } = useCurrentUser();
  const create = taskHooks.useCreate();
  const update = taskHooks.useUpdate();
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema), values: toValues(task, defaults) });

  async function onSubmit({ owner_id, due_date, ...values }: Values) {
    const data: TaskInput = { ...values, due_date: due_date || null, ...(isManager ? { owner_id } : {}) };
    try {
      if (task) await update.mutateAsync({ id: task.id, data });
      else await create.mutateAsync(data);
      onOpenChange(false);
    } catch {
      // Error toast already shown.
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{task ? "Edit task" : "New task"}</DialogTitle>
          <DialogDescription>A follow-up or to-do, optionally linked to a record.</DialogDescription>
        </DialogHeader>
        <form id="task-form" onSubmit={handleSubmit(onSubmit)} className="grid max-h-[65vh] gap-4 overflow-y-auto px-1 sm:grid-cols-2" noValidate>
          <FormField label="Title" htmlFor="title" required error={errors.title?.message} className="sm:col-span-2">
            <Input id="title" placeholder="e.g. Send proposal" {...register("title")} />
          </FormField>
          <FormField label="Due date" htmlFor="due_date">
            <Input id="due_date" type="date" {...register("due_date")} />
          </FormField>
          <FormField label="Priority" htmlFor="priority">
            <Controller
              control={control}
              name="priority"
              render={({ field }) => <EnumSelect id="priority" value={field.value} onChange={field.onChange} options={TASK_PRIORITIES} />}
            />
          </FormField>
          <FormField label="Status" htmlFor="status">
            <Controller
              control={control}
              name="status"
              render={({ field }) => <EnumSelect id="status" value={field.value} onChange={field.onChange} options={TASK_STATUSES} />}
            />
          </FormField>
          {isManager ? (
            <FormField label="Assigned to" htmlFor="owner_id">
              <Controller
                control={control}
                name="owner_id"
                render={({ field }) => <UserSelect id="owner_id" value={field.value} onChange={field.onChange} placeholder="Me" />}
              />
            </FormField>
          ) : (
            <div />
          )}
          <FormField label="Contact" htmlFor="contact_id">
            <Controller
              control={control}
              name="contact_id"
              render={({ field }) => (
                <EntityCombobox
                  id="contact_id"
                  queryKey="contacts"
                  fetchOptions={(search) => contactsService.options({ search })}
                  value={field.value}
                  selectedLabel={task?.contact?.name ?? defaults?.contact?.name}
                  onChange={field.onChange}
                  placeholder="None"
                />
              )}
            />
          </FormField>
          <FormField label="Company" htmlFor="company_id">
            <Controller
              control={control}
              name="company_id"
              render={({ field }) => (
                <EntityCombobox
                  id="company_id"
                  queryKey="companies"
                  fetchOptions={(search) => companiesService.options({ search })}
                  value={field.value}
                  selectedLabel={task?.company?.name ?? defaults?.company?.name}
                  onChange={field.onChange}
                  placeholder="None"
                />
              )}
            />
          </FormField>
          <FormField label="Deal" htmlFor="deal_id" className="sm:col-span-2">
            <Controller
              control={control}
              name="deal_id"
              render={({ field }) => (
                <EntityCombobox
                  id="deal_id"
                  queryKey="deals"
                  fetchOptions={(search) =>
                    dealsService.list({ search, page_size: 20 }).then((page) => page.items.map((d) => ({ id: d.id, name: d.name })))
                  }
                  value={field.value}
                  selectedLabel={task?.deal?.name ?? defaults?.deal?.name}
                  onChange={field.onChange}
                  placeholder="None"
                />
              )}
            />
          </FormField>
          <FormField label="Description" htmlFor="description" className="sm:col-span-2">
            <Textarea id="description" rows={3} {...register("description")} />
          </FormField>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="task-form" disabled={isSubmitting}>
            {isSubmitting ? "Saving…" : task ? "Save changes" : "Create task"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
