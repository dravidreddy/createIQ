// User types
export interface User {
    id: string          // MongoDB ObjectId string
    email: string
    display_name: string
    is_active: boolean
    is_verified: boolean
    created_at: string
    has_profile: boolean
}

export interface Profile {
    id: string          // MongoDB ObjectId string (same as user id — embedded)
    user_id: string     // MongoDB ObjectId string
    content_niche: string
    custom_niche?: string
    primary_platforms: string[]
    content_style: string
    target_audience?: string
    typical_video_length: string
    preferred_language: string
    additional_context?: string
    created_at: string
    updated_at: string
}

export interface UserWithProfile extends User {
    profile?: Profile
}

// Project types
export interface ContentIdea {
    title: string
    description: string
    trending_reason: string
    unique_angle: string
    engagement_potential: string
    source_urls: string[]
    keywords: string[]
}

export interface Collaborator {
    user_id: string
    role: 'owner' | 'editor' | 'viewer'
    added_at: string
}

export interface Project {
    id: string
    user_id: string
    title: string
    topic: string
    status: ProjectStatus
    
    // V4 Architecture fields
    parent_project_id?: string
    strategy_plan_id?: string
    platform?: string
    goal?: string
    collaborators?: Collaborator[]
    
    // Legacy pipeline outputs (migrating to ProjectVersion)
    discovered_ideas?: ContentIdea[]
    selected_idea?: ContentIdea
    generated_script?: string
    screenplay_guidance?: ScreenplayGuidance
    edited_script?: string
    editing_suggestions?: EditingSuggestions

    current_agent?: string
    error_message?: string
    created_at: string
    updated_at: string
    completed_at?: string
    completed_stages?: string[]
    niche?: string
}

export interface ProjectVersion {
    id: string
    project_id: string
    version_number: number
    is_saved: boolean
    
    ideas?: ContentIdea[]
    selected_idea?: ContentIdea
    hook?: any[]
    script?: string
    screenplay_guidance?: ScreenplayGuidance
    
    expires_at?: string
    created_at: string
    updated_at: string
}

export interface StrategyPlan {
    id: string
    user_id: string
    title: string
    focus_niche: string
    series_plan: any[]
    created_at: string
    updated_at: string
}

export type ProjectStatus =
    | 'draft'
    | 'idea_discovery'
    | 'researching'
    | 'screenplay'
    | 'editing'
    | 'completed'
    | 'failed'

export interface ScreenplayGuidance {
    overall_assessment?: string
    hook_analysis?: {
        current_hook: string
        hook_strength: string
        improvement_suggestions: string[]
    }
    structure_breakdown?: {
        timestamp_or_position: string
        section_name: string
        current_content_summary: string
        recommendation: string
        pacing_note: string
    }[]
    retention_checkpoints?: {
        position: string
        technique: string
        implementation: string
    }[]
    cta_placement?: {
        recommended_position: string
        cta_script: string
    }
}

export interface EditingSuggestions {
    overall_assessment?: {
        current_quality: string
        main_strengths: string[]
        main_weaknesses: string[]
        priority_changes: string[]
    }
    line_edits?: {
        section: string
        original_text: string
        suggested_text: string
        edit_type: string
        reason: string
        priority: string
    }[]
    hook_improvements?: {
        current_hook: string
        issues: string[]
        improved_hook: string
        why_better: string
    }
    improvement_summary?: {
        engagement_score_before: number
        engagement_score_after: number
        retention_prediction: string
        key_improvements: string[]
    }
}

// Agent stream event types (Canonical V4 Schema)
export type PipelineEventType = 
    | 'token' 
    | 'agent_start' 
    | 'agent_complete' 
    | 'group_start' 
    | 'group_complete' 
    | 'interrupt' 
    | 'cost_update' 
    | 'error' 
    | 'stream_start'
    | 'stream_end'
    | 'heartbeat' 
    | 'fallback' 
    | 'node_complete'
    | 'metrics'
    | 'thread_created';

export interface StreamEvent {
    type: PipelineEventType;
    seq: number;
    thread_id: string;
    request_id: string;
    node?: string;
    stage?: string;
    content?: any;
    tokens?: { input: number; output: number };
    cost_cents?: number;
    model?: string;
    status?: 'success' | 'fallback' | 'failed' | 'interrupted' | 'error';
    fallback_used?: boolean;
    timestamp: string;
    error_type?: string;
    retryable?: boolean;
    
    // Performance / Resilience
    final?: boolean;
    ttft_ms?: number;
    total_latency_ms?: number;
    tokens_per_second?: number;
    
    // Compatibility fields for legacy usage if any
    event_type?: PipelineEventType; 
    agent_name?: string;
}

export interface PipelineInterruptData {
    type: string;
    message: string;
    current_output: any;
    options: string[];
    node: string;
    interrupt_version?: number;
}

export interface PipelineStatusResponse {
    thread_id: string;
    current_stage?: string;
    completed_stages: string[];
    next_nodes: string[];
    total_cost_cents: number;
    total_tokens: { input: number; output: number };
    errors: string[];
    interrupt_data?: PipelineInterruptData;
    interrupt_version: number;
    config_version: number;
    
    // Production Hardening
    ttft_ms?: number;
    total_latency_ms?: number;
    tokens_per_second?: number;
}

// Auth types
export interface LoginRequest {
    email: string
    password: string
}

export interface SignupRequest {
    email: string
    password: string
    display_name: string
}

export interface Token {
    access_token: string
    refresh_token: string
    token_type: string
    expires_in: number
}

// Profile setup types
export type ContentNiche =
    | 'Tech'
    | 'Fitness'
    | 'Finance'
    | 'Education'
    | 'Entertainment'
    | 'Gaming'
    | 'Lifestyle'
    | 'Travel'
    | 'Food'
    | 'Beauty'
    | 'Other'

export type Platform =
    | 'YouTube'
    | 'Instagram Reels'
    | 'TikTok'
    | 'LinkedIn'
    | 'Podcast'
    | 'Blog'
    | 'Twitter/X'

export type ContentStyle =
    | 'Educational'
    | 'Entertaining'
    | 'Inspirational'
    | 'Casual'
    | 'Professional'
    | 'Storytelling'
    | 'Tutorial'

export type VideoLength =
    | 'Short-form (<60s)'
    | 'Medium (1-10 min)'
    | 'Long-form (10+ min)'
    | 'Mixed'

export interface ProfileCreate {
    content_niche: ContentNiche
    custom_niche?: string
    primary_platforms: Platform[]
    content_style: ContentStyle
    target_audience?: string
    typical_video_length: VideoLength
    preferred_language: string
    additional_context?: string
}

// ─── V3.3 Types ─────────────────────────────────────────────────

export type QualityMode = 'quality' | 'balanced' | 'speed'
export type UserTier = 'free' | 'pro' | 'enterprise'

export interface RankedVariant {
    variant_id: string
    total_score: number
    breakdown: {
        engagement: number
        persona: number
        novelty: number
        trend: number
    }
    dominant_signal: string
}

export interface JobSimulationRequest {
    quality_mode: QualityMode
    variant_cnt: number
    user_tier: UserTier
}

export interface JobSimulationResponse {
    estimated_cost_cents: number
    within_budget: boolean
    variant_cap: number
    effective_variant_count: number
    model_tier: string
    steps: { name: string; cost_cents: number }[]
}

export interface AgentStateResponse {
    project_id: string   // MongoDB ObjectId string
    version: number
    state: Record<string, any> | null
}
