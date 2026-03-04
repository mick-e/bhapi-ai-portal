interface BhapiLogoProps {
  className?: string;
  variant?: "full" | "icon";
  color?: string;
}

export function BhapiLogo({
  className = "h-8 w-auto",
  variant = "full",
  color = "currentColor",
}: BhapiLogoProps) {
  if (variant === "icon") {
    // Smile arc only — for favicon-sized contexts
    return (
      <svg
        viewBox="0 0 32 32"
        fill="none"
        className={className}
        role="img"
        aria-label="Bhapi"
      >
        <path
          d="M6 14c2 6 6.5 10 10 10s8-4 10-10"
          stroke={color}
          strokeWidth="3.5"
          strokeLinecap="round"
          fill="none"
        />
      </svg>
    );
  }

  // Full wordmark: "bhapi" text with smile arc above "hap"
  return (
    <svg
      viewBox="0 0 120 40"
      fill="none"
      className={className}
      role="img"
      aria-label="Bhapi"
    >
      {/* Smile arc above "hap" */}
      <path
        d="M30 8c3 8 10 13 17 13s14-5 17-13"
        stroke={color}
        strokeWidth="3"
        strokeLinecap="round"
        fill="none"
      />
      {/* "bhapi" wordmark */}
      <text
        x="6"
        y="36"
        fill={color}
        fontFamily="Inter, system-ui, sans-serif"
        fontWeight="700"
        fontSize="28"
        letterSpacing="-0.5"
      >
        bhapi
      </text>
    </svg>
  );
}
