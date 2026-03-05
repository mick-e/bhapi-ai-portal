import Image from "next/image";

interface BhapiLogoProps {
  className?: string;
}

export function BhapiLogo({ className = "h-8 w-auto" }: BhapiLogoProps) {
  return (
    <Image
      src="/logo.png"
      alt="Bhapi"
      width={200}
      height={60}
      className={className}
      priority
    />
  );
}
