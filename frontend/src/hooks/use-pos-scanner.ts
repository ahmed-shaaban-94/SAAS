"use client";

import { useCallback, useEffect, useRef } from "react";
import {
  attachScannerListener,
  type ScannerConfig,
  type ScannerHandle,
} from "@/lib/pos/scanner-keymap";
import { hasElectron, electron } from "@/lib/pos/ipc";

export type { ScannerConfig };

export interface PosScannerOptions {
  onScan?: (code: string) => void;
  onMiss?: (partial: string) => void;
  config?: ScannerConfig;
}

export function usePosScanner(options?: PosScannerOptions): { reset: () => void } {
  const handleRef = useRef<ScannerHandle | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const stableOnScan = useCallback((code: string) => {
    optionsRef.current?.onScan?.(code);
  }, []);

  const stableOnMiss = useCallback((partial: string) => {
    optionsRef.current?.onMiss?.(partial);
  }, []);

  useEffect(() => {
    const handle = attachScannerListener(
      { onScan: stableOnScan, onMiss: stableOnMiss },
      optionsRef.current?.config,
    );
    handleRef.current = handle;

    let unsubscribeIpc: (() => void) | null = null;
    if (hasElectron() && typeof electron().onBarcodeScanned === "function") {
      unsubscribeIpc = electron().onBarcodeScanned((barcode) => {
        optionsRef.current?.onScan?.(barcode);
      });
    }

    return () => {
      handle.stop();
      unsubscribeIpc?.();
    };
  }, [stableOnScan, stableOnMiss]);

  const reset = useCallback(() => {
    handleRef.current?.reset();
  }, []);

  return { reset };
}
