import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { configApi } from '../services/api';

interface ConfigState {
    configVersion: number;
    v33Enabled: boolean;
    streamingBatchThreshold: number;
    heartbeatIntervalMs: number;
    interruptVersion: number;
    lastFetched: string | null;
    isLoading: boolean;
    error: string | null;
    
    fetchConfig: () => Promise<void>;
}

export const useConfigStore = create<ConfigState>()(
    persist(
        (set) => ({
            configVersion: 0,
            v33Enabled: false,
            streamingBatchThreshold: 3,
            heartbeatIntervalMs: 5000,
            interruptVersion: 0,
            lastFetched: null,
            isLoading: false,
            error: null,
            
            fetchConfig: async () => {
                set({ isLoading: true, error: null });
                try {
                    const config = await configApi.getConfig();
                    set({
                        configVersion: config.config_version,
                        v33Enabled: config.v3_3_enabled,
                        streamingBatchThreshold: config.streaming_batch_threshold,
                        heartbeatIntervalMs: config.heartbeat_interval_ms,
                        interruptVersion: config.interrupt_version,
                        lastFetched: new Date().toISOString(),
                        isLoading: false,
                    });
                } catch (err: any) {
                    set({ 
                        error: err.message || 'Failed to fetch config',
                        isLoading: false 
                    });
                }
            },
        }),
        {
            name: 'config-storage',
            partialize: (state) => ({ 
                configVersion: state.configVersion,
                v33Enabled: state.v33Enabled,
                interruptVersion: state.interruptVersion
            }),
        }
    )
);
