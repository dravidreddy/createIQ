import { useState } from 'react';
import { useWorkspaceStore } from '../../store/workspaceStore';
import { Building, Users, Mail, Shield, Check, Loader2, Star } from 'lucide-react';
import toast from 'react-hot-toast';

export default function WorkspaceSettings() {
  const { workspaces, activeWorkspaceId, inviteMember, isLoading } = useWorkspaceStore();
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('editor');
  const [isInviting, setIsInviting] = useState(false);

  const activeWorkspace = workspaces.find(w => w.id === activeWorkspaceId);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !activeWorkspaceId) return;

    setIsInviting(true);
    try {
      await inviteMember(activeWorkspaceId, email, role);
      toast.success(`Invited ${email} as ${role}`);
      setEmail('');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || error.message || 'Failed to invite member');
    } finally {
      setIsInviting(false);
    }
  };

  if (isLoading && workspaces.length === 0) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    );
  }

  if (!activeWorkspace) {
    return (
      <div className="glass p-8 rounded-2xl text-center">
        <Building className="w-12 h-12 text-text-secondary mx-auto mb-4 opacity-50" />
        <h3 className="text-xl font-display font-bold mb-2">No Workspace Found</h3>
        <p className="text-text-secondary">Please create or join a workspace to manage team settings.</p>
      </div>
    );
  }

  const isFreeTier = activeWorkspace.tier === 'free';

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Workspace Header Info */}
      <div className="glass p-6 rounded-2xl flex items-center justify-between border-l-4 border-l-accent">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-accent/20 flex items-center justify-center">
            <Building className="w-6 h-6 text-accent" />
          </div>
          <div>
            <h2 className="text-xl font-display font-bold">{activeWorkspace.name}</h2>
            <p className="text-sm text-text-secondary capitalize">
              Role: <span className="font-semibold text-text-primary">{activeWorkspace.role}</span>
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/5 border border-white/10">
            <Star className={`w-3.5 h-3.5 ${isFreeTier ? 'text-text-secondary' : 'text-yellow-400'}`} />
            <span className="text-xs font-bold uppercase tracking-widest text-text-primary">
              {activeWorkspace.tier} Plan
            </span>
          </div>
        </div>
      </div>

      {/* Invite Section (Only for owners/admins) */}
      {(activeWorkspace.role === 'owner' || activeWorkspace.role === 'admin') && (
        <div className="glass p-6 rounded-2xl">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-accent" />
            <h3 className="text-lg font-display font-bold">Invite Team Member</h3>
          </div>
          
          <form onSubmit={handleInvite} className="flex gap-3">
            <div className="relative flex-1">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="colleague@agency.com"
                className="w-full pl-10 pr-4 py-2.5 bg-bg border border-white/10 rounded-xl text-sm focus:border-accent focus:ring-1 focus:ring-accent transition-all"
              />
            </div>
            
            <div className="relative w-40">
              <Shield className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary" />
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-bg border border-white/10 rounded-xl text-sm appearance-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
              >
                <option value="editor">Editor</option>
                <option value="viewer">Viewer</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            
            <button
              type="submit"
              disabled={isInviting || !email}
              className="btn-primary py-2.5 px-6 rounded-xl flex items-center gap-2 whitespace-nowrap"
            >
              {isInviting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Check className="w-4 h-4" />
              )}
              Send Invite
            </button>
          </form>
          
          {isFreeTier && (
            <p className="mt-4 text-xs text-text-secondary bg-white/5 p-3 rounded-lg flex items-center gap-2">
              <Star className="w-4 h-4 text-accent" />
              The Free plan allows for 1 member. Upgrade to the Agency Plan to invite your whole team.
            </p>
          )}
        </div>
      )}

      {/* Member List Mockup (If API returned members, we'd map them here) */}
      <div className="glass p-6 rounded-2xl">
        <h3 className="text-lg font-display font-bold mb-4">Current Members</h3>
        <p className="text-sm text-text-secondary italic">
          To view full member management, the backend workspace response must be extended to include the member array. Currently, the API only returns your role.
        </p>
      </div>
    </div>
  );
}
