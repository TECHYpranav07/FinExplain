import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { LandingPage } from "@/pages/LandingPage";
import { AppShell } from "@/components/finex/AppShell";
import { DashboardPage } from "@/pages/DashboardPage";
import { DocumentsPage } from "@/pages/DocumentsPage";
import { DocumentAnalysisPage } from "@/pages/DocumentAnalysisPage";
import { QueryPage } from "@/pages/QueryPage";
import { ReviewPage } from "@/pages/ReviewPage";
import { BeforeConfirmationPage } from "@/pages/BeforeConfirmationPage";
import { ProductsPage } from "@/pages/ProductsPage";
import { ProductDetailPage } from "@/pages/ProductDetailPage";
import { ComparePage } from "@/pages/ComparePage";
import { HITLPage } from "@/pages/HITLPage";
import { FeedbackPage } from "@/pages/FeedbackPage";
import { SettingsPage } from "@/pages/SettingsPage";

export function App() {
  return (
    <Routes>
      {/* Public Landing Page */}
      <Route path="/" element={<LandingPage />} />

      {/* Authenticated Application Shell */}
      <Route path="/app" element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="documents/:id" element={<DocumentAnalysisPage />} />
        <Route path="query" element={<QueryPage />} />
        <Route path="review" element={<ReviewPage />} />
        <Route path="before-confirmation" element={<BeforeConfirmationPage />} />
        <Route path="products" element={<ProductsPage />} />
        <Route path="products/:id" element={<ProductDetailPage />} />
        <Route path="compare" element={<ComparePage />} />
        <Route path="hitl" element={<HITLPage />} />
        <Route path="feedback" element={<FeedbackPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      {/* Fallback to landing */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
