"use client";

/**
 * useManagerOverride — wraps destructive cart actions in a manager PIN gate.
 *
 * Usage:
 *   const { requestOverride, overrideOpen, overrideLabel, approveOverride, cancelOverride } =
 *     useManagerOverride();
 *
 *   // In event handler:
 *   requestOverride("حذف صنف من السلة", () => removeItem(drugCode));
 *
 *   // In JSX:
 *   <ManagerPinOverrideModal
 *     open={overrideOpen}
 *     actionLabel={overrideLabel}
 *     onApproved={approveOverride}
 *     onCancel={cancelOverride}
 *   />
 */

import { useCallback, useRef, useState } from "react";

interface OverrideState {
  open: boolean;
  label: string;
}

export function useManagerOverride() {
  const [state, setState] = useState<OverrideState>({ open: false, label: "" });
  const pendingAction = useRef<(() => void) | null>(null);

  const requestOverride = useCallback((actionLabel: string, action: () => void) => {
    pendingAction.current = action;
    setState({ open: true, label: actionLabel });
  }, []);

  const approveOverride = useCallback(() => {
    const action = pendingAction.current;
    pendingAction.current = null;
    setState({ open: false, label: "" });
    action?.();
  }, []);

  const cancelOverride = useCallback(() => {
    pendingAction.current = null;
    setState({ open: false, label: "" });
  }, []);

  return {
    overrideOpen: state.open,
    overrideLabel: state.label,
    requestOverride,
    approveOverride,
    cancelOverride,
  };
}
