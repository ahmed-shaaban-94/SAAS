import Link from "next/link";
import { FileQuestion } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center">
      <FileQuestion className="h-16 w-16 text-text-secondary" />
      <h1 className="mt-6 text-2xl font-bold">Page Not Found</h1>
      <p className="mt-2 text-text-secondary">
        The page you are looking for does not exist.
      </p>
      <Link
        href="/dashboard"
        className="mt-6 rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-page hover:bg-accent/90 transition-colors"
      >
        Back to Dashboard
      </Link>
    </div>
  );
}
