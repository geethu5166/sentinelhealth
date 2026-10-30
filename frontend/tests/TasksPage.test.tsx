import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { TasksPage } from "../src/features/tasks/TasksPage";

describe("TasksPage", () => {
  it("renders preventive tasks page header and filter controls", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <TasksPage />
        </BrowserRouter>
      </QueryClientProvider>
    );

    expect(screen.getByText(/Preventive Action & Mitigation Tasks/i)).toBeDefined();
    expect(screen.getByText(/Track assigned playbook tasks/i)).toBeDefined();
  });
});

