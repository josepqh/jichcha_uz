import { useEffect } from "react";
import { Navigate, Route, Routes, useParams } from "react-router";

import { Layout } from "@/components/Layout";
import { DEFAULT_LANGUAGE, isLanguage, type Language } from "@/i18n";
import { refreshSession } from "@/lib/api";
import { AccountPage } from "@/pages/AccountPage";
import { AdminPage } from "@/pages/AdminPage";
import { FaqPage } from "@/pages/FaqPage";
import { ForgotPage } from "@/pages/ForgotPage";
import { HomePage } from "@/pages/HomePage";
import { LegalPage } from "@/pages/LegalPage";
import { LoginPage } from "@/pages/LoginPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { ResetPage } from "@/pages/ResetPage";
import { VerifyEmailPage } from "@/pages/VerifyEmailPage";
import { ToolPage } from "@/pages/ToolPage";

function LangGuard({ children }: { children: React.ReactNode }) {
  const { lang } = useParams();
  return isLanguage(lang) ? children : <NotFoundPage />;
}

function preferredLanguage(): Language {
  for (const tag of navigator.languages ?? []) {
    const code = tag.slice(0, 2).toLowerCase();
    if (isLanguage(code)) return code;
  }
  return DEFAULT_LANGUAGE;
}

export function App() {
  // Restore the session from the httpOnly refresh cookie once per page load.
  useEffect(() => {
    void refreshSession();
  }, []);

  return (
    <Routes>
      <Route index element={<Navigate to={`/${preferredLanguage()}`} replace />} />
      <Route path=":lang" element={<Layout />}>
        <Route index element={<LangGuard><HomePage /></LangGuard>} />
        <Route path="tools/:slug" element={<LangGuard><ToolPage /></LangGuard>} />
        <Route path="convert/:pair" element={<LangGuard><ToolPage /></LangGuard>} />
        <Route path="login" element={<LangGuard><LoginPage /></LangGuard>} />
        <Route path="register" element={<LangGuard><RegisterPage /></LangGuard>} />
        <Route path="forgot" element={<LangGuard><ForgotPage /></LangGuard>} />
        <Route path="reset/:uid/:token" element={<LangGuard><ResetPage /></LangGuard>} />
        <Route path="verify-email/:token" element={<LangGuard><VerifyEmailPage /></LangGuard>} />
        <Route path="account" element={<LangGuard><AccountPage /></LangGuard>} />
        <Route path="admin" element={<LangGuard><AdminPage /></LangGuard>} />
        <Route path="admin/:tab" element={<LangGuard><AdminPage /></LangGuard>} />
        <Route path="privacy" element={<LangGuard><LegalPage key="privacy" doc="privacy" /></LangGuard>} />
        <Route path="terms" element={<LangGuard><LegalPage key="terms" doc="terms" /></LangGuard>} />
        <Route path="faq" element={<LangGuard><FaqPage /></LangGuard>} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
