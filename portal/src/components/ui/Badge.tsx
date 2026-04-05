"use client";
import React from "react";

export type BadgeVariant = "info" | "success" | "warning" | "error" | "neutral";

export interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  info: "bg-blue-50 text-blue-700 ring-blue-600/20",
  success: "bg-green-50 text-green-700 ring-green-600/20",
  warning: "bg-amber-50 text-amber-700 ring-amber-600/20",
  error: "bg-red-50 text-red-700 ring-red-600/20",
  neutral: "bg-gray-50 text-gray-700 ring-gray-600/20",
};

export function Badge({ variant = "neutral", children, className }: BadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${variantStyles[variant]} ${className ?? ""}`}>
      {children}
    </span>
  );
}
