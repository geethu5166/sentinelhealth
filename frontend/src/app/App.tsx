import React, { Suspense, lazy } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "../components/layout/AppLayout";
import { ProtectedRoute } from "../auth/ProtectedRoute";
import { LoginPage } from "./LoginPage";
import { NotFoundPage } from "./NotFoundPage";
import { Skeleton } from "../components/ui/skeleton";

const OverviewPage = lazy(() =>
  import("../features/overview/OverviewPage").then((m) => ({ default: m.OverviewPage }))
);
const AlertsPage = lazy(() =>
  import("../features/alerts/AlertsPage").then((m) => ({ default: m.AlertsPage }))
);
const AlertDetailPage = lazy(() =>
  import("../features/alerts/AlertDetailPage").then((m) => ({ default: m.AlertDetailPage }))
);
const SignalsPage = lazy(() =>
  import("../features/signals/SignalsPage").then((m) => ({ default: m.SignalsPage }))
);
const SourcesPage = lazy(() =>
  import("../features/sources/SourcesPage").then((m) => ({ default: m.SourcesPage }))
);
const MapPage = lazy(() =>
  import("../features/maps/MapPage").then((m) => ({ default: m.MapPage }))
);
const TasksPage = lazy(() =>
  import("../features/tasks/TasksPage").then((m) => ({ default: m.TasksPage }))
);
const ValidationPage = lazy(() =>
  import("../features/validation/ValidationPage").then((m) => ({ default: m.ValidationPage }))
);
const ImpactPage = lazy(() =>
  import("../features/impact/ImpactPage").then((m) => ({ default: m.ImpactPage }))
);
const GovernancePage = lazy(() =>
  import("../features/governance/GovernancePage").then((m) => ({ default: m.GovernancePage }))
);
const SettingsPage = lazy(() =>
  import("../features/settings/SettingsPage").then((m) => ({ default: m.SettingsPage }))
);

const RouteFallback = () => (
  <div className="mx-auto max-w-7xl space-y-4 p-2">
    <Skeleton className="h-10 w-64" />
    <Skeleton className="h-40 w-full" />
  </div>
);

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route
            path="/"
            element={
              <Suspense fallback={<RouteFallback />}>
                <Navigate to="/overview" replace />
              </Suspense>
            }
          />
          <Route
            path="/overview"
            element={
              <Suspense fallback={<RouteFallback />}>
                <OverviewPage />
              </Suspense>
            }
          />
          <Route
            path="/alerts"
            element={
              <Suspense fallback={<RouteFallback />}>
                <AlertsPage />
              </Suspense>
            }
          />
          <Route
            path="/alerts/:id"
            element={
              <Suspense fallback={<RouteFallback />}>
                <AlertDetailPage />
              </Suspense>
            }
          />
          <Route
            path="/map"
            element={
              <Suspense fallback={<RouteFallback />}>
                <MapPage />
              </Suspense>
            }
          />
          <Route
            path="/signals"
            element={
              <Suspense fallback={<RouteFallback />}>
                <SignalsPage />
              </Suspense>
            }
          />
          <Route
            path="/tasks"
            element={
              <Suspense fallback={<RouteFallback />}>
                <TasksPage />
              </Suspense>
            }
          />
          <Route
            path="/sources"
            element={
              <Suspense fallback={<RouteFallback />}>
                <SourcesPage />
              </Suspense>
            }
          />
          <Route
            path="/validation"
            element={
              <Suspense fallback={<RouteFallback />}>
                <ValidationPage />
              </Suspense>
            }
          />
          <Route
            path="/impact"
            element={
              <Suspense fallback={<RouteFallback />}>
                <ImpactPage />
              </Suspense>
            }
          />
          <Route
            path="/governance"
            element={
              <Suspense fallback={<RouteFallback />}>
                <GovernancePage />
              </Suspense>
            }
          />
          <Route
            path="/settings"
            element={
              <Suspense fallback={<RouteFallback />}>
                <SettingsPage />
              </Suspense>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
};
