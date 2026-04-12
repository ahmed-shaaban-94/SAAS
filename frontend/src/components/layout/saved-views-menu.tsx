"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Bookmark, ChevronDown, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useSavedViews, type SavedView } from "@/hooks/use-saved-views";
import { useToast } from "@/components/ui/toast";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";

interface SavedViewsMenuProps {
  onNavigate?: () => void;
}

export function SavedViewsMenu({ onNavigate }: SavedViewsMenuProps) {
  const { views, isLoading, deleteView } = useSavedViews();
  const { success, error: toastError } = useToast();
  const router = useRouter();
  const [expanded, setExpanded] = useState(true);
  const [showAll, setShowAll] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<{ id: number; name: string } | null>(null);

  const MAX_VISIBLE = 5;
  const visibleViews = showAll ? views : views.slice(0, MAX_VISIBLE);
  const hasMore = views.length > MAX_VISIBLE;

  const handleApplyView = (view: SavedView) => {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(view.filters)) {
      if (value !== undefined && value !== null) {
        params.set(key, String(value));
      }
    }
    const qs = params.toString();
    const url = qs ? `${view.page_path}?${qs}` : view.page_path;
    router.push(url);
    onNavigate?.();
  };

  const requestDelete = (e: React.MouseEvent, id: number, name: string) => {
    e.stopPropagation();
    e.preventDefault();
    setConfirmDelete({ id, name });
  };

  const handleDelete = async () => {
    if (!confirmDelete) return;
    setDeletingId(confirmDelete.id);
    try {
      await deleteView(confirmDelete.id);
      success(`View "${confirmDelete.name}" deleted`);
    } catch {
      toastError("Failed to delete view");
    } finally {
      setDeletingId(null);
      setConfirmDelete(null);
    }
  };

  if (isLoading) return null;

  return (
    <div className="border-t border-border px-3 py-3">
      {/* Collapsible header */}
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-text-secondary transition-colors hover:text-text-primary"
        aria-expanded={expanded}
      >
        <Bookmark className="h-4 w-4" />
        <span>Saved Views</span>
        {views.length > 0 && (
          <span className="ml-1 text-xs font-normal text-text-secondary/70">
            ({views.length})
          </span>
        )}
        <ChevronDown
          className={cn(
            "ml-auto h-3.5 w-3.5 transition-transform",
            expanded && "rotate-180",
          )}
        />
      </button>

      {/* View list */}
      {expanded && (
        <div className="mt-1 space-y-0.5">
          {views.length === 0 ? (
            <p className="px-3 py-2 text-xs text-text-secondary">
              No saved views yet
            </p>
          ) : (
            <>
              {visibleViews.map((view) => (
                <div
                  key={view.id}
                  className="group flex items-center rounded-lg transition-colors hover:bg-divider"
                >
                  <button
                    onClick={() => handleApplyView(view)}
                    className="flex min-w-0 flex-1 items-center gap-2 px-3 py-2 text-left"
                  >
                    <span
                      className={cn(
                        "truncate text-sm",
                        view.is_default
                          ? "font-medium text-accent"
                          : "text-text-secondary",
                      )}
                    >
                      {view.name}
                    </span>
                  </button>
                  <button
                    onClick={(e) => requestDelete(e, view.id, view.name)}
                    disabled={deletingId === view.id}
                    className="mr-2 hidden rounded-md p-1 text-text-secondary/50 transition-colors hover:bg-growth-red/10 hover:text-growth-red group-hover:block"
                    aria-label={`Delete view "${view.name}"`}
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}

              {hasMore && (
                <button
                  onClick={() => setShowAll((prev) => !prev)}
                  className="px-3 py-1.5 text-xs font-medium text-accent hover:underline"
                >
                  {showAll ? "Show less" : `Show all (${views.length})`}
                </button>
              )}
            </>
          )}
        </div>
      )}

      <ConfirmDialog
        open={!!confirmDelete}
        title="Delete Saved View"
        description={`Delete "${confirmDelete?.name}"? This cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setConfirmDelete(null)}
      />
    </div>
  );
}
