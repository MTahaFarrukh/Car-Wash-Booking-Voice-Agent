import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        outline: "border-border text-foreground",
        aqua: "border-aqua/30 bg-aqua/15 text-primary",
        voice: "border-teal-200 bg-teal-50 text-teal-900",
        web: "border-sky-200 bg-sky-50 text-sky-900",
        whatsapp: "border-emerald-200 bg-emerald-50 text-emerald-900",
        pending: "border-amber-200 bg-amber-50 text-amber-900",
        confirmed: "border-aqua/40 bg-aqua/10 text-primary",
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
