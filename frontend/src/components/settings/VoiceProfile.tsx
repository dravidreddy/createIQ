import React, { useState, useEffect } from 'react';
import {
  Mic,
  Loader2,
  Trash2,
  Check,
  Plus,
  X,
  Sparkles,
} from 'lucide-react';
import { voiceApi } from '../../services/api';
import toast from 'react-hot-toast';

export const VoiceProfile: React.FC = () => {
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [scripts, setScripts] = useState<string[]>(['']);
  const [profileLoaded, setProfileLoaded] = useState(false);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    setLoading(true);
    try {
      const data = await voiceApi.getProfile();
      setProfile(data.profile);
      setProfileLoaded(true);
    } catch (e: any) {
      // No profile yet — that's fine
    } finally {
      setLoading(false);
    }
  };

  const analyzeVoice = async () => {
    const validScripts = scripts.filter((s) => s.trim().length > 50);
    if (validScripts.length < 1) {
      toast.error('Add at least 1 script (minimum 50 characters each)');
      return;
    }
    setAnalyzing(true);
    try {
      const data = await voiceApi.analyze(validScripts);
      setProfile(data);
      toast.success('Voice profile created!');
    } catch (e: any) {
      toast.error('Voice analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  const resetProfile = async () => {
    try {
      await voiceApi.resetProfile();
      setProfile(null);
      toast.success('Voice profile reset');
    } catch (e: any) {
      toast.error('Failed to reset');
    }
  };

  const addScriptField = () => {
    if (scripts.length < 5) {
      setScripts([...scripts, '']);
    }
  };

  const removeScriptField = (index: number) => {
    setScripts(scripts.filter((_, i) => i !== index));
  };

  const updateScript = (index: number, value: string) => {
    const updated = [...scripts];
    updated[index] = value;
    setScripts(updated);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-accent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-display font-bold flex items-center gap-2">
            <Mic className="w-5 h-5 text-accent" />
            Voice Profile
          </h3>
          <p className="text-sm text-text-secondary mt-1">
            Upload your old scripts so the AI learns to write in your unique voice.
          </p>
        </div>
        {profile && (
          <button
            onClick={resetProfile}
            className="text-xs text-red-400 hover:text-red-300 transition-colors flex items-center gap-1"
          >
            <Trash2 className="w-3 h-3" /> Reset
          </button>
        )}
      </div>

      {/* Active Profile */}
      {profile && (
        <div className="border border-accent/20 bg-accent/5 rounded-2xl p-4 space-y-4">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-accent">
            <Sparkles className="w-4 h-4" />
            Your Voice DNA
          </div>

          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Tone', value: profile.tone },
              { label: 'Formality', value: profile.formality },
              { label: 'Vocabulary', value: profile.vocabulary_level },
              { label: 'Pacing', value: profile.pacing },
              { label: 'Hook Style', value: profile.hook_style },
              { label: 'Engagement', value: profile.engagement_style },
            ].map((item) => (
              <div key={item.label} className="p-2 bg-white/3 rounded-lg">
                <div className="text-[10px] text-text-secondary uppercase tracking-widest">
                  {item.label}
                </div>
                <div className="text-sm font-medium capitalize mt-0.5">
                  {(item.value || '—').replace(/_/g, ' ')}
                </div>
              </div>
            ))}
          </div>

          {/* Signature Phrases */}
          {profile.signature_phrases?.length > 0 && (
            <div>
              <div className="text-[10px] text-text-secondary uppercase tracking-widest mb-2">
                Signature Phrases
              </div>
              <div className="flex flex-wrap gap-2">
                {profile.signature_phrases.map((phrase: string, i: number) => (
                  <span
                    key={i}
                    className="text-xs px-2.5 py-1 bg-accent/10 border border-accent/20 rounded-lg text-accent"
                  >
                    "{phrase}"
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="text-[10px] text-text-secondary">
            Based on {profile.sample_count || 0} analyzed scripts •{' '}
            {profile.analyzed_at ? new Date(profile.analyzed_at).toLocaleDateString() : ''}
          </div>
        </div>
      )}

      {/* Upload Area */}
      {!profile && (
        <div className="space-y-4">
          <div className="text-xs text-text-secondary">
            Paste 2-3 of your old scripts below. The AI will analyze your writing patterns.
          </div>

          {scripts.map((script, i) => (
            <div key={i} className="relative">
              <textarea
                value={script}
                onChange={(e) => updateScript(i, e.target.value)}
                placeholder={`Paste script ${i + 1} here...`}
                className="w-full bg-white/3 border border-white/10 rounded-xl p-3 text-sm min-h-[120px] resize-y focus:border-accent/30 focus:ring-1 focus:ring-accent/20 transition-all placeholder:text-text-secondary/50"
              />
              {scripts.length > 1 && (
                <button
                  onClick={() => removeScriptField(i)}
                  className="absolute top-2 right-2 p-1 hover:bg-white/5 rounded"
                >
                  <X className="w-3.5 h-3.5 text-text-secondary" />
                </button>
              )}
              <div className="text-[10px] text-text-secondary mt-1 text-right">
                {script.split(/\s+/).filter(Boolean).length} words
              </div>
            </div>
          ))}

          <div className="flex items-center gap-3">
            {scripts.length < 5 && (
              <button
                onClick={addScriptField}
                className="text-xs text-text-secondary hover:text-accent transition-colors flex items-center gap-1"
              >
                <Plus className="w-3 h-3" /> Add another script
              </button>
            )}
          </div>

          <button
            onClick={analyzeVoice}
            disabled={analyzing}
            className="btn-primary w-full py-2.5 text-sm gap-2"
          >
            {analyzing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Analyzing your voice...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" /> Analyze My Voice
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};
