interface HeaderProps {
  title: string;
  description?: string;
}

export function Header({ title, description }: HeaderProps) {
  return (
    <div className="mb-4 sm:mb-6">
      <h1 className="text-xl font-bold text-text-primary sm:text-2xl">{title}</h1>
      {description && (
        <p className="mt-0.5 text-xs text-text-secondary sm:mt-1 sm:text-sm">{description}</p>
      )}
    </div>
  );
}
