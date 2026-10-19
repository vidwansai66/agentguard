from typing import Any, Callable, Dict, List, Optional, Type
from app.adapters.base import AgentAdapter
from app.agents.sample_ticket_agent import SampleTicketAgent
from app.agents.custom_test_agent import CustomTestAgent
from app.adapters.http_adapter import HttpAgentAdapter, HttpAdapterSecurityError
from app.adapters.wrappers.callable_wrapper import CallableAgentWrapper
from app.adapters.model_backed_adapter import ModelBackedAgentAdapter
from app.adapters.frameworks.langgraph_adapter import LangGraphAgentAdapter
from app.agents.existing_sample_agent import existing_ticket_solver, ExistingCustomerSupportAgent
from app.agents.framework_sample_graph import customer_support_graph
from app.core.errors import ValidationError, NotFoundError

class AgentRegistry:
    def __init__(self):
        # Trusted Python Adapter classes
        self._trusted_python_classes: Dict[str, Type[AgentAdapter]] = {
            "agent-ticket-sample": SampleTicketAgent,
            "SampleTicketAgent": SampleTicketAgent,
            "agent-custom-python": CustomTestAgent,
            "CustomTestAgent": CustomTestAgent,
        }

        # Trusted Python callables for SDK wrappers
        self._trusted_callables: Dict[str, Callable[..., Any]] = {
            "existing_ticket_solver": existing_ticket_solver,
            "existing_sample_agent.solve_ticket": existing_ticket_solver,
            "ExistingCustomerSupportAgent": ExistingCustomerSupportAgent().handle_request,
            "legacy_support_handler": existing_ticket_solver
        }

        # Registered Framework Graphs
        self._framework_graphs: Dict[str, Any] = {
            "customer_support_graph": customer_support_graph,
            "langgraph_ticket_graph": customer_support_graph
        }

    def register_python_adapter(self, name: str, adapter_cls: Type[AgentAdapter]) -> None:
        """Register a trusted Python agent class in the application."""
        self._trusted_python_classes[name] = adapter_cls

    def register_callable(self, name: str, target: Callable[..., Any]) -> None:
        """Register a trusted Python callable for SDK wrapping."""
        self._trusted_callables[name] = target

    def register_framework_graph(self, name: str, graph: Any) -> None:
        """Register a compiled framework graph."""
        self._framework_graphs[name] = graph

    def get_trusted_adapters(self) -> List[str]:
        return list(self._trusted_python_classes.keys())

    def get_trusted_callables(self) -> List[str]:
        return list(self._trusted_callables.keys())

    def get_framework_graphs(self) -> List[str]:
        return list(self._framework_graphs.keys())

    def get_framework_catalog(self) -> List[Dict[str, Any]]:
        return [
            {
                "framework": "langgraph",
                "status": "supported",
                "installed_version": "1.2.16",
                "description": "Compiled StateGraph workflows with node-level event capture and instrumented tool injection.",
                "example_target": "customer_support_graph"
            },
            {
                "framework": "crewai",
                "status": "planned",
                "description": "CrewAI task orchestration with role-based agents (Planned integration contract).",
                "example_target": None
            },
            {
                "framework": "autogen",
                "status": "planned",
                "description": "Microsoft AutoGen conversational multi-agent systems (Planned integration contract).",
                "example_target": None
            }
        ]

    def validate_adapter_config(self, adapter_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validates adapter configuration before saving to database."""
        obs_level = config.get("observability_level", "level_3_instrumented_tools")

        if adapter_type == "python":
            cls_name = config.get("adapter_class") or config.get("class_name") or "CustomTestAgent"
            if cls_name not in self._trusted_python_classes:
                raise ValidationError(
                    f"Unsupported or untrusted Python adapter class '{cls_name}'. "
                    f"Trusted classes: {list(self._trusted_python_classes.keys())}"
                )
            return {
                "valid": True,
                "adapter_type": "python",
                "class_name": cls_name,
                "observability_level": obs_level
            }

        elif adapter_type in ["python_sdk_wrapper", "sdk_wrapper"]:
            target_name = config.get("target_name") or config.get("callable_name") or "existing_ticket_solver"
            if target_name not in self._trusted_callables:
                raise ValidationError(
                    f"Untrusted SDK wrapper target '{target_name}'. "
                    f"Available trusted callables: {list(self._trusted_callables.keys())}"
                )
            return {
                "valid": True,
                "adapter_type": "python_sdk_wrapper",
                "target_name": target_name,
                "observability_level": obs_level
            }

        elif adapter_type == "http":
            base_url = (config.get("base_url") or "").strip()
            if not base_url:
                raise ValidationError("HTTP Adapter requires a non-empty 'base_url'.")
            temp_adapter = HttpAgentAdapter(agent_id="validation-check", config=config)
            try:
                temp_adapter._validate_ssrf_safety(base_url)
            except HttpAdapterSecurityError as se:
                raise ValidationError(f"Security validation failed for URL '{base_url}': {str(se)}")

            req_map = config.get("request_mapping")
            if req_map and not isinstance(req_map, dict):
                raise ValidationError("HTTP request_mapping must be a JSON object.")
            resp_map = config.get("response_mapping")
            if resp_map and not isinstance(resp_map, dict):
                raise ValidationError("HTTP response_mapping must be a JSON object.")

            return {
                "valid": True,
                "adapter_type": "http",
                "base_url": base_url,
                "invocation_endpoint": config.get("invocation_endpoint", "/run"),
                "observability_level": obs_level
            }

        elif adapter_type == "model_backed":
            val_res = ModelBackedAgentAdapter.validate_config(config)
            if not val_res.get("valid"):
                raise ValidationError(f"Model-backed config error: {val_res.get('error')}")
            return {
                "valid": True,
                "adapter_type": "model_backed",
                "model": config.get("model", "gpt-4o-mini"),
                "base_url": config.get("base_url", "https://api.openai.com/v1"),
                "observability_level": "level_3_instrumented_tools"
            }

        elif adapter_type in ["langgraph", "framework"]:
            val_res = LangGraphAgentAdapter.validate_config(config)
            if not val_res.get("valid"):
                raise ValidationError(f"Framework config error: {val_res.get('error')}")
            return {
                "valid": True,
                "adapter_type": "langgraph",
                "framework": "langgraph",
                "observability_level": "level_3_instrumented_tools"
            }

        else:
            raise ValidationError(
                f"Unsupported adapter_type '{adapter_type}'. Allowed types: ['python', 'http', 'python_sdk_wrapper', 'model_backed', 'langgraph']"
            )

    def get_agent(
        self,
        agent_id: str,
        version: str = "1.0.0",
        strategy: str = "baseline",
        config: Optional[Dict[str, Any]] = None,
        adapter_type: str = "python"
    ) -> AgentAdapter:
        """
        Factory method to instantiate a compatible AgentAdapter.
        """
        cfg = config or {}

        # 1. HTTP Adapter
        if adapter_type == "http" or cfg.get("adapter_type") == "http" or "base_url" in cfg and "model" not in cfg:
            return HttpAgentAdapter(
                agent_id=agent_id,
                version=version,
                strategy=strategy,
                config=cfg
            )

        # 2. Model-Backed Adapter (LLM)
        if adapter_type == "model_backed" or cfg.get("adapter_type") == "model_backed" or "model" in cfg:
            return ModelBackedAgentAdapter(
                agent_id=agent_id,
                version=version,
                config=cfg
            )

        # 3. LangGraph Framework Adapter
        if adapter_type in ["langgraph", "framework"] or cfg.get("adapter_type") in ["langgraph", "framework"]:
            graph_key = cfg.get("graph_name", "customer_support_graph")
            graph_inst = self._framework_graphs.get(graph_key, customer_support_graph)
            return LangGraphAgentAdapter(
                agent_id=agent_id,
                graph_instance=graph_inst,
                version=version,
                config=cfg
            )

        # 4. Python SDK Wrapper
        if adapter_type in ["python_sdk_wrapper", "sdk_wrapper"] or cfg.get("adapter_type") == "python_sdk_wrapper":
            target_name = cfg.get("target_name") or cfg.get("callable_name") or "existing_ticket_solver"
            target_callable = self._trusted_callables.get(target_name, existing_ticket_solver)
            return CallableAgentWrapper(
                agent_id=agent_id,
                target_callable=target_callable,
                version=version,
                strategy=strategy,
                config=cfg
            )

        # 5. Python Adapter from trusted registry
        cls_name = cfg.get("adapter_class") or cfg.get("class_name") or agent_id
        agent_cls = self._trusted_python_classes.get(cls_name)
        if not agent_cls:
            agent_cls = self._trusted_python_classes.get(agent_id, SampleTicketAgent)

        return agent_cls(agent_id=agent_id, version=version, strategy=strategy, config=cfg)

agent_registry = AgentRegistry()

