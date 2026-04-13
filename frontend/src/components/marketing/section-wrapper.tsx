interface SectionWrapperProps {
  id?: string;
  children: React.ReactNode;
  className?: string;
  variant?: "default" | "alternate" | "gradient";
}

export function SectionWrapper({
  id,
  children,
  className = "",
  variant = "default",
}: SectionWrapperProps) {
  const bgClass =
    variant === "alternate"
      ? "bg-white/4"
      : variant === "gradient"
        ? "bg-gradient-to-b from-transparent via-white/4 to-transparent"
        : "";

  return (
    <section
      id={id}
      className={`relative px-4 py-16 sm:px-6 md:py-24 lg:px-8 ${bgClass} ${className}`}
    >
      <div className="mx-auto max-w-6xl">{children}</div>
    </section>
  );
}
