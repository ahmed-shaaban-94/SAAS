"use client";

import { useEffect, useState } from "react";
import { Responsive, useContainerWidth } from "react-grid-layout";
import {
  Save,
  Plus,
  X,
  GripVertical,
  RotateCcw,
  Lock,
  Unlock,
  Trash2,
} from "lucide-react";
import { useDashboardLayout, type LayoutItem } from "@/hooks/use-dashboard-layout";
import { WidgetRenderer } from "@/components/dashboard-builder/widget-renderer";
import {
  WIDGET_CATALOG,
  CATEGORY_LABELS,
  type WidgetDef,
} from "@/components/dashboard-builder/widget-catalog";
import { useToast } from "@/components/ui/toast";
import { DashboardContent } from "../dashboard/dashboard-content";

import "react-grid-layout/css/styles.css";

// react-grid-layout v2 uses useContainerWidth instead of WidthProvider

function WidgetPickerPanel({
  open,
  onClose,
  onAdd,
  activeWidgets,
}: {
  open: boolean;
  onClose: () => void;
  onAdd: (widget: WidgetDef) => void;
  activeWidgets: Set<string>;
}) {
  const [search, setSearch] = useState("");

  if (!open) return null;

  const filtered = WIDGET_CATALOG.filter(
    (w) =>
      w.label.toLowerCase().includes(search.toLowerCase()) ||
      w.description.toLowerCase().includes(search.toLowerCase())
  );

  const grouped = Object.entries(CATEGORY_LABELS).map(([cat, label]) => ({
    category: cat,
    label,
    widgets: filtered.filter((w) => w.category === cat),
  })).filter((g) => g.widgets.length > 0);

  return (
    <div className="fixed right-0 top-0 z-50 flex h-screen w-80 flex-col border-l border-border bg-card shadow-xl">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="text-sm font-semibold text-text-primary">Add Widget</h3>
        <button onClick={onClose} className="p-1 text-text-secondary hover:text-text-primary">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="px-4 py-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search widgets..."
          className="w-full rounded-md border border-border bg-page px-3 py-1.5 text-sm text-text-primary outline-none focus:border-accent"
        />
      </div>
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {grouped.map((group) => (
          <div key={group.category} className="mb-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-text-secondary">
              {group.label}
            </p>
            <div className="space-y-1.5">
              {group.widgets.map((w) => {
                const isActive = activeWidgets.has(w.key);
                return (
                  <button
                    key={w.key}
                    onClick={() => !isActive && onAdd(w)}
                    disabled={isActive}
                    className={`flex w-full items-start gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors ${
                      isActive
                        ? "border-accent/30 bg-accent/5 opacity-60"
                        : "border-border hover:border-accent hover:bg-accent/5"
                    }`}
                  >
                    <div className="flex-1">
                      <p className="text-sm font-medium text-text-primary">{w.label}</p>
                      <p className="text-xs text-text-secondary">{w.description}</p>
                    </div>
                    {isActive ? (
                      <span className="text-[10px] text-accent">Added</span>
                    ) : (
                      <Plus className="h-4 w-4 text-accent" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function MyDashboardPage() {
  const { layout: savedLayout, isLoading, saveLayout } = useDashboardLayout();
  const { containerRef, width } = useContainerWidth();
  const { success: toastSuccess, error: toastError } = useToast();
  const [layout, setLayout] = useState<LayoutItem[]>([]);
  const [initialized, setInitialized] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [locked, setLocked] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!isLoading && !initialized) {
      setLayout(savedLayout.length > 0 ? savedLayout : getDefaultLayout());
      setInitialized(true);
    }
  }, [isLoading, initialized, savedLayout]);

  const activeWidgets = new Set(layout.map((item) => item.i));

  function handleLayoutChange(newLayout: LayoutItem[]) {
    // react-grid-layout fires this on every render; only mark dirty if positions changed
    const changed = newLayout.some((item, idx) => {
      const old = layout[idx];
      if (!old) return true;
      return item.x !== old.x || item.y !== old.y || item.w !== old.w || item.h !== old.h;
    });
    if (changed) {
      setLayout(newLayout.map((item) => ({
        i: item.i,
        x: item.x,
        y: item.y,
        w: item.w,
        h: item.h,
        minW: item.minW,
        minH: item.minH,
      })));
      setDirty(true);
    }
  }

  function addWidget(widget: WidgetDef) {
    // Find lowest Y position to place new widget
    const maxY = layout.reduce((max, item) => Math.max(max, item.y + item.h), 0);
    const newItem: LayoutItem = {
      i: widget.key,
      x: 0,
      y: maxY,
      w: widget.defaultW,
      h: widget.defaultH,
      minW: widget.minW,
      minH: widget.minH,
    };
    setLayout((prev) => [...prev, newItem]);
    setDirty(true);
  }

  function removeWidget(key: string) {
    setLayout((prev) => prev.filter((item) => item.i !== key));
    setDirty(true);
  }

  async function handleSave() {
    setSaving(true);
    try {
      await saveLayout(layout);
      setDirty(false);
      toastSuccess("Dashboard layout saved!");
    } catch {
      toastError("Failed to save layout. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  function handleReset() {
    setLayout(getDefaultLayout());
    setDirty(true);
  }

  if (isLoading || !initialized) {
    return (
      <div className="space-y-4 p-6">
        <div className="h-8 w-64 animate-pulse rounded-lg bg-card" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-48 animate-pulse rounded-xl bg-card" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-3 sm:p-4 lg:p-6">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-xl font-bold text-text-primary">My Dashboard</h1>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setLocked(!locked)}
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
              locked
                ? "border-chart-amber/30 bg-chart-amber/10 text-chart-amber"
                : "border-border text-text-secondary hover:bg-divider"
            }`}
          >
            {locked ? <Lock className="h-3.5 w-3.5" /> : <Unlock className="h-3.5 w-3.5" />}
            {locked ? "Locked" : "Unlocked"}
          </button>
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-text-secondary hover:bg-divider"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Reset
          </button>
          <button
            onClick={() => setPickerOpen(true)}
            className="flex items-center gap-1.5 rounded-lg border border-accent/30 bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent hover:bg-accent/20"
          >
            <Plus className="h-3.5 w-3.5" />
            Add Widget
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !dirty}
            className="flex items-center gap-1.5 rounded-lg bg-accent px-4 py-1.5 text-xs font-semibold text-page hover:bg-accent/90 disabled:opacity-50"
          >
            <Save className="h-3.5 w-3.5" />
            {saving ? "Saving..." : dirty ? "Save Layout" : "Saved"}
          </button>
        </div>
      </div>

      <DashboardContent>
        {layout.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-border py-24">
            <p className="mb-2 text-sm text-text-secondary">Your dashboard is empty</p>
            <button
              onClick={() => setPickerOpen(true)}
              className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-page hover:bg-accent/90"
            >
              <Plus className="h-4 w-4" />
              Add your first widget
            </button>
          </div>
        ) : (
          <Responsive
            innerRef={containerRef as React.RefObject<HTMLDivElement>}
            width={width || 1024}
            className="layout"
            layouts={{ lg: layout }}
            breakpoints={{ lg: 1024, md: 768, sm: 480, xs: 0 }}
            cols={{ lg: 4, md: 3, sm: 2, xs: 1 }}
            rowHeight={100}
            dragConfig={{ enabled: !locked, handle: ".drag-handle" }}
            resizeConfig={{ enabled: !locked }}
            onLayoutChange={(newLayout) => handleLayoutChange([...newLayout] as LayoutItem[])}
            margin={[12, 12] as [number, number]}
          >
            {layout.map((item) => (
              <div
                key={item.i}
                className="group overflow-hidden rounded-xl border border-border bg-card shadow-sm"
              >
                {/* Widget header with drag handle */}
                <div className="flex items-center gap-1 border-b border-border/50 bg-card px-3 py-1.5">
                  {!locked && (
                    <div className="drag-handle cursor-grab text-text-secondary/50 hover:text-text-secondary">
                      <GripVertical className="h-4 w-4" />
                    </div>
                  )}
                  <span className="flex-1 text-xs font-medium text-text-secondary">
                    {WIDGET_CATALOG.find((w) => w.key === item.i)?.label ?? item.i}
                  </span>
                  {!locked && (
                    <button
                      onClick={() => removeWidget(item.i)}
                      className="rounded p-0.5 text-text-secondary/50 opacity-0 transition-opacity hover:bg-growth-red/10 hover:text-growth-red group-hover:opacity-100"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
                {/* Widget content */}
                <div className="h-[calc(100%-32px)] overflow-auto p-2">
                  <WidgetRenderer widgetKey={item.i} />
                </div>
              </div>
            ))}
          </Responsive>
        )}
      </DashboardContent>

      {/* Widget Picker */}
      <WidgetPickerPanel
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onAdd={(w) => {
          addWidget(w);
          setPickerOpen(false);
        }}
        activeWidgets={activeWidgets}
      />
    </div>
  );
}

function getDefaultLayout(): LayoutItem[] {
  return [
    { i: "kpi-grid", x: 0, y: 0, w: 4, h: 2, minW: 2, minH: 2 },
    { i: "daily-trend", x: 0, y: 2, w: 2, h: 3, minW: 2, minH: 2 },
    { i: "monthly-trend", x: 2, y: 2, w: 2, h: 3, minW: 2, minH: 2 },
    { i: "top-products", x: 0, y: 5, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "top-customers", x: 2, y: 5, w: 2, h: 4, minW: 2, minH: 3 },
    { i: "narrative", x: 0, y: 9, w: 4, h: 2, minW: 2, minH: 2 },
  ];
}
