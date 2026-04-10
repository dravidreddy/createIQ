import React, { useState, useEffect, useRef } from 'react';
import { Mic, Square } from 'lucide-react';
import { clsx } from 'clsx';
import toast from 'react-hot-toast';

interface MicButtonProps {
  onTranscription: (text: string) => void;
  currentText?: string;
  className?: string;
  disabled?: boolean;
}

declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

export const MicButton: React.FC<MicButtonProps> = ({ 
  onTranscription, 
  currentText = '',
  className,
  disabled = false 
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const recognitionRef = useRef<any>(null);
  const finalTranscriptRef = useRef<string>('');
  const baselineTextRef = useRef<string>('');

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsRecording(true);
        finalTranscriptRef.current = '';
        // Capture the text that was in the input just before we started talking
        baselineTextRef.current = currentText.trim();
      };

      recognition.onresult = (event: any) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }

        if (finalTranscript) {
           finalTranscriptRef.current += finalTranscript + ' ';
        }
        
        let liveTranscript = (finalTranscriptRef.current + interimTranscript).trim();
        
        // Output combined baseline text + new live transcription
        if (baselineTextRef.current) {
            onTranscription(`${baselineTextRef.current} ${liveTranscript}`);
        } else {
            onTranscription(liveTranscript);
        }
      };

      recognition.onerror = (event: any) => {
        if (event.error !== 'no-speech') {
            console.error('Speech recognition error', event.error);
            setIsRecording(false);
            if (event.error === 'not-allowed') {
                toast.error('Microphone access denied.');
            } else {
                toast.error(`Speech error: ${event.error}`);
            }
        }
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
    } else {
        console.warn("Speech Recognition API not supported in this browser.");
    }

    return () => {
        if (recognitionRef.current) {
            recognitionRef.current.abort();
        }
    };
  }, [onTranscription, currentText]);

  const startRecording = () => {
    if (!recognitionRef.current) {
        toast.error("Your browser does not support real-time speech recognition. Please use Google Chrome or Safari.");
        return;
    }
    try {
      recognitionRef.current.start();
    } catch (e) {
      // Ignore if already started
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current && isRecording) {
      recognitionRef.current.stop();
    }
  };

  return (
    <button
      type="button"
      onClick={isRecording ? stopRecording : startRecording}
      disabled={disabled}
      className={clsx(
        "relative flex items-center justify-center w-10 h-10 rounded-full transition-all duration-300",
        isRecording 
          ? "bg-red-500 text-white shadow-[0_0_15px_rgba(239,68,68,0.5)] animate-pulse" 
          : "bg-indigo-600 hover:bg-indigo-700 text-white shadow-md hover:shadow-lg",
        disabled && "opacity-50 cursor-not-allowed",
        className
      )}
      title={isRecording ? "Stop Recording" : "Voice Input"}
    >
      {isRecording ? (
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
