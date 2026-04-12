import sys
import os
import asyncio

sys.path.append(os.path.abspath('c:/Users/dravi/OneDrive/Desktop/CreatorIQ/backend'))

from app.utils.prompt_orchestrator import get_prompt_orchestrator
from app.utils.prompt_loader import load_user_prompt

# Dummy Memory Service mock
class MockMemory:
    async def get_project_context(self, *args):
        return {}

roles = [
    "trend_researcher",
    "idea_generator",
    "idea_ranker",
    "hook_creator",
    "hook_evaluator",
    "deep_researcher",
    "script_drafter",
    "fact_checker",
    "structure_analyzer",
    "pacing_optimizer",
    "line_editor",
    "engagement_booster",
    "final_reviewer",
    "series_planner",
    "growth_advisor",
    "evaluator"
]

project_ctx = {
    'topic': 'Artificial Intelligence in 2026',
    'niche': 'technology',
    'target_audience': 'developers',
    'platform': 'YouTube',
    'video_length': '10 minutes',
    'brand_voice': 'professional yet approachable',
    'content_niche': 'technology',
    'style_overrides': ''
}

user_prefs = {'brand_voice': 'casual'}

kwargs = {
    'topic': project_ctx['topic'],
    'niche': project_ctx['niche'],
    'platforms': ['YouTube'],
    'platform': 'YouTube',
    'target_audience': 'developers',
    'framework': 'story loop',
    'script': 'This is a dummy script about AI. '*50,  # 1600 chars
    'ideas': [{'id': 1, 'idea': 'AI in 2026', 'title': 'AI in 2026'}],
    'hooks': [{'id': 1, 'hook': 'Wait till you see this AI cache', 'content': 'Wait till you see this'}],
    'features': [{'name': 'cache', 'description': 'AI cache'}],
    'research_results': [{'title': 'Fact 1', 'content': 'AI is fast'}],
    'selected_idea': {'title': 'Super AI Model', 'idea': 'Super AI idea'},
    'selected_hook': {'content': 'Super AI Hook', 'hook': 'hook text'},
    'user_preferences': user_prefs,
    'output_content': 'Sample output string to evaluate',
    'stage_name': 'idea_generation',
    'eval_context': 'Sample context'
}

async def main():
    orchestrator = get_prompt_orchestrator(memory_service=MockMemory())
    
    print(f"\n{'-'*80}")
    print(f"| {'Agent Role':<25} | {'Sys Toks':<10} | {'Usr Toks':<10} | {'Total Tokens':<12} |")
    print(f"{'-'*80}")

    total_tokens = 0
    valid_agents = 0

    for role in roles:
        try:
            # Sys prompt
            sys_prompt = await orchestrator.build_system_prompt(role, niche=project_ctx['niche'], user_preferences=user_prefs, project_context=project_ctx)
            sys_toks = int(len(sys_prompt) / 4.0)
            
            # Usr prompt
            user_prompt = load_user_prompt(role, **kwargs)
            usr_toks = int(len(user_prompt) / 4.0)
            
            tot_toks = sys_toks + usr_toks
            
            print(f"| {role:<25} | {sys_toks:<10} | {usr_toks:<10} | {tot_toks:<12} |")
            total_tokens += tot_toks
            valid_agents += 1
        except Exception as e:
            import traceback
            err = str(e).splitlines()[0][:15] if str(e) else type(e).__name__[:15]
            print(f"| {role:<25} | ERROR      | {err:<10} | {'-':<12} |")

    print(f"{'-'*80}")
    print(f"Average Prompt Size (Tokens): {int(total_tokens / valid_agents) if valid_agents else 0}")

if __name__ == '__main__':
    asyncio.run(main())
