import { useEffect, useState, useRef } from 'react';
import { useWorkspaceStore } from '../../store/workspaceStore';
import { Building, ChevronDown, Check, Loader2 } from 'lucide-react';
import clsx from 'clsx';

export default function WorkspaceSelector() {
  const { workspaces, activeWorkspaceId, fetchWorkspaces, setActiveWorkspace, isLoading } = useWorkspaceStore();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchWorkspaces();
  }, [fetchWorkspaces]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const activeWorkspace = workspaces.find((w) => w.id === activeWorkspaceId) || workspaces[0];

  if (isLoading && workspaces.length === 0) {
    return (
      <div className="flex items-center px-3 py-1.5 rounded-lg border border-white/5 bg-white/5">
        <Loader2 className="w-3.5 h-3.5 animate-spin text-text-secondary" />
      </div>
    );
  }

  if (workspaces.length === 0) {
    return null; // Don't render if no workspaces (should fallback to personal in backend)
  }

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/5 bg-white/5 hover:bg-white/5 transition-colors"
      >
        <Building className="w-3.5 h-3.5 text-accent" />
        <span className="text-xs font-semibold text-text-primary max-w-[120px] truncate">
          {activeWorkspace?.name || 'Workspace'}
        </span>
        <ChevronDown className="w-3 h-3 text-text-secondary" />
      </button>

      {isOpen && (
        <div className="absolute top-full right-0 mt-2 w-56 py-2 bg-elevated border border-white/10 rounded-xl shadow-2xl z-50 animate-in slide-up fade-in duration-200">
          <div className="px-3 py-1.5 mb-1 border-b border-white/5">
            <p className="text-[10px] font-bold uppercase tracking-widest text-text-secondary">
              Switch Workspace
            </p>
          </div>
          
          <div className="max-h-64 overflow-y-auto">
            {workspaces.map((workspace) => {
              const isActive = workspace.id === activeWorkspaceId;
              return (
                <button
                  key={workspace.id}
                  onClick={() => {
                    setActiveWorkspace(workspace.id);
                    setIsOpen(false);
                    // Force reload to refresh context (projects list, etc)
                    window.location.reload();
                  }}
                  className={clsx(
                    "w-full flex items-center justify-between px-4 py-2.5 text-sm hover:bg-white/5 transition-colors text-left",
                    isActive ? "text-accent bg-accent/5" : "text-text-primary"
                  )}
                >
                  <div className="flex flex-col">
                    <span className="font-medium truncate">{workspace.name}</span>
                    <span className="text-[10px] text-text-secondary uppercase tracking-widest mt-0.5">
                      {workspace.tier} • {workspace.role}
                    </span>
                  </div>
                  {isActive && <Check className="w-4 h-4 text-accent flex-shrink-0" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
