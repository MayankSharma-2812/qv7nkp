import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";

function renderWithProviders(ui: React.ReactElement, initialEntry = "/") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        {ui}
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Layout and Navigation Components", () => {
  it("renders sidebar with brand title and primary navigation links", () => {
    renderWithProviders(<Sidebar />);

    expect(screen.getByText("WindScope")).toBeInTheDocument();
    expect(screen.getByText("Decision Cockpit")).toBeInTheDocument();
    expect(screen.getByText("Accuracy Studio")).toBeInTheDocument();
    expect(screen.getByText("Methodology")).toBeInTheDocument();
  });

  it("renders header with title and status badges for default route", () => {
    renderWithProviders(<Header onMobileMenuToggle={() => {}} />, "/");

    expect(screen.getByText("Decision Cockpit")).toBeInTheDocument();
    expect(screen.getByText("Jan 2026 Decisions")).toBeInTheDocument();
    expect(screen.getByText("UK National Grid")).toBeInTheDocument();
  });

  it("renders accuracy studio title when on /accuracy route", () => {
    renderWithProviders(<Header onMobileMenuToggle={() => {}} />, "/accuracy");

    expect(screen.getByText("Accuracy Studio")).toBeInTheDocument();
  });
});
