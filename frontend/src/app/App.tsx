import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "../components/layout/AppLayout";
import { ProtectedRoute } from "../auth/ProtectedRoute";
import { LoginPage } from "./LoginPage";
import { NotFoundPage } from "./NotFoundPage";
import { OverviewPage } from "../features/overview/OverviewPage";
import { AlertsPage } from "../features/alerts/AlertsPage";
import { AlertDetailPage } from "../features/alerts/AlertDetailPage";
import { SignalsPage } from "../features/signals/SignalsPage";
import { SourcesPage } from "../features/sources/SourcesPage";
import { MapPage } from "../features/maps/MapPage";
import { TasksPage } from "../features/tasks/TasksPage";
import { ValidationPage } from "../features/validation/ValidationPage";
import { ImpactPage } from "../features/impact/ImpactPage";
import { GovernancePage } from "../features/governance/GovernancePage";
import { SettingsPage } from "../features/settings/SettingsPage";

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Authenticated Dashboard Routes */}
        <Route
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/alerts/:id" element={<AlertDetailPage />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/signals" element={<SignalsPage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/sources" element={<SourcesPage />} />
          <Route path="/validation" element={<ValidationPage />} />
          <Route path="/impact" element={<ImpactPage />} />
          <Route path="/governance" element={<GovernancePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

