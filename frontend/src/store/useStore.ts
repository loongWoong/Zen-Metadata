/**
 * 状态管理 - Zustand
 */
import { create } from 'zustand';
import type { Statistics, Task } from '../types';

interface AppState {
  statistics: Statistics | null;
  loading: boolean;
  error: string | null;
  setStatistics: (stats: Statistics) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  statistics: null,
  loading: false,
  error: null,
  setStatistics: (stats) => set({ statistics: stats }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}));

interface TaskState {
  tasks: Task[];
  currentTask: Task | null;
  setTasks: (tasks: Task[]) => void;
  addTask: (task: Task) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
  setCurrentTask: (task: Task | null) => void;
}

export const useTaskStore = create<TaskState>((set) => ({
  tasks: [],
  currentTask: null,
  setTasks: (tasks) => set({ tasks }),
  addTask: (task) => set((state) => ({ tasks: [task, ...state.tasks] })),
  updateTask: (taskId, updates) =>
    set((state) => ({
      tasks: state.tasks.map((t) => (t.id === taskId ? { ...t, ...updates } : t)),
    })),
  setCurrentTask: (task) => set({ currentTask: task }),
}));







