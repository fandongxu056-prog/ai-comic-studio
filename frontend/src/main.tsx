import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Layout } from "./app/layout";
import { HomePage } from "./app/page";
import { LoginPage } from "./app/login/page";
import { RegisterPage } from "./app/register/page";
import { ProjectDashboard } from "./app/project/[id]/page";
import { ScriptWorkspace } from "./app/project/[id]/script/page";
import { AssetWorkspace } from "./app/project/[id]/assets/page";
import { StoryboardWorkspace } from "./app/project/[id]/storyboard/page";
import { ProductionWorkspace } from "./app/project/[id]/production/page";
import "./index.css";

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* App shell with sidebar */}
          <Route element={<Layout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/project/:id" element={<ProjectDashboard />} />
            <Route path="/project/:id/script" element={<ScriptWorkspace />} />
            <Route path="/project/:id/assets" element={<AssetWorkspace />} />
            <Route path="/project/:id/storyboard" element={<StoryboardWorkspace />} />
            <Route path="/project/:id/production" element={<ProductionWorkspace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>
);
