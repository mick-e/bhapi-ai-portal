interface CardProps {
  title?: string;
  description?: string;
  footer?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}

export function Card({
  title,
  description,
  footer,
  className = "",
  children,
}: CardProps) {
  return (
    <div
      className={`rounded-xl bg-white shadow-sm ring-1 ring-gray-200 ${className}`}
    >
      {(title || description) && (
        <div className="border-b border-gray-100 px-6 py-4">
          {title && (
            <h3 className="text-base font-semibold text-gray-900">{title}</h3>
          )}
          {description && (
            <p className="mt-1 text-sm text-gray-500">{description}</p>
          )}
        </div>
      )}
      <div className="px-6 py-4">{children}</div>
      {footer && (
        <div className="border-t border-gray-100 px-6 py-4 bg-gray-50 rounded-b-xl">
          {footer}
        </div>
      )}
    </div>
  );
}
