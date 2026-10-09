from pydantic import BaseModel

from app.strategies.templates import ALL_TEMPLATES
from app.strategies.types import StrategyMetadata, StrategyTemplate


class StrategyRegistry:
    def __init__(self) -> None:
        self._templates: dict[str, StrategyTemplate] = {
            t.metadata.id: t for t in ALL_TEMPLATES
        }

    def list_metadata(self) -> list[StrategyMetadata]:
        return [t.metadata for t in self._templates.values()]

    def get(self, template_id: str) -> StrategyTemplate:
        if template_id not in self._templates:
            raise KeyError(f"Unknown strategy template: {template_id}")
        return self._templates[template_id]

    def params_schema(self, template_id: str) -> dict:
        template = self.get(template_id)
        return template.params_model.model_json_schema()

    def parse_params(self, template_id: str, raw: dict) -> BaseModel:
        template = self.get(template_id)
        return template.params_model.model_validate(raw)


strategy_registry = StrategyRegistry()
