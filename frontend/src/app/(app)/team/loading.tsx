export default function TeamLoading() {
  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <div className="h-8 w-48 animate-pulse rounded-lg bg-card" />
      <div className="animate-pulse space-y-4">
        <div className="h-48 rounded-xl bg-card" />
        <div className="h-64 rounded-xl bg-card" />
      </div>
    </div>
  );
}
