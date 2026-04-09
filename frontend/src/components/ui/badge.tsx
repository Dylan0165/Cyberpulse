import { cn } from "@/lib/utils";

function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  variant?: "default" | "secondary" | "destructive" | "outline" | "critical" | "high" | "medium" | "low" | "info";
}) {
  const variantClasses: Record<string, string> = {
    default: "border-transparent bg-primary text-primary-foreground",
    secondary: "border-transparent bg-secondary text-secondary-foreground",
    destructive: "border-transparent bg-destructive text-destructive-foreground",
    outline: "text-foreground",
    critical: "border-transparent bg-red-600 text-white",
    high: "border-transparent bg-orange-500 text-white",
    medium: "border-transparent bg-yellow-500 text-white",
    low: "border-transparent bg-blue-500 text-white",
    info: "border-transparent bg-gray-400 text-white",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
        variantClasses[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };
