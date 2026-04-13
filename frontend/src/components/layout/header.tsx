interface HeaderProps {
  title: string;
  description?: string;
}

export function Header({ title, description }: HeaderProps) {
  return (
    <div className="mb-4 sm:mb-6">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.26em] text-text-secondary">
        Data Pulse
      </p>
      <h1 className="text-2xl font-bold tracking-tight text-text-primary sm:text-[2rem]">{title}</h1>
      {description && (
        <p className="mt-1 text-sm text-text-secondary sm:text-base">{description}</p>
      )}
    </div>
  );
}
