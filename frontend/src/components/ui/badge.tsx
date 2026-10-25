import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "bg-[#174D3E] text-white",
        secondary: "bg-[#F0EFEA] text-[#141F1B] border border-[#E2E0D8]",
        accent: "bg-[#DCE8DF] text-[#174D3E] border border-[#c5d8ca]",
        outline: "border border-[#E2E0D8] text-[#5A6B64]",
        warning: "bg-amber-100 text-amber-900 border border-amber-200",
        destructive: "bg-red-50 text-red-800 border border-red-200",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
