"use client";

import { useState, useCallback } from "react";
// eslint-disable-next-line
const ReactGridLayout = require("react-grid-layout");
import { Settings, Plus, Save, X } from "lucide-react";
import {
  useDashboardLayout,
  type LayoutItem,
} from "@/hooks/use-dashboard-layout";
import { WIDGET_REGISTRY, DEFAULT_LAYOUT } from "./widget-registry";
import { WidgetWrapper } from "./widget-wrapper";
import { WidgetPicker } from "./widget-picker";
import { useToast } from "@/components/ui/toast";

import "react-grid-layout/css/styles.css";

const ResponsiveGridLayout = ReactGridLayout.WidthProvider(
  ReactGridLayout.Responsive,
);

interface GridLayoutItem {
  i: string;
  x: number;
  y: number;
  w: number;
  h: number;
  minW?: number;
  minH?: number;
}

interface DashboardGridProps {
  /** Map of widget ID to React component to render */
  widgets: Record<string, React.ReactNode>;
}

export function DashboardGrid({ widgets }: DashboardGridProps) {
  const { layout: savedLayout, saveLayout } = useDashboardLayout();
  const [editMode, setEditMode] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [currentLayout, setCurrentLayout] = useState<LayoutItem[]>(() =>
    savedLayout.length > 0 ? savedLayout : DEFAULT_LAYOUT,
  );
  const { success } = useToast();

  // Sync when saved layout loads
  const effectiveLayout = editMode
    ? currentLayout
    : savedLayout.length > 0
      ? savedLayout
      : DEFAULT_LAYOUT;

  const handleLayoutChange = useCallback(
    (layout: GridLayoutItem[]) => {
      if (!editMode) return;
      setCurrentLayout(
        layout.map((l) => ({
          i: l.i,
          x: l.x,
          y: l.y,
          w: l.w,
          h: l.h,
          minW: l.minW,
          minH: l.minH,
        })),
      );
    },
    [editMode],
  );

  const handleSave = async () => {
    await saveLayout(currentLayout);
    setEditMode(false);
    success("Dashboard layout saved!");
  };

  const handleCancel = () => {
    setCurrentLayout(
      savedLayout.length > 0 ? savedLayout : DEFAULT_LAYOUT,
    );
    setEditMode(false);
  };

  const handleRemoveWidget = (widgetId: string) => {
    setCurrentLayout((prev) => prev.filter((l) => l.i !== widgetId));
  };

  const handleAddWidget = (widgetId: string) => {
    const def = WIDGET_REGISTRY.find((w) => w.id === widgetId);
    if (!def) return;
    const maxY = currentLayout.reduce(
      (max, l) => Math.max(max, l.y + l.h),
      0,
    );
    setCurrentLayout((prev) => [
      ...prev,
      { i: widgetId, x: 0, y: maxY, ...def.defaultLayout },
    ]);
  };

  const activeWidgetIds = effectiveLayout.map((l) => l.i);

  return (
    <div>
      {/* Toolbar */}
      <div className="mb-4 flex items-center justify-end gap-2">
        {editMode ? (
          <>
            <button
              onClick={() => setPickerOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-text-secondary hover:bg-divider"
            >
              <Plus className="h-3.5 w-3.5" />
              Add Widget
            </button>
            <button
              onClick={handleCancel}
              className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-text-secondary hover:bg-divider"
            >
              <X className="h-3.5 w-3.5" />
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-medium text-white"
            >
              <Save className="h-3.5 w-3.5" />
              Save Layout
            </button>
          </>
        ) : (
          <button
            onClick={() => {
              setCurrentLayout(effectiveLayout);
              setEditMode(true);
            }}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-text-secondary hover:bg-divider"
          >
            <Settings className="h-3.5 w-3.5" />
            Customize
          </button>
        )}
      </div>

      {/* Grid */}
      <ResponsiveGridLayout
        layouts={{ lg: effectiveLayout }}
        breakpoints={{ lg: 1024, md: 768, sm: 480 }}
        cols={{ lg: 12, md: 8, sm: 4 }}
        rowHeight={60}
        isDraggable={editMode}
        isResizable={editMode}
        draggableHandle=".drag-handle"
        onLayoutChange={handleLayoutChange}
        containerPadding={[0, 0]}
        margin={[16, 16]}
      >
        {effectiveLayout.map((item) => {
          const widgetDef = WIDGET_REGISTRY.find((w) => w.id === item.i);
          return (
            <div key={item.i}>
              <WidgetWrapper
                title={widgetDef?.label ?? item.i}
                editMode={editMode}
                onRemove={
                  editMode ? () => handleRemoveWidget(item.i) : undefined
                }
              >
                {widgets[item.i] ?? (
                  <div className="flex h-full items-center justify-center text-sm text-text-secondary">
                    Widget: {item.i}
                  </div>
                )}
              </WidgetWrapper>
            </div>
          );
        })}
      </ResponsiveGridLayout>

      {/* Widget Picker */}
      <WidgetPicker
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onAdd={handleAddWidget}
        activeWidgets={activeWidgetIds}
      />
    </div>
  );
}
