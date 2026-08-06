// Sheet 06: same query the 9:30 AM email uses, rendered as a page. Minutes sum
// honestly across projects; efficiency is shown per-project, never blended.
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

type Overview = {
  total_minutes: number;
  projects: { project: string; minutes_worked?: number; efficiency_score?: number }[];
};

export function OverviewPage() {
  const [newProject, setNewProject] = useState("");
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<Overview>({
    queryKey: ["overview"],
    queryFn: () => api.getOverview("today") as Promise<Overview>,
  });

  const createProject = useMutation({
    mutationFn: (name: string) => api.createProject(name),
    onSuccess: (project) => {
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
    <div className="overview-page">
      <h1>Everything, today</h1>
      {!isLoading && data && <p className="stat-value">{data.total_minutes} minutes across every project</p>}

      <ul className="project-list">
        {data?.projects.map((p) => (
          <li key={p.project}>
            <Link to={`/projects/${p.project}`}>{p.project}</Link>
            {p.minutes_worked !== undefined && (
              <span className="chip">
                {p.minutes_worked}m &middot; eff {p.efficiency_score}
              </span>
            )}
          </li>
        ))}
      </ul>

      <form className="new-project-form" onSubmit={onCreate}>
        <input
          placeholder="New project name&hellip;"
          value={newProject}
          onChange={(e) => setNewProject(e.target.value)}
        />
        <button type="submit">Create</button>
      </form>
    </div>
  );
}
