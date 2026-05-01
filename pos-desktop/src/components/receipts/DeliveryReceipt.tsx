/**
 * DeliveryReceipt — home-delivery variant (issue #634, C1).
 * Replaces the pharmacist counseling eyebrow with "ملاحظة للمندوب" (Note to rider),
 * adds the inverted-ink DeliveryBlock (address / landmark / rider name / ETA),
 * a two-column SignatureBlock, and labels the grand total as "الإجمالي — توصيل".
 */

import type { ReceiptData } from "./receipt-mock";
import {
  ReceiptPaper,
  BaseReceiptBody,
  DeliveryBlock,
  SignatureBlock,
  GrandTotalBlock,
  PaymentRow,
  CounselingBlock,
  QrBlock,
  BarcodeBlock,
  ThanksFooter,
} from "./ReceiptPaper";

interface DeliveryReceiptProps {
  data: ReceiptData;
  flatEdges?: boolean;
}

export function DeliveryReceipt({ data, flatEdges }: DeliveryReceiptProps) {
  const { totals, delivery, counseling_text } = data;

  return (
    <ReceiptPaper flatEdges={flatEdges}>
      <BaseReceiptBody data={data} />
      {delivery && <DeliveryBlock info={delivery} />}
      <GrandTotalBlock total={totals.grand_total} label="الإجمالي — توصيل" />
      <PaymentRow method={totals.payment_method} amount={totals.grand_total} />
      {counseling_text && (
        <CounselingBlock text={counseling_text} eyebrow="ملاحظة للمندوب" />
      )}
      <SignatureBlock />
      <QrBlock invoiceId={data.meta.invoice_number} />
      <BarcodeBlock value={data.meta.invoice_number} />
      <ThanksFooter />
    </ReceiptPaper>
  );
}
