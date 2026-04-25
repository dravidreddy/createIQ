import React, { useRef, useEffect } from 'react';
import { useStreamingStore, ChatMessage } from '../../store/streamingStore';
import { Bot, User, AlertCircle, Loader2, CheckCircle2, Sparkles } from 'lucide-react';
import clsx from 'clsx';

export function ChatTimeline() {
    const messages = useStreamingStore((s) => s.messages);
    const status = useStreamingStore((s) => s.status);
    const bottomRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages.length]);

    if (messages.length === 0 && status === 'idle') {
        return (
            <div className="flex flex-col items-center justify-center h-[400px] text-text-secondary/30 gap-4">
                <Sparkles className="w-12 h-12" />
                <p className="font-display italic text-lg">Hit Execute to start creating</p>
                <p className="text-xs font-mono uppercase tracking-widest">or type an instruction below</p>
            </div>
        );
    }

    return (
        <div className="flex-1 w-full space-y-3 py-6 px-4 overflow-y-auto min-w-0">
            {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
            ))}

            {/* Active thinking indicator */}
            {status === 'running' && (
                <div className="flex items-center gap-3 pl-12 animate-pulse">
                    <div className="flex gap-1">
                        <div className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <div className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <div className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-[10px] text-text-secondary font-mono uppercase tracking-widest">Processing...</span>
                </div>
            )}

            <div ref={bottomRef} />
        </div>
    );
}

function MessageBubble({ message }: { message: ChatMessage }) {
    const isUser = message.role === 'user';

    // User message — right aligned
    if (isUser) {
        return (
            <div className="flex justify-end animate-in slide-up">
                <div className="max-w-[80%] px-5 py-3 rounded-2xl rounded-br-md bg-accent text-bg font-medium shadow-glow">
                    {typeof message.content === 'string' ? message.content : JSON.stringify(message.content)}
                </div>
            </div>
        );
    }

    // System messages (errors, interrupts)
    if (message.role === 'system') {
        if (message.type === 'error') {
            return (
                <div className="flex items-start gap-3 animate-in slide-up">
                    <div className="w-8 h-8 rounded-xl bg-red-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <AlertCircle className="w-4 h-4 text-red-400" />
                    </div>
                    <div className="px-4 py-3 rounded-2xl rounded-bl-md bg-red-500/10 border border-red-500/20 text-red-300 text-sm max-w-[80%]">
                        {typeof message.content === 'string' ? message.content : JSON.stringify(message.content)}
                    </div>
                </div>
            );
        }
        if (message.type === 'interrupt') {
            return (
                <div className="flex items-start gap-3 animate-in slide-up">
                    <div className="w-8 h-8 rounded-xl bg-amber-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <AlertCircle className="w-4 h-4 text-amber-400" />
                    </div>
                    <div className="px-4 py-3 rounded-2xl rounded-bl-md bg-amber-500/10 border border-amber-500/20 text-amber-200 text-sm max-w-[80%]">
                        ⏸ {typeof message.content === 'string' ? message.content : JSON.stringify(message.content)}
                    </div>
                </div>
            );
        }
    }

    // Agent thinking messages — small, subtle, left-aligned
    if (message.type === 'thinking') {
        return (
            <div className="flex items-center gap-3 animate-in slide-up">
                <div className="w-8 h-8 rounded-xl bg-accent/10 flex items-center justify-center flex-shrink-0">
                    <Loader2 className="w-3.5 h-3.5 text-accent animate-spin" />
                </div>
                <span className="text-sm text-text-secondary/80 font-medium">
                    {message.content}
                </span>
            </div>
        );
    }

    // Agent progress (checkmarks)
    if (message.type === 'progress') {
        return (
            <div className="flex items-center gap-3 pl-0.5 animate-in slide-up">
                <div className="w-8 h-8 rounded-xl bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                </div>
                <span className="text-xs text-emerald-400/80 font-mono capitalize">
                    {message.content}
                </span>
            </div>
        );
    }

    // Agent output — main content bubble
    if (message.type === 'output') {
        return (
            <div className="flex items-start gap-3 animate-in slide-up">
                <div className="w-8 h-8 rounded-xl bg-accent/10 flex items-center justify-center flex-shrink-0 mt-1">
                    <Bot className="w-4 h-4 text-accent" />
                </div>
                <div className="flex-1 min-w-0">
                    <div className="p-5 rounded-2xl rounded-bl-md bg-surface/80 border border-white/5 shadow-xl">
                        <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-text-primary/90 break-words">
                            {typeof message.content === 'string' ? message.content : JSON.stringify(message.content, null, 2)}
                        </pre>
                    </div>
                </div>
            </div>
        );
    }

    return null;
}
