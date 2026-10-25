import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-busy="true"
      aria-label="Loading..."
      className={cn("animate-pulse rounded-md bg-[#E2E0D8]/60", className)}
      {...props}
    />
  );
}

export { Skeleton };
