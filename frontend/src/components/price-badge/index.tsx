import { formatPrice } from "@/lib/currency";

type Props = {
  minorUnits: number;
  currency: string;
  locale: string;
  monthly?: boolean;
  className?: string;
};

export function PriceBadge({
  minorUnits,
  currency,
  locale,
  monthly = false,
  className = "",
}: Props) {
  const price = formatPrice(minorUnits, currency, locale);
  return (
    <span className={`font-semibold ${className}`}>
      {price}
      {monthly && <span className="text-text-secondary">/mo</span>}
    </span>
  );
}
