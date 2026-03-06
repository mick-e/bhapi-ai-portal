interface BhapiLogoProps {
  className?: string;
}

export function BhapiLogo({ className = "h-8 w-auto" }: BhapiLogoProps) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/logo.png"
      alt="Bhapi"
      width={200}
      height={106}
      className={className}
      style={{ maxHeight: "2.5rem", width: "auto" }}
    />
  );
}
