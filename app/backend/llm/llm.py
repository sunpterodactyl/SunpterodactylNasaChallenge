import os
from langchain_core.prompts import ChatPromptTemplate
from .models import Suggestion
from .data import METRICS

def get_llm(provider: str):
    if provider == 'openai':
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'), temperature=0)
    if provider == 'anthropic':
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-5-5'), temperature=0)
    raise ValueError(f'unknown provider: {provider}')

PROMPT = ChatPromptTemplate.from_messages([
    ('system',
     'You map a researcher workflow to metrics for finding Earth analogues of Moon or Mars sites. '
     'Use ONLY these metric ids: {metric_ids}. Categories: terrain, isru, human_factors. '
     'Never invent metrics. If unsure, return fewer picks. Give one-line rationales.'),
    ('human', '{prompt}'),
])

def suggest(prompt: str, provider: str) -> Suggestion:
    valid = {m.id for m in METRICS}
    chain = PROMPT | get_llm(provider).with_structured_output(Suggestion)
    for _ in range(2):                      # one retry
        out = chain.invoke({'prompt': prompt, 'metric_ids': ', '.join(sorted(valid))})
        out.picks = [p for p in out.picks if p.metric_id in valid]
        if out.picks:
            return out
    raise ValueError('model returned no valid metrics')
