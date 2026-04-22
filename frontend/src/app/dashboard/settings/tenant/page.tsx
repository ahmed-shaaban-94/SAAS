"use client";

import { useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { type Locale } from "@/i18n/config";

type TenantCurrency = "USD" | "EGP";

export default function TenantSettingsPage() {
  const t = useTranslations("settings.tenant");
  const locale = useLocale() as Locale;
  const [currency, setCurrency] = useState<TenantCurrency>("USD");
  const [saved, setSaved] = useState(false);

  const save = async () => {
    const resp = await fetch("/api/v1/tenants/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ currency, locale }),
    });
    if (resp.ok) {
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }
  };

  return (
    <section className="mx-auto max-w-2xl space-y-6 p-6">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>

      <div className="space-y-2">
        <label className="text-sm font-medium text-text-secondary">{t("locale_label")}</label>
        <LocaleSwitcher currentLocale={locale} />
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium text-text-secondary">{t("currency_label")}</label>
        <select
          value={currency}
          onChange={(e) => setCurrency(e.target.value as TenantCurrency)}
          className="block rounded-lg border border-border bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
        >
          <option value="USD">USD — US Dollar</option>
          <option value="EGP">EGP — Egyptian Pound</option>
        </select>
      </div>

      <button
        onClick={save}
        className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-accent-strong"
      >
        {saved ? t("saved") : t("save")}
      </button>
    </section>
  );
}
