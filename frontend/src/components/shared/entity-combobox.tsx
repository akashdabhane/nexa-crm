"use client";

import { useQuery } from "@tanstack/react-query";
import { Check, ChevronsUpDown, X } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import type { EntityRef } from "@/types";

type EntityComboboxProps = {
  /** Cache key namespace, e.g. "companies". */
  queryKey: string;
  fetchOptions: (search: string) => Promise<EntityRef[]>;
  value: string | null | undefined;
  /** Label for the current value when it isn't in the fetched list yet. */
  selectedLabel?: string | null;
  onChange: (value: string | null, option: EntityRef | null) => void;
  placeholder?: string;
  id?: string;
  disabled?: boolean;
};

/** Searchable select that loads id/name options from the API as you type. */
export function EntityCombobox({
  queryKey,
  fetchOptions,
  value,
  selectedLabel,
  onChange,
  placeholder = "Select…",
  id,
  disabled,
}: EntityComboboxProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const { data: options = [], isFetching } = useQuery({
    queryKey: [queryKey, "options", search],
    queryFn: () => fetchOptions(search),
    enabled: open,
  });
  const [picked, setPicked] = useState<EntityRef | null>(null);
  const label =
    (picked?.id === value ? picked?.name : null) ?? options.find((o) => o.id === value)?.name ?? selectedLabel;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className="w-full justify-between font-normal"
        >
          <span className={cn("truncate", !value && "text-muted-foreground")}>{value ? label ?? "Selected" : placeholder}</span>
          <span className="flex items-center gap-1">
            {value && !disabled && (
              <X
                className="size-4 opacity-60 hover:opacity-100"
                onClick={(event) => {
                  event.stopPropagation();
                  onChange(null, null);
                }}
              />
            )}
            <ChevronsUpDown className="size-4 opacity-50" />
          </span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-(--radix-popover-trigger-width) p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput placeholder="Search…" value={search} onValueChange={setSearch} />
          <CommandList>
            <CommandEmpty>{isFetching ? "Loading…" : "No results."}</CommandEmpty>
            <CommandGroup>
              {options.map((option) => (
                <CommandItem
                  key={option.id}
                  value={option.id}
                  onSelect={() => {
                    setPicked(option);
                    onChange(option.id, option);
                    setOpen(false);
                  }}
                >
                  <Check className={cn("size-4", value === option.id ? "opacity-100" : "opacity-0")} />
                  {option.name}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
