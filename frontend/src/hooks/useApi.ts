import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

const ACTIVE = new Set(["queued", "processing"]);

export function useUsage() {
  // Keyed by account so limits switch immediately on sign-in / sign-out.
  const who = useAuthStore((s) => s.user?.id ?? s.status);
  return useQuery({ queryKey: ["usage", who], queryFn: api.usage, staleTime: 30_000 });
}

/** Polls while the task is queued or processing. SSE replaces this later (docs/TZ.md F-10). */
export function useTask(id: string | null) {
  return useQuery({
    queryKey: ["task", id],
    queryFn: () => api.task(id as string),
    enabled: id !== null,
    refetchInterval: (query) => (query.state.data && ACTIVE.has(query.state.data.status) ? 1000 : false),
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 2,
  });
}

export function useDeleteTask() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: api.deleteTask,
    onSuccess: (_data, id) => client.invalidateQueries({ queryKey: ["task", id] }),
  });
}
