"use client";

/**
 * InsuranceReceipt — insurance co-pay variant (issue #634, C1).
 * Inserts InsurancePanel (2px-border insurer/patient split box + approval row)
 * between totals and the grand total block. The grand total shows only the
 * patient co-pay amount with a matching label.
 */

import type { ReceiptData } from "./receipt-mock";
import {
  ReceiptPaper,
  BaseReceiptBody,
  InsurancePanel,
  GrandTotalBlock,
  PaymentRow,
  CounselingBlock,
  QrBlock,
  BarcodeBlock,
  ThanksFooter,
} from "./ReceiptPaper";

interface InsuranceReceiptProps {
  data: ReceiptData;
  flatEdges?: boolean;
}

export function InsuranceReceipt({ data, flatEdges }: InsuranceReceiptProps) {
  const { totals, insurance, counseling_text } = data;

  return (
    <ReceiptPaper flatEdges={flatEdges}>
      <BaseReceiptBody data={data} />
      {insurance && <InsurancePanel info={insurance} />}
      <GrandTotalBlock
        total={insurance ? insurance.patient_amount : totals.grand_total}
        label="مستحق على المريض"
      />
      <PaymentRow method={totals.payment_method} amount={insurance ? insurance.patient_amount : totals.grand_total} />
      {counseling_text && <CounselingBlock text={counseling_text} />}
      <QrBlock invoiceId={data.meta.invoice_number} />
      <BarcodeBlock value={data.meta.invoice_number} />
      <ThanksFooter />
    </ReceiptPaper>
  );
}
