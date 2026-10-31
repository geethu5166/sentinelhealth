import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { MapPage } from "../src/features/maps/MapPage";

describe("MapPage", () => {
  it("renders map page with metric and window controls and no leaked suppression counts", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <MapPage />
        </BrowserRouter>
      </QueryClientProvider>
    );

    // Verify header and controls
    expect(screen.getByText(/Aggregate Spatial Surveillance/i)).toBeDefined();
    expect(screen.getByText(/Metric:/i)).toBeDefined();
    expect(screen.getByText(/Window:/i)).toBeDefined();

    // Verify disclosure rule: no protected exact count like "n=6" appears in DOM
    const htmlContent = document.body.innerHTML;
    expect(htmlContent).not.toMatch(/\bn\s*=\s*[1-9]\b/i);
    expect(htmlContent).not.toMatch(/contributor count\s*[:=]\s*[1-9]/i);
  });
});

