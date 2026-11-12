import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { BrowserRouter } from "react-router-dom";
import { LoginPage } from "../src/app/LoginPage";

vi.mock("../src/auth/AuthProvider", () => ({
  useAuth: () => ({
    loginAsDemoUser: vi.fn(),
    isAuthenticated: false,
    isLoading: false,
  }),
}));

describe("LoginPage", () => {
  it("renders brand-forward operator access picker", () => {
    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );

    expect(screen.getByText("SentinelHealth")).toBeDefined();
    expect(screen.getByText(/Vikram Patel/i)).toBeDefined();
    expect(screen.getByText(/Operator access/i)).toBeDefined();
    expect(screen.getByText(/Screening decision support only/i)).toBeDefined();
  });
});
