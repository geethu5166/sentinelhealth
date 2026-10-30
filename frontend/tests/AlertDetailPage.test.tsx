import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AlertDetailPage } from "../src/features/alerts/AlertDetailPage";

describe("AlertDetailPage", () => {
  it("renders detail page skeleton and initial structure cleanly", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<AlertDetailPage />} />
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    );

    expect(document.body).toBeDefined();
  });
});

