"use client";

import { useQuery } from "@tanstack/react-query";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { usersService } from "@/services/users";

const NONE = "__none__";

export function useUsers() {
  return useQuery({ queryKey: ["users"], queryFn: usersService.list, staleTime: 5 * 60_000 });
}

/** Dropdown of active users, used for "Assigned to" fields. */
export function UserSelect({
  value,
  onChange,
  id,
  disabled,
  allowEmpty = false,
  placeholder = "Select user",
}: {
  value: string | null | undefined;
  onChange: (value: string | null) => void;
  id?: string;
  disabled?: boolean;
  allowEmpty?: boolean;
  placeholder?: string;
}) {
  const { data: users = [] } = useUsers();
  return (
    <Select value={value ?? NONE} onValueChange={(next) => onChange(next === NONE ? null : next)} disabled={disabled}>
      <SelectTrigger id={id} className="w-full">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {allowEmpty && <SelectItem value={NONE}>Unassigned</SelectItem>}
        {users
          .filter((user) => user.is_active || user.id === value)
          .map((user) => (
            <SelectItem key={user.id} value={user.id}>
              {user.full_name}
            </SelectItem>
          ))}
      </SelectContent>
    </Select>
  );
}
