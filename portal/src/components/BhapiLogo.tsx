interface BhapiLogoProps {
  className?: string;
}

export function BhapiLogo({ className = "h-8 w-auto" }: BhapiLogoProps) {
  return (
    <img
      src="/logo.png"
      alt="Bhapi"
      className={className}
    />
  );
}
