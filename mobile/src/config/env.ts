const rawApiUrl = process.env.EXPO_PUBLIC_API_URL?.trim() ?? "";

export const env = {
  apiUrl: rawApiUrl.replace(/\/$/, ""),
  apiKey: process.env.EXPO_PUBLIC_API_KEY?.trim() ?? "",
  appName: "DataPulse Mobile",
};

export function buildApiUrl(path: string): string {
  if (!env.apiUrl) {
    throw new Error(
      "EXPO_PUBLIC_API_URL is not set. Add it in mobile/.env.local or your shell before starting Expo.",
    );
  }

  return `${env.apiUrl}${path}`;
}
