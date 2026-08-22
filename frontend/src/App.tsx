import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { GoogleOAuthProvider } from "@react-oauth/google";
import { AuthProvider } from "@/lib/authContext";
import { ProtectedRoute } from "@/components/finex/ProtectedRoute";
import { LandingPage } from "@/pages/LandingPage";
import { AuthPage } from "@/pages/AuthPage";
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

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "333830843232-example.apps.googleusercontent.com";

export function App() {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthProvider>
        <Routes>
        {/* Public Landing & Authentication */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/auth" element={<AuthPage />} />
        <Route path="/login" element={<Navigate to="/auth" replace />} />
        <Route path="/signup" element={<Navigate to="/auth" replace />} />

        {/* Protected Authenticated Application Shell */}
        <Route element={<ProtectedRoute />}>
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
        </Route>

        {/* Fallback to landing */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
    </GoogleOAuthProvider>
  );
}
