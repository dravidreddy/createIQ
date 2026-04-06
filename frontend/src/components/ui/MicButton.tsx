import React, { useState, useRef } from 'react';
import { Mic, Square, Loader2 } from 'lucide-react';
import { clsx } from 'clsx';
import api from '../../services/api';

interface MicButtonProps {
  onTranscription: (text: string) => void;
  className?: string;
  disabled?: boolean;
}

export const MicButton: React.FC<MicButtonProps> = ({ 
  onTranscription, 
  className,
  disabled = false 
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
        await handleUpload(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error('Failed to start recording', err);
      alert('Microphone access denied or not available.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleUpload = async (blob: Blob) => {
    setIsProcessing(true);
    const formData = new FormData();
    formData.append('file', blob, 'recording.webm');

    try {
      // Using shared axios instance with interceptors and base URL
      const response = await api.post('/stt/transcribe', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      if (response.data && response.data.text) {
        onTranscription(response.data.text);
      }
    } catch (err) {
      console.error('Upload failed', err);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <button
      type="button"
      onClick={isRecording ? stopRecording : startRecording}
      disabled={disabled || isProcessing}
      className={clsx(
        "relative flex items-center justify-center w-10 h-10 rounded-full transition-all duration-300",
        isRecording 
          ? "bg-red-500 text-white shadow-[0_0_15px_rgba(239,68,68,0.5)] animate-pulse" 
          : "bg-indigo-600 hover:bg-indigo-700 text-white shadow-md hover:shadow-lg",
        (disabled || isProcessing) && "opacity-50 cursor-not-allowed",
        className
      )}
      title={isRecording ? "Stop Recording" : "Voice Input"}
    >
      {isProcessing ? (
        <Loader2 className="w-5 h-5 animate-spin" />
      ) : isRecording ? (
        <Square className="w-5 h-5 fill-current" />
      ) : (
        <Mic className="w-5 h-5" />
      )}
      
      {isRecording && (
        <span className="absolute -inset-1 rounded-full border-2 border-red-500 animate-ping opacity-75" />
      )}
    </button>
  );
};
