import { BrowserRouter, NavLink, Navigate, Route, Routes, useParams } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Login } from "./pages/Login";
import { OverviewPage } from "./pages/OverviewPage";
import { BoardPage } from "./pages/BoardPage";
import { TodayPage } from "./pages/TodayPage";
import { ProductivityPage } from "./pages/ProductivityPage";
import { DevicesPage } from "./pages/DevicesPage";
import { Sidebar } from "./components/Sidebar";
import "./App.css";

const queryClient = new QueryClient();

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("token");
  return token ? <>{children}</> : <Navigate to="/login" replace />;
}

function ProjectNav() {
  const { slug = "" } = useParams();
  return (
    <nav className="project-nav">
      <NavLink to={`/projects/${slug}`} end className={({ isActive }) => (isActive ? "active" : "")}>
        Board
      </NavLink>
      <NavLink to={`/projects/${slug}/today`} className={({ isActive }) => (isActive ? "active" : "")}>
        Today
      </NavLink>
      <NavLink
        to={`/projects/${slug}/productivity`}
        className={({ isActive }) => (isActive ? "active" : "")}
      >
        Productivity
      </NavLink>
    </nav>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="app-main">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/overview"
            element={
              <RequireAuth>
                <Shell>
                  <OverviewPage />
                </Shell>
              </RequireAuth>
            }
          />
          <Route
            path="/devices"
            element={
              <RequireAuth>
                <Shell>
                  <DevicesPage />
                </Shell>
              </RequireAuth>
            }
          />
          <Route
            path="/projects/:slug"
            element={
              <RequireAuth>
                <Shell>
                  <ProjectNav />
                  <BoardPage />
                </Shell>
              </RequireAuth>
            }
          />
          <Route
            path="/projects/:slug/today"
            element={
              <RequireAuth>
                <Shell>
                  <ProjectNav />
                  <TodayPage />
                </Shell>
              </RequireAuth>
            }
          />
          <Route
            path="/projects/:slug/productivity"
            element={
              <RequireAuth>
                <Shell>
                  <ProjectNav />
                  <ProductivityPage />
                </Shell>
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/overview" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
