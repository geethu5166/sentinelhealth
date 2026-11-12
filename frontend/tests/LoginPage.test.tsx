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
  it("renders brand-forward demo identity picker", () => {
    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );

    expect(screen.getByText("SentinelHealth")).toBeDefined();
    expect(screen.getByText(/Vikram Patel/i)).toBeDefined();
    expect(screen.getByText(/Demonstration prototype/i)).toBeDefined();
  });
});
