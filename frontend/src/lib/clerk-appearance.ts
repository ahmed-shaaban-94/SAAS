/**
 * Clerk `<SignIn>` / `<SignUp>` appearance keyed to DataPulse theme tokens.
 *
 * Mirrors the dashboard's visual language (accent cyan, card radius,
 * border color) so the auth flow doesn't look like a stock Clerk widget.
 * Theme-aware via `next-themes` — the hook resolves `dark` or `light`
 * and picks the matching variable set below.
 */

// Clerk's `Appearance` type isn't re-exported from `@clerk/nextjs`; the
// canonical location is `@clerk/types`, but taking the parameter shape
// directly off `<SignIn>` keeps us free of an extra dep.
import type { ComponentProps } from "react";
import type { SignIn } from "@clerk/nextjs";

type Appearance = NonNullable<ComponentProps<typeof SignIn>["appearance"]>;

// Hex values mirror globals.css. Kept in sync manually; when the design
// system rotates colors, both places change together.
const TOKENS = {
  light: {
    page: "#f3f7fb",
    card: "#ffffff",
    textPrimary: "#102a43",
    textSecondary: "#627d98",
    accent: "#00c7f2",
    border: "#d7e2ec",
    danger: "#f46d75",
  },
  dark: {
    page: "#0b1e34",
    card: "#102a43",
    textPrimary: "#f7fbff",
    textSecondary: "#b8c0cc",
    accent: "#00c7f2",
    border: "#33506b",
    danger: "#ff7b7b",
  },
} as const;

export function getClerkAppearance(theme: "light" | "dark"): Appearance {
  const t = TOKENS[theme];
  return {
    variables: {
      colorPrimary: t.accent,
      colorBackground: t.card,
      colorText: t.textPrimary,
      colorTextSecondary: t.textSecondary,
      colorInputBackground: theme === "dark" ? "#1b3655" : "#f3f7fb",
      colorInputText: t.textPrimary,
      colorDanger: t.danger,
      colorNeutral: t.textSecondary,
      borderRadius: "0.75rem", // Tailwind `rounded-xl`
      fontFamily: "inherit",
      fontSize: "14px",
    },
    elements: {
      rootBox: "w-full",
      card: {
        backgroundColor: t.card,
        borderColor: t.border,
        borderWidth: "1px",
        boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.2)",
      },
      headerTitle: {
        color: t.textPrimary,
        fontWeight: 600,
      },
      headerSubtitle: {
        color: t.textSecondary,
      },
      socialButtonsBlockButton: {
        borderColor: t.border,
        color: t.textPrimary,
        "&:hover": {
          backgroundColor: theme === "dark" ? "#1b3655" : "#eef3f8",
        },
      },
      formButtonPrimary: {
        backgroundColor: t.accent,
        color: theme === "dark" ? "#0b1e34" : "#ffffff",
        fontWeight: 500,
        "&:hover": {
          backgroundColor: theme === "dark" ? "#5cdfff" : "#0b7da1",
        },
      },
      formFieldLabel: {
        color: t.textSecondary,
        fontSize: "13px",
      },
      formFieldInput: {
        borderColor: t.border,
        backgroundColor: theme === "dark" ? "#1b3655" : "#f3f7fb",
        color: t.textPrimary,
      },
      footerActionText: {
        color: t.textSecondary,
      },
      footerActionLink: {
        color: t.accent,
        "&:hover": {
          color: theme === "dark" ? "#5cdfff" : "#0b7da1",
        },
      },
      dividerLine: {
        backgroundColor: t.border,
      },
      dividerText: {
        color: t.textSecondary,
      },
      identityPreviewText: {
        color: t.textPrimary,
      },
      identityPreviewEditButton: {
        color: t.accent,
      },
    },
  };
}
