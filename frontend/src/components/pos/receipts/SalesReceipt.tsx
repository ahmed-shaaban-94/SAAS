"use client";

/**
 * SalesReceipt — standard retail variant (issue #634, C1).
 * Adds VIP-discount line, Visa/card payment band, cross-sell suggestion box,
 * and loyalty points banner on top of the shared BaseReceiptBody shell.
 */

import type { ReceiptData } from "./receipt-mock";
import {
  ReceiptPaper,
  BaseReceiptBody,
  GrandTotalBlock,
  PaymentRow,
  CounselingBlock,
  CrossSellList,
  LoyaltyBand,
  QrBlock,
  BarcodeBlock,
  ThanksFooter,
} from "./ReceiptPaper";

interface SalesReceiptProps {
  data: ReceiptData;
  flatEdges?: boolean;
  /**
   * Show torn-paper top/bottom edges. Defaults to true for the retail
   * sales variant. Forced off when `flatEdges` is true (print-preview
   * mode strips all on-screen-only decoration).
   */
  jaggedEdges?: boolean;
  /**
   * Show subtle paper-noise grain. Defaults to true for the retail
   * sales variant. Forced off when `flatEdges` is true.
   */
  paperNoise?: boolean;
}

export function SalesReceipt({
  data,
  flatEdges,
  jaggedEdges = true,
  paperNoise = true,
}: SalesReceiptProps) {
  const { totals, customer, counseling_text, cross_sell } = data;

  return (
    <ReceiptPaper
      flatEdges={flatEdges}
      jaggedEdges={jaggedEdges}
      paperNoise={paperNoise}
    >
      <BaseReceiptBody data={data} />
      <GrandTotalBlock total={totals.grand_total} />
      <PaymentRow method={totals.payment_method} amount={totals.grand_total} />
      {customer.loyalty_points !== undefined && customer.loyalty_balance !== undefined && (
        <LoyaltyBand
          pointsEarned={customer.loyalty_points}
          balance={customer.loyalty_balance}
        />
      )}
      {counseling_text && <CounselingBlock text={counseling_text} />}
      {cross_sell && <CrossSellList items={cross_sell} />}
      <QrBlock invoiceId={data.meta.invoice_number} />
      <BarcodeBlock value={data.meta.invoice_number} />
      <ThanksFooter />
    </ReceiptPaper>
  );
}
