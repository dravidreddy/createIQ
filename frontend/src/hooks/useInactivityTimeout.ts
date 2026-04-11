import { useEffect, useRef, useCallback } from 'react';
import { useStreamingStore } from '../store/streamingStore';
import { usePipelineStream } from './usePipelineStream';
import toast from 'react-hot-toast';

const INACTIVITY_TIMEOUT_MS = 10 * 60 * 1000; // 10 minutes
const ACTIVITY_EVENTS = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'] as const;

/**
 * Monitors user activity and pauses active pipeline streams
 * after 10 minutes of inactivity to prevent wasted resources.
 */
export const useInactivityTimeout = () => {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { status } = useStreamingStore();
  const { stopStream } = usePipelineStream();

  const resetTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    // Only set timeout if pipeline is actively running
    if (status === 'running') {
      timerRef.current = setTimeout(() => {
        stopStream();
        useStreamingStore.getState().setStatus('idle');
        toast('Pipeline paused due to inactivity', {
          icon: '⏸️',
          duration: 5000,
        });
      }, INACTIVITY_TIMEOUT_MS);
    }
  }, [status, stopStream]);

  useEffect(() => {
    // Attach listeners
    ACTIVITY_EVENTS.forEach((event) => {
      window.addEventListener(event, resetTimer, { passive: true });
    });

    // Start initial timer
    resetTimer();

    return () => {
      ACTIVITY_EVENTS.forEach((event) => {
        window.removeEventListener(event, resetTimer);
      });
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [resetTimer]);
};
