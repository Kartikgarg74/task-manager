import { useState, type FormEvent } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

export function Sidebar() {
  const [newProject, setNewProject] = useState("");
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.listProjects(),
  });

  const createProject = useMutation({
    mutationFn: (name: string) => api.createProject(name),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      navigate(`/projects/${(project as { slug: string }).slug}`);
    },
  });

  function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!newProject.trim()) return;
    createProject.mutate(newProject.trim());
    setNewProject("");
  }

  return (
    <aside className="sidebar">
      <NavLink to="/overview" className="sidebar-brand">
        Task Manager
      </NavLink>

      <nav className="sidebar-nav">
        <NavLink to="/overview" className={({ isActive }) => (isActive ? "active" : "")}>
          <span aria-hidden="true">&#8962;</span> Overview
        </NavLink>
      </nav>

      <div className="sidebar-section-label">Projects</div>
      <nav className="sidebar-projects">
        {projects?.map((p) => (
          <NavLink key={p.slug} to={`/projects/${p.slug}`} className={({ isActive }) => (isActive ? "active" : "")}>
            {p.name}
          </NavLink>
        ))}
        {projects?.length === 0 && <p className="empty">No projects yet.</p>}
      </nav>

      <form className="sidebar-new-project" onSubmit={onCreate}>
        <input
          placeholder="New project&hellip;"
          value={newProject}
          onChange={(e) => setNewProject(e.target.value)}
        />
        <button type="submit" aria-label="Create project">
          +
        </button>
      </form>

      <div className="sidebar-footer">
        <NavLink to="/devices" className={({ isActive }) => (isActive ? "active" : "")}>
          Devices
        </NavLink>
      </div>
    </aside>
  );
}
