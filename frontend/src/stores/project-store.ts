import { create } from "zustand";

export type StageStatus =
  | "not_started"
  | "in_progress"
  | "review"
  | "locked"
  | "revision"
  | "partial_complete"
  | "complete"
  | "failed";

export interface ProjectStage {
  status: StageStatus;
  id?: string;
  version?: number;
  lastUpdated?: string;
  // Stage-specific counts
  episodeCount?: number;
  characterCount?: number;
  totalShots?: number;
  shotsCompleted?: number;
  totalCostUsd?: number;
}

export interface Project {
  id: string;
  title: string;
  currentStage: "script" | "assets" | "storyboard" | "production" | "complete";
  stages: {
    script: ProjectStage;
    assets: ProjectStage;
    storyboard: ProjectStage;
    production: ProjectStage;
  };
  createdAt: string;
  updatedAt: string;
}

interface ProjectStore {
  projects: Project[];
  currentProject: Project | null;
  isLoading: boolean;
  error: string | null;
  setProjects: (projects: Project[]) => void;
  setCurrentProject: (project: Project | null) => void;
  updateStage: (stageKey: keyof Project["stages"], data: Partial<ProjectStage>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useProjectStore = create<ProjectStore>((set) => ({
  projects: [],
  currentProject: null,
  isLoading: false,
  error: null,

  setProjects: (projects) => set({ projects }),
  setCurrentProject: (project) => set({ currentProject: project }),
  updateStage: (stageKey, data) =>
    set((state) => {
      if (!state.currentProject) return state;
      return {
        currentProject: {
          ...state.currentProject,
          stages: {
            ...state.currentProject.stages,
            [stageKey]: {
              ...state.currentProject.stages[stageKey],
              ...data,
            },
          },
        },
      };
    }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
}));
