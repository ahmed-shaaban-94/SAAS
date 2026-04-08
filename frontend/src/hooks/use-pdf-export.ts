import { useState } from "react";
import { API_BASE_URL } from "@/lib/constants";
import { getSession } from "next-auth/react";

export function usePdfExport() {
  const [isExporting, setIsExporting] = useState(false);

  async function exportDashboardPdf(startDate?: string, endDate?: string) {
    setIsExporting(true);
    try {
      const session = await getSession();
      const headers: Record<string, string> = {};
      if (session?.accessToken) {
        headers["Authorization"] = `Bearer ${session.accessToken}`;
      }

      const params = new URLSearchParams();
      if (startDate) params.set("start_date", startDate);
      if (endDate) params.set("end_date", endDate);
      const qs = params.toString() ? `?${params.toString()}` : "";

      const res = await fetch(`${API_BASE_URL}/api/v1/export/dashboard/pdf${qs}`, { headers });
      if (!res.ok) throw new Error(`Export failed: ${res.status}`);

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "dashboard_report.pdf";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setIsExporting(false);
    }
  }

  async function exportEntityPdf(entity: "products" | "customers" | "staff", startDate?: string, endDate?: string) {
    setIsExporting(true);
    try {
      const session = await getSession();
      const headers: Record<string, string> = {};
      if (session?.accessToken) {
        headers["Authorization"] = `Bearer ${session.accessToken}`;
      }

      const params = new URLSearchParams({ format: "pdf" });
      if (startDate) params.set("start_date", startDate);
      if (endDate) params.set("end_date", endDate);

      const res = await fetch(`${API_BASE_URL}/api/v1/export/${entity}?${params}`, { headers });
      if (!res.ok) throw new Error(`Export failed: ${res.status}`);

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${entity}_export.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setIsExporting(false);
    }
  }

  return { isExporting, exportDashboardPdf, exportEntityPdf };
}
