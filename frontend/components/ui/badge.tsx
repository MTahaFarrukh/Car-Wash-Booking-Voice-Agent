import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded px-2 py-0.5 text-[11px] font-semibold tracking-wide uppercase",
  {
    variants: {
      variant: {
        default: "bg-primary/10 text-primary",
        secondary: "bg-secondary text-secondary-foreground",
        outline: "border border-border text-foreground",
        aqua: "bg-aqua/15 text-aqua",
        voice: "bg-teal-500/10 text-teal-300",
        web: "bg-sky-500/10 text-sky-300",
        whatsapp: "bg-emerald-500/10 text-emerald-300",
        pending: "bg-amber-500/10 text-amber-400",
        confirmed: "bg-aqua/15 text-aqua",
        completed: "bg-white/10 text-chrome",
        cancelled: "bg-red-500/10 text-red-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

function Badge({
  className,
  variant,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
