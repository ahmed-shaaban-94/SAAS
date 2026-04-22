"use client";

import { QRCodeSVG } from "qrcode.react";

const QR_BASE = "https://datapulse.health/r/";

interface QrBlockProps {
  invoiceId: string;
}

export function QrBlock({ invoiceId }: QrBlockProps) {
  const payload = `${QR_BASE}${invoiceId}`;

  return (
    <div className="mb-3 flex flex-col items-center gap-1">
      <QRCodeSVG
        value={payload}
        size={80}
        marginSize={2}
        fgColor="var(--pos-paper-ink, #1a1a1a)"
        bgColor="transparent"
        aria-label={`QR code for invoice ${invoiceId}`}
      />
      <div
        style={{
          fontFamily: "var(--font-plex-arabic, sans-serif)",
          fontSize: 9,
          color: "var(--pos-paper-ink-faint)",
          textAlign: "center",
        }}
      >
        امسح للحصول على الإيصال الرقمي
      </div>
    </div>
  );
}
