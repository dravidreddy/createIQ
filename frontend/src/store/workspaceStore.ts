import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { workspaceApi } from '../services/api';

export interface Workspace {
  id: string;
  name: string;
  tier: string;
  role: string;
}

interface WorkspaceState {
  workspaces: Workspace[];
  activeWorkspaceId: string | null;
  isLoading: boolean;
  error: string | null;
  fetchWorkspaces: () => Promise<void>;
  setActiveWorkspace: (id: string) => void;
  inviteMember: (workspaceId: string, email: string, role: string) => Promise<void>;
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set, get) => ({
      workspaces: [],
      activeWorkspaceId: null,
      isLoading: false,
      error: null,

      fetchWorkspaces: async () => {
        set({ isLoading: true, error: null });
        try {
          const workspaces = await workspaceApi.list();
          set({ workspaces, isLoading: false });
          
          // If we have workspaces but no active one is set (or the active one is no longer valid), 
          // default to the first one available
          const { activeWorkspaceId } = get();
          if (workspaces.length > 0) {
            if (!activeWorkspaceId || !workspaces.find((w: Workspace) => w.id === activeWorkspaceId)) {
              set({ activeWorkspaceId: workspaces[0].id });
            }
          } else {
            set({ activeWorkspaceId: null });
          }
        } catch (error: any) {
          set({ error: error.message || 'Failed to fetch workspaces', isLoading: false });
        }
      },

      setActiveWorkspace: (id: string) => {
        set({ activeWorkspaceId: id });
      },

      inviteMember: async (workspaceId: string, email: string, role: string) => {
        set({ isLoading: true, error: null });
        try {
          await workspaceApi.invite(workspaceId, email, role);
          set({ isLoading: false });
        } catch (error: any) {
          set({ error: error.message || 'Failed to invite member', isLoading: false });
          throw error;
        }
      },
    }),
    {
      name: 'workspace-storage',
      // Only persist the activeWorkspaceId so the user stays in the same workspace across reloads
      partialize: (state) => ({ activeWorkspaceId: state.activeWorkspaceId }),
    }
  )
);
