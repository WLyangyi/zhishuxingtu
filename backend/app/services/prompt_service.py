from typing import Dict, Any, Optional, Tuple
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from app.core.config import settings


class PromptService:
    def __init__(self):
        self._templates: Dict[str, ChatPromptTemplate] = {}

    def create_prompt_template(
        self,
        system_prompt: str,
        user_prompt: str,
        template_id: str = None
    ) -> ChatPromptTemplate:
        template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt)
        ])
        
        if template_id:
            self._templates[template_id] = template
        
        return template

    def render(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> Tuple[str, str]:
        rendered_system = self._render_single(system_prompt, kwargs)
        rendered_user = self._render_single(user_prompt, kwargs)
        return rendered_system, rendered_user

    def _render_single(self, template_str: str, variables: Dict[str, Any]) -> str:
        try:
            template = PromptTemplate.from_template(template_str)
            return template.format(**variables)
        except Exception:
            for key, value in variables.items():
                placeholder = "{" + key + "}"
                template_str = template_str.replace(placeholder, str(value))
            return template_str

    def render_chat_template(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> ChatPromptTemplate:
        chat_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt)
        ])
        return chat_template

    def format_messages(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> list:
        chat_template = self.render_chat_template(system_prompt, user_prompt)
        return chat_template.format_messages(**kwargs)

    def get_template(self, template_id: str) -> Optional[ChatPromptTemplate]:
        return self._templates.get(template_id)

    def clear_cache(self):
        self._templates.clear()


_prompt_service_instance = None

def get_prompt_service() -> PromptService:
    global _prompt_service_instance
    if _prompt_service_instance is None:
        _prompt_service_instance = PromptService()
    return _prompt_service_instance


def render_prompt_langchain(
    system_prompt: str,
    user_prompt: str,
    **kwargs
) -> Tuple[str, str]:
    service = get_prompt_service()
    return service.render(system_prompt, user_prompt, **kwargs)
