import React, { useState, useEffect } from 'react';
import {
  History,
  Clock,
  RotateCcw,
  GitCompare,
  ChevronRight,
  X,
  Check,
  FileText,
  Loader2,
} from 'lucide-react';
import { historyApi } from '../../services/api';
import toast from 'react-hot-toast';

interface VersionHistoryProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
}

export const VersionHistory: React.FC<VersionHistoryProps> = ({
  projectId,
  isOpen,
  onClose,
}) => {
  const [blocks, setBlocks] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<any>(null);
  const [compareMode, setCompareMode] = useState(false);
  const [compareV1, setCompareV1] = useState<string>('');
  const [compareV2, setCompareV2] = useState<string>('');
  const [diff, setDiff] = useState<any>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [restoring, setRestoring] = useState(false);

  useEffect(() => {
    if (isOpen && projectId) {
      loadHistory();
    }
  }, [isOpen, projectId]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const data = await historyApi.getHistory(projectId);
      setBlocks(data);
    } catch (e: any) {
      toast.error('Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  const viewVersion = async (versionId: string) => {
    try {
      const data = await historyApi.getVersion(projectId, versionId);
      setSelectedVersion(data);
    } catch (e: any) {
      toast.error('Failed to load version');
    }
  };

  const handleCompare = async () => {
    if (!compareV1 || !compareV2) {
      toast.error('Select two versions to compare');
      return;
    }
    setDiffLoading(true);
    try {
      const data = await historyApi.compare(projectId, compareV1, compareV2);
      setDiff(data);
    } catch (e: any) {
      toast.error('Failed to compare versions');
    } finally {
      setDiffLoading(false);
    }
  };

  const handleRestore = async (versionId: string) => {
    setRestoring(true);
    try {
      await historyApi.restore(projectId, versionId);
      toast.success('Version restored successfully');
      loadHistory();
      setSelectedVersion(null);
    } catch (e: any) {
      toast.error('Failed to restore version');
    } finally {
      setRestoring(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-lg z-50 flex">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div className={`relative ml-auto w-full bg-surface border-l border-white/10 shadow-2xl flex flex-col animate-in slide-in-from-right transition-all duration-300 ease-in-out ${compareMode ? 'max-w-5xl' : 'max-w-lg'}`}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-accent" />
            <h2 className="text-lg font-display font-bold">Version History</h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setCompareMode(!compareMode);
                setDiff(null);
                setCompareV1('');
                setCompareV2('');
              }}
              className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
                compareMode
                  ? 'bg-accent text-white'
                  : 'bg-white/5 text-text-secondary hover:bg-white/10'
              }`}
            >
              <GitCompare className="w-3.5 h-3.5 inline mr-1" />
              Compare
            </button>
            <button onClick={onClose} className="p-1.5 hover:bg-white/5 rounded-lg">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-accent" />
            </div>
          ) : blocks.length === 0 ? (
            <div className="text-center py-12 text-text-secondary">
              <FileText className="w-8 h-8 mx-auto mb-3 opacity-40" />
              <p>No versions yet</p>
              <p className="text-xs mt-1">Run the pipeline to create your first version</p>
            </div>
          ) : (
            blocks.map((block) => (
              <div key={block.block_id} className="space-y-2">
                <div className="text-xs font-semibold uppercase tracking-widest text-accent">
                  {block.block_type}
                </div>
                {block.versions.map((v: any) => (
                  <div
                    key={v.id}
                    className={`p-3 rounded-xl border transition-all cursor-pointer ${
                      v.is_active
                        ? 'border-accent/30 bg-accent/5'
                        : 'border-white/5 bg-white/5 hover:border-white/10'
                    } ${
                      compareMode && (compareV1 === v.id || compareV2 === v.id)
                        ? 'ring-2 ring-accent'
                        : ''
                    }`}
                    onClick={() => {
                      if (compareMode) {
                        if (!compareV1) setCompareV1(v.id);
                        else if (!compareV2 && v.id !== compareV1) setCompareV2(v.id);
                        else {
                          setCompareV1(v.id);
                          setCompareV2('');
                        }
                      } else {
                        viewVersion(v.id);
                      }
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold">V{v.version_number}</span>
                        {v.is_active && (
                          <span className="text-[10px] px-1.5 py-0.5 bg-accent/20 text-accent rounded-full font-semibold">
                            CURRENT
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1 text-xs text-text-secondary">
                        <Clock className="w-3 h-3" />
                        {new Date(v.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    {!compareMode && (
                      <div className="flex items-center gap-2 mt-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            viewVersion(v.id);
                          }}
                          className="text-[10px] px-2 py-1 bg-white/5 rounded-lg hover:bg-white/10 transition-colors"
                        >
                          Preview
                        </button>
                        {!v.is_active && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRestore(v.id);
                            }}
                            disabled={restoring}
                            className="text-[10px] px-2 py-1 bg-accent/10 text-accent rounded-lg hover:bg-accent/20 transition-colors"
                          >
                            <RotateCcw className="w-3 h-3 inline mr-1" />
                            Restore
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ))
          )}

          {/* Compare Button */}
          {compareMode && compareV1 && compareV2 && (
            <button
              onClick={handleCompare}
              disabled={diffLoading}
              className="w-full btn-primary py-2 text-sm"
            >
              {diffLoading ? (
                <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
              ) : (
                <GitCompare className="w-4 h-4 inline mr-2" />
              )}
              Compare Selected
            </button>
          )}

          {/* Diff View */}
          {diff && (
            <div className="border border-white/10 rounded-xl overflow-hidden flex flex-col bg-bg">
              <div className="p-4 bg-white/5 border-b border-white/10 flex justify-between items-center text-sm font-semibold">
                <div className="flex items-center gap-4">
                  <span className="px-3 py-1 bg-white/5 rounded-lg border border-white/10 text-text-secondary">
                    V{diff.v1.version_number}
                  </span>
                  <span className="text-text-secondary/50">→</span>
                  <span className="px-3 py-1 bg-accent/20 text-accent rounded-lg border border-accent/20">
                    V{diff.v2.version_number}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-xs font-mono">
                  <span className="text-green-400 bg-green-400/10 px-2 py-1 rounded">+{diff.stats.additions} Additions</span>
                  <span className="text-red-400 bg-red-400/10 px-2 py-1 rounded">-{diff.stats.deletions} Deletions</span>
                </div>
              </div>
              
              <div 
                className="diff-viewer p-4 flex-1 overflow-y-auto max-h-[70vh]"
                dangerouslySetInnerHTML={{ __html: diff.html_diff }}
              />
            </div>
          )}

          {/* Version Preview */}
          {selectedVersion && !compareMode && (
            <div className="border border-white/10 rounded-xl overflow-hidden">
              <div className="p-3 bg-white/5 border-b border-white/10 flex justify-between">
                <span className="text-sm font-semibold">
                  V{selectedVersion.version_number} Preview
                </span>
                <button
                  onClick={() => setSelectedVersion(null)}
                  className="text-text-secondary hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <pre className="p-4 text-sm whitespace-pre-wrap max-h-96 overflow-y-auto scrollbar-hide text-text-secondary">
                {typeof selectedVersion.content?.script === 'string'
                  ? selectedVersion.content.script
                  : JSON.stringify(selectedVersion.content, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
