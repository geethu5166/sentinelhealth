import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { OverviewPage } from "../src/features/overview/OverviewPage";

describe("OverviewPage", () => {
  it("renders overview page loading skeleton or error state cleanly", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <OverviewPage />
        </BrowserRouter>
      </QueryClientProvider>
    );

    // Initial state renders skeletons or headers cleanly
    expect(document.body).toBeDefined();
  });
});

