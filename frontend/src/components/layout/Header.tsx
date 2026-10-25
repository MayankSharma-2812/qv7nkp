import { useLocation } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Menu, Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";

interface HeaderProps {
  onMobileMenuToggle: () => void;
}

export function Header({ onMobileMenuToggle }: HeaderProps) {
  const location = useLocation();

  let title = "Decision Cockpit";
  let subtitle = "Day-ahead wind forecasts vs actual outturn generation";

  if (location.pathname === "/accuracy") {
    title = "Accuracy Studio";
    subtitle = "Quantitative error metrics, diurnal curves, and horizon degradation";
  } else if (location.pathname === "/methodology") {
    title = "Methodology & Architecture";
    subtitle = "Formulas, temporal cutoff rules, resolution alignment, and Elexon data specs";
  }

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-[#E2E0D8] bg-white/95 px-6 backdrop-blur-md">
      <div className="flex items-center gap-3">
        <Button
          variant="outline"
          size="icon"
          onClick={onMobileMenuToggle}
          className="lg:hidden h-9 w-9 text-[#141F1B]"
          aria-label="Toggle navigation menu"
        >
          <Menu className="h-5 w-5" />
        </Button>

        <div>
          <h2 className="text-lg font-bold tracking-tight text-[#141F1B]">{title}</h2>
          <p className="text-xs text-[#5A6B64] hidden sm:block">{subtitle}</p>
        </div>
      </div>

      <div className="flex items-center gap-2.5">
        <Badge variant="secondary" className="gap-1 px-2.5 py-1 text-xs font-medium">
          <Calendar className="h-3 w-3 text-[#174D3E]" />
          <span>Jan 2026 Decisions</span>
        </Badge>
        <Badge variant="accent" className="hidden sm:inline-flex text-xs">
          UK National Grid
        </Badge>
      </div>
    </header>
  );
}
