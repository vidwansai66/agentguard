import os
import re
import ipaddress
import urllib.parse
import time
from contextlib import nullcontext
from typing import Any, Dict, List, Optional
import httpx
from app.adapters.base import AgentAdapter
from app.adapters.models import AgentTaskInput, AgentExecutionContext, AgentTaskResult
from app.tracing.sanitizer import sanitize_text

# Forbidden SSRF Targets (cloud metadata, link-local, multicast, etc.)
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local / Cloud metadata (AWS, GCP, Azure)
    ipaddress.ip_network("224.0.0.0/4"),       # Multicast
    ipaddress.ip_network("240.0.0.0/4"),       # Reserved
    ipaddress.ip_network("0.0.0.0/8"),         # Broadcast
]

class HttpAdapterSecurityError(Exception):
    pass

def _extract_json_path(data: Any, path: Optional[str]) -> Any:
    """Extracts a nested value from a dictionary/list using dot notation (e.g., 'data.answer')."""
    if not path or not isinstance(data, (dict, list)):
        return None
    parts = path.strip().split(".")
    curr = data
    for part in parts:
        if isinstance(curr, dict):
            if part in curr:
                curr = curr[part]
            else:
                return None
        elif isinstance(curr, list) and part.isdigit():
            idx = int(part)
            if 0 <= idx < len(curr):
                curr = curr[idx]
            else:
                return None
        else:
            return None
    return curr

class HttpAgentAdapter(AgentAdapter):
    """
    HTTP Agent Adapter for testing external AI agent microservices.
    Enforces strict SSRF protection, configurable timeouts, request/response mappings,
    observability level distinction, and secret protection.
    """
    adapter_type: str = "http"

    def __init__(
        self,
        agent_id: str,
        version: str = "1.0.0",
        strategy: str = "default",
        config: Optional[Dict[str, Any]] = None
    ):
        self.agent_id = agent_id
        self.version = version
        self.strategy = strategy
        self.config = config or {}
        self.initialize(self.config)

    def initialize(self, config: Dict[str, Any]) -> None:
        self.config = dict(config or {})
        if "_client" in self.config:
            self._client = self.config.pop("_client")
        self.base_url = (self.config.get("base_url") or "").strip().rstrip("/")
        self.health_endpoint = self.config.get("health_endpoint", "/health")
        if self.health_endpoint and not self.health_endpoint.startswith("/"):
            self.health_endpoint = f"/{self.health_endpoint}"

        self.invocation_endpoint = self.config.get("invocation_endpoint", "/run")
        if not self.invocation_endpoint.startswith("/"):
            self.invocation_endpoint = f"/{self.invocation_endpoint}"

        self.connect_timeout = float(self.config.get("connect_timeout_seconds", 5.0))
        self.read_timeout = float(self.config.get("read_timeout_seconds", 15.0))
        self.secret_env_var = self.config.get("secret_env_var")
        self.auth_type = self.config.get("auth_type", "Bearer")
        self.auth_header_name = self.config.get("auth_header_name", "Authorization")
        self.allow_local_dev = bool(self.config.get("allow_local_dev", True))

        self.observability_level = self.config.get("observability_level", "level_1_result_only")
        self.event_format = self.config.get("event_format", "agentguard_standard")
        self.request_mapping = self.config.get("request_mapping", {})
        self.response_mapping = self.config.get("response_mapping", {})

        self.declared_capabilities = self.config.get("declared_capabilities", [
            "ticket_create",
            "ticket_query",
            "ticket_get"
        ])
        self.supported_tools = self.config.get("supported_tools", [
            "ticket_create",
            "ticket_query",
            "ticket_get"
        ])

        if self.base_url:
            self._validate_ssrf_safety(self.base_url)

    def _validate_ssrf_safety(self, url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            raise HttpAdapterSecurityError(f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are permitted.")

        hostname = parsed.hostname or ""
        if not hostname:
            raise HttpAdapterSecurityError("Missing hostname in agent base_url.")

        # Check for direct cloud metadata hostnames
        if hostname.lower() in ["metadata.google.internal", "instance-data", "169.254.169.254"]:
            raise HttpAdapterSecurityError(f"Access to cloud metadata target '{hostname}' is strictly prohibited.")

        # Resolve IP or parse direct IP
        try:
            ip = ipaddress.ip_address(hostname)
            # Check against blocked networks
            for net in BLOCKED_IP_NETWORKS:
                if ip in net:
                    raise HttpAdapterSecurityError(f"Target IP '{ip}' belongs to blocked network '{net}'.")

            # Check loopback / private
            if ip.is_loopback:
                if not self.allow_local_dev:
                    raise HttpAdapterSecurityError("Loopback targets (localhost/127.0.0.1) are disabled in non-development mode.")
            elif ip.is_private:
                if not self.allow_local_dev:
                    raise HttpAdapterSecurityError(f"Private network address '{ip}' is not permitted without explicit dev authorization.")

        except ValueError:
            # Hostname is a domain name
            if not self.allow_local_dev and hostname.lower() in ["localhost", "127.0.0.1", "0.0.0.0"]:
                raise HttpAdapterSecurityError("Localhost targets are not permitted in non-development mode.")

    def _get_auth_header(self) -> Dict[str, str]:
        if not self.secret_env_var:
            return {}
        token = os.environ.get(self.secret_env_var, "")
        if not token:
            return {}

        if self.auth_type == "Bearer":
            return {self.auth_header_name: f"Bearer {token}"}
        elif self.auth_type == "ApiKey-Header":
            return {self.auth_header_name: token}
        elif self.auth_type == "Basic":
            return {self.auth_header_name: f"Basic {token}"}
        elif self.auth_type == "Custom":
            return {self.auth_header_name: token}
        return {self.auth_header_name: token}

    def test_connection(self) -> Dict[str, Any]:
        """Performs connectivity, handshake, and configuration test."""
        if not self.base_url:
            return {
                "status": "error",
                "message": "Agent base_url is not configured.",
                "adapter_type": "http"
            }

        try:
            self._validate_ssrf_safety(self.base_url)
        except HttpAdapterSecurityError as se:
            return {
                "status": "error",
                "message": f"Security validation failed: {str(se)}",
                "adapter_type": "http"
            }

        headers = self._get_auth_header()
        headers["User-Agent"] = "AgentGuard-Adapter/1.0"

        # If a health endpoint is configured, test it
        if self.health_endpoint:
            health_url = f"{self.base_url}{self.health_endpoint}"
            try:
                client_ctx = getattr(self, "_client", None) or httpx.Client(
                    timeout=httpx.Timeout(self.connect_timeout, read=self.read_timeout),
                    follow_redirects=False,
                    verify=True
                )
                with client_ctx if hasattr(client_ctx, "__enter__") else nullcontext(client_ctx) as client:
                    resp = client.get(health_url, headers=headers)
                    if resp.status_code == 200:
                        data = {}
                        try:
                            data = resp.json()
                        except Exception:
                            pass
                        return {
                            "status": "healthy",
                            "agent_id": self.agent_id,
                            "adapter_type": "http",
                            "observability_level": self.observability_level,
                            "base_url": self.base_url,
                            "health_endpoint": self.health_endpoint,
                            "invocation_endpoint": self.invocation_endpoint,
                            "response_code": resp.status_code,
                            "declared_capabilities": self.declared_capabilities,
                            "message": "HTTP Agent endpoint reached successfully via health check.",
                            "service_info": data
                        }
                    else:
                        return {
                            "status": "warning",
                            "agent_id": self.agent_id,
                            "adapter_type": "http",
                            "observability_level": self.observability_level,
                            "base_url": self.base_url,
                            "response_code": resp.status_code,
                            "message": f"Health endpoint {self.health_endpoint} responded with HTTP {resp.status_code}"
                        }
            except httpx.ConnectTimeout:
                return {"status": "error", "message": f"Connection timed out after {self.connect_timeout}s.", "adapter_type": "http"}
            except httpx.ConnectError as ce:
                return {"status": "error", "message": f"Connection refused to {self.base_url}: {str(ce)}", "adapter_type": "http"}
            except Exception as e:
                return {"status": "error", "message": sanitize_text(str(e)), "adapter_type": "http"}
        else:
            # No health endpoint defined; verify base URL schema & SSRF
            return {
                "status": "healthy",
                "agent_id": self.agent_id,
                "adapter_type": "http",
                "observability_level": self.observability_level,
                "base_url": self.base_url,
                "invocation_endpoint": self.invocation_endpoint,
                "message": "HTTP Agent configured without health endpoint; validation passed."
            }

    def run_task(
        self,
        task_input: Any,
        context: Any,
        tool_invoker: Any
    ) -> Dict[str, Any]:
        """
        Executes external HTTP agent task.
        Supports:
        - LEVEL 1 (Result-Only): Dispatches mapped payload, records final output.
        - LEVEL 2 (Structured-Events): Extracts external execution events and records them in AgentGuard trace.
        - LEVEL 3 (Instrumented-Tools): Evaluates tool_call_request delegations through ToolInvoker.
        """
        self._validate_ssrf_safety(self.base_url)

        inp_dict = task_input.model_dump() if hasattr(task_input, "model_dump") else dict(task_input or {})
        ctx_dict = context.model_dump() if hasattr(context, "model_dump") else dict(context or {})

        prompt = inp_dict.get("prompt") or inp_dict.get("description") or inp_dict.get("task") or str(inp_dict)

        # Build payload based on request_mapping if configured
        if isinstance(self.request_mapping, dict) and self.request_mapping:
            payload: Dict[str, Any] = {}
            for target_key, src in self.request_mapping.items():
                if isinstance(src, str):
                    if src == "prompt":
                        payload[target_key] = prompt
                    elif src == "run_id":
                        payload[target_key] = ctx_dict.get("run_id")
                    elif src == "scenario_id":
                        payload[target_key] = ctx_dict.get("scenario_id")
                    elif src in inp_dict:
                        payload[target_key] = inp_dict[src]
                    elif src in ctx_dict:
                        payload[target_key] = ctx_dict[src]
                    else:
                        payload[target_key] = src
                else:
                    payload[target_key] = src
        else:
            payload = {
                "run_id": ctx_dict.get("run_id"),
                "scenario_id": ctx_dict.get("scenario_id"),
                "task_input": inp_dict,
                "declared_capabilities": self.declared_capabilities,
                "supported_tools": self.supported_tools,
                "config": self.config
            }

        headers = self._get_auth_header()
        headers["Content-Type"] = "application/json"
        headers["User-Agent"] = "AgentGuard-Adapter/1.0"

        run_url = f"{self.base_url}{self.invocation_endpoint}"
        dispatch_start_time = time.perf_counter()
        tool_invoker.record_decision(
            action="http_dispatch_start",
            reasoning=f"Dispatching task to {run_url} [Observability: {self.observability_level}, connect_timeout={self.connect_timeout}s, read_timeout={self.read_timeout}s]"
        )

        try:
            client_ctx = getattr(self, "_client", None) or httpx.Client(
                timeout=httpx.Timeout(self.connect_timeout, read=self.read_timeout),
                follow_redirects=False,
                verify=True
            )
            with client_ctx if hasattr(client_ctx, "__enter__") else nullcontext(client_ctx) as client:
                resp = client.post(run_url, json=payload, headers=headers)
                duration_ms = round((time.perf_counter() - dispatch_start_time) * 1000, 2)

                # 1. Non-2xx HTTP status handling
                if resp.status_code < 200 or resp.status_code >= 300:
                    raw_snippet = sanitize_text(resp.text[:300]) if resp.text else ""
                    if self.secret_env_var:
                        sec = os.environ.get(self.secret_env_var, "")
                        if sec:
                            raw_snippet = raw_snippet.replace(sec, "[REDACTED_SECRET]")

                    err_msg = f"HTTP Agent service returned status code {resp.status_code}: {raw_snippet}"
                    if hasattr(tool_invoker, "record_http_error"):
                        tool_invoker.record_http_error(
                            action="http_response_error",
                            error_message=err_msg,
                            duration_ms=duration_ms,
                            output_data={
                                "status_code": resp.status_code,
                                "url": run_url,
                                "response_preview": raw_snippet
                            },
                            severity="high"
                        )
                    elif hasattr(tool_invoker, "recorder") and hasattr(tool_invoker.recorder, "record_event"):
                        tool_invoker.current_step = getattr(tool_invoker, "current_step", 0) + 1
                        tool_invoker.recorder.record_event(
                            step_index=tool_invoker.current_step,
                            event_type="error",
                            action_name="http_response_error",
                            severity="high",
                            output_data={"status_code": resp.status_code, "url": run_url, "response_preview": raw_snippet},
                            duration_ms=duration_ms,
                            error_message=err_msg
                        )

                    tool_invoker.record_decision(
                        action="http_error",
                        reasoning=f"HTTP service returned non-2xx status code {resp.status_code}"
                    )
                    return {
                        "status": "failed",
                        "status_code": resp.status_code,
                        "disrupted": True,
                        "recovered": False,
                        "error": err_msg,
                        "message": f"External HTTP agent returned status {resp.status_code}",
                        "observability_level": self.observability_level
                    }

                # 2. Parse JSON response
                try:
                    result_data = resp.json()
                except Exception as json_err:
                    raw_snippet = sanitize_text(resp.text[:300]) if resp.text else ""
                    err_msg = f"HTTP Agent returned invalid JSON: {str(json_err)}"
                    if hasattr(tool_invoker, "record_http_error"):
                        tool_invoker.record_http_error(
                            action="http_malformed_json",
                            error_message=err_msg,
                            duration_ms=duration_ms,
                            output_data={
                                "status_code": resp.status_code,
                                "url": run_url,
                                "response_preview": raw_snippet
                            },
                            severity="high"
                        )
                    elif hasattr(tool_invoker, "recorder") and hasattr(tool_invoker.recorder, "record_event"):
                        tool_invoker.current_step = getattr(tool_invoker, "current_step", 0) + 1
                        tool_invoker.recorder.record_event(
                            step_index=tool_invoker.current_step,
                            event_type="error",
                            action_name="http_malformed_json",
                            severity="high",
                            output_data={"status_code": resp.status_code, "url": run_url, "response_preview": raw_snippet},
                            duration_ms=duration_ms,
                            error_message=err_msg
                        )

                    tool_invoker.record_decision(
                        action="http_error",
                        reasoning=f"HTTP response JSON parse error: {str(json_err)}"
                    )
                    return {
                        "status": "failed",
                        "status_code": resp.status_code,
                        "disrupted": True,
                        "recovered": False,
                        "error": err_msg,
                        "message": "HTTP service responded with non-JSON payload",
                        "observability_level": self.observability_level
                    }

                # 3. Validate JSON object structure
                if not isinstance(result_data, dict):
                    err_msg = f"HTTP Agent response must be a JSON object, not {type(result_data).__name__}."
                    if hasattr(tool_invoker, "record_http_error"):
                        tool_invoker.record_http_error(
                            action="http_schema_error",
                            error_message=err_msg,
                            duration_ms=duration_ms,
                            output_data={"status_code": resp.status_code, "response_type": type(result_data).__name__},
                            severity="high"
                        )
                    elif hasattr(tool_invoker, "recorder") and hasattr(tool_invoker.recorder, "record_event"):
                        tool_invoker.current_step = getattr(tool_invoker, "current_step", 0) + 1
                        tool_invoker.recorder.record_event(
                            step_index=tool_invoker.current_step,
                            event_type="error",
                            action_name="http_schema_error",
                            severity="high",
                            output_data={"status_code": resp.status_code, "response_type": type(result_data).__name__},
                            duration_ms=duration_ms,
                            error_message=err_msg
                        )

                    tool_invoker.record_decision(
                        action="http_error",
                        reasoning=err_msg
                    )
                    return {
                        "status": "failed",
                        "status_code": resp.status_code,
                        "disrupted": True,
                        "recovered": False,
                        "error": err_msg,
                        "message": err_msg,
                        "observability_level": self.observability_level
                    }

                # LEVEL 3: If external agent requested a tool call through AgentGuard:
                if "tool_call_request" in result_data:
                    req = result_data["tool_call_request"]
                    tool_res = tool_invoker.call_tool(
                        tool_name=req.get("tool_name", "ticket_tool"),
                        params=req.get("params", {}),
                        retry_count=req.get("retry_count", 0)
                    )
                    return {
                        "status": "success",
                        "ticket_id": tool_res.get("ticket_id"),
                        "disrupted": False,
                        "recovered": False,
                        "message": "Tool executed via HTTP adapter delegation",
                        "observability_level": self.observability_level
                    }

                # LEVEL 2: Extract structured events if present
                if self.observability_level == "level_2_structured_events":
                    events_path = self.response_mapping.get("events_path", "events")
                    ext_events = _extract_json_path(result_data, events_path) or result_data.get("events") or result_data.get("trace") or result_data.get("steps") or []
                    if isinstance(ext_events, list):
                        for idx, ev in enumerate(ext_events):
                            if isinstance(ev, dict):
                                ev_action = ev.get("action") or ev.get("name") or "external_step"
                                ev_type = ev.get("type", "agent_step")
                                tool_invoker.recorder.record_event(
                                    step_index=tool_invoker.current_step + idx + 1,
                                    event_type=ev_type,
                                    action_name=ev_action,
                                    tool_name=ev.get("tool_name"),
                                    input_data=ev.get("input", {}),
                                    output_data=ev.get("output", {}),
                                    duration_ms=float(ev.get("duration_ms", 1.0))
                                )
                        tool_invoker.current_step += len(ext_events)

                # 4. Extract response fields using response_mapping if configured
                mapping_failed = False
                mapping_error_msg = None
                result_val = None
                status_val = None
                error_val = None
                ticket_id_val = None

                if self.response_mapping:
                    result_path = self.response_mapping.get("result_path")
                    status_path = self.response_mapping.get("status_path")
                    error_path = self.response_mapping.get("error_path")
                    ticket_id_path = self.response_mapping.get("ticket_id_path")

                    if result_path:
                        result_val = _extract_json_path(result_data, result_path)
                    if status_path:
                        status_val = _extract_json_path(result_data, status_path)
                    if error_path:
                        error_val = _extract_json_path(result_data, error_path)
                    if ticket_id_path:
                        ticket_id_val = _extract_json_path(result_data, ticket_id_path)

                    # Fallbacks if paths weren't strictly resolved
                    if result_val is None:
                        result_val = result_data.get("output") or result_data.get("result") or result_data.get("message")
                    if status_val is None and not status_path:
                        status_val = result_data.get("status", "success")
                    if error_val is None and not error_path:
                        error_val = result_data.get("error")
                    if ticket_id_val is None and not ticket_id_path:
                        ticket_id_val = result_data.get("ticket_id")

                    # Check for mapping failure
                    if status_path and status_val is None:
                        mapping_failed = True
                        mapping_error_msg = f"Configured status_path '{status_path}' could not be resolved from HTTP response keys {list(result_data.keys())}"
                    elif result_path and result_val is None and not any(k in result_data for k in ["output", "result", "message"]):
                        mapping_failed = True
                        mapping_error_msg = f"Configured result_path '{result_path}' could not be resolved from HTTP response keys {list(result_data.keys())}"
                else:
                    status_val = result_data.get("status", "success")
                    result_val = result_data.get("message") or result_data.get("output") or result_data.get("result") or "Completed by HTTP agent"
                    error_val = result_data.get("error")
                    ticket_id_val = result_data.get("ticket_id")

                # Handle response-mapping failure
                if mapping_failed:
                    missing_field = status_path if (status_path and status_val is None) else result_path
                    if hasattr(tool_invoker, "record_http_error"):
                        tool_invoker.record_http_error(
                            action="http_mapping_error",
                            error_message=mapping_error_msg or "Response mapping error",
                            duration_ms=duration_ms,
                            output_data={
                                "status_code": resp.status_code,
                                "response_keys": list(result_data.keys()),
                                "missing_path": missing_field,
                                "mapping_config": self.response_mapping
                            },
                            severity="high"
                        )
                    elif hasattr(tool_invoker, "recorder") and hasattr(tool_invoker.recorder, "record_event"):
                        tool_invoker.current_step = getattr(tool_invoker, "current_step", 0) + 1
                        tool_invoker.recorder.record_event(
                            step_index=tool_invoker.current_step,
                            event_type="error",
                            action_name="http_mapping_error",
                            severity="high",
                            output_data={
                                "status_code": resp.status_code,
                                "response_keys": list(result_data.keys()),
                                "missing_path": missing_field,
                                "mapping_config": self.response_mapping
                            },
                            duration_ms=duration_ms,
                            error_message=mapping_error_msg
                        )

                    tool_invoker.record_decision(
                        action="http_error",
                        reasoning=f"Response mapping failure: {mapping_error_msg}"
                    )
                    return {
                        "status": "failed",
                        "status_code": resp.status_code,
                        "disrupted": True,
                        "recovered": False,
                        "error": mapping_error_msg,
                        "message": f"Response mapping failed: {mapping_error_msg}",
                        "raw_output": result_data,
                        "observability_level": self.observability_level
                    }

                # Determine mapped task outcome
                is_task_success = (str(status_val).lower() in ["success", "completed", "ok", "true"]) and not error_val
                final_task_status = "success" if is_task_success else "failed"

                # 5. Record sanitized HTTP response event into the trace
                sanitized_summary = {
                    "status_code": resp.status_code,
                    "mapped_status": final_task_status,
                    "raw_status": status_val,
                    "result_summary": sanitize_text(str(result_val)[:300]) if result_val is not None else None,
                    "ticket_id": ticket_id_val,
                    "error": sanitize_text(str(error_val)) if error_val is not None else None,
                    "response_keys": list(result_data.keys()),
                    "content_type": resp.headers.get("content-type", "")
                }

                if hasattr(tool_invoker, "record_http_response"):
                    tool_invoker.record_http_response(
                        action="http_response",
                        status_code=resp.status_code,
                        duration_ms=duration_ms,
                        output_data=sanitized_summary,
                        severity="info" if is_task_success else "warning"
                    )
                elif hasattr(tool_invoker, "recorder") and hasattr(tool_invoker.recorder, "record_event"):
                    tool_invoker.current_step = getattr(tool_invoker, "current_step", 0) + 1
                    tool_invoker.recorder.record_event(
                        step_index=tool_invoker.current_step,
                        event_type="http_response",
                        action_name="http_response",
                        severity="info" if is_task_success else "warning",
                        output_data=sanitized_summary,
                        duration_ms=duration_ms
                    )

                return {
                    "status": final_task_status,
                    "status_code": resp.status_code,
                    "ticket_id": ticket_id_val,
                    "disrupted": result_data.get("disrupted", not is_task_success),
                    "recovered": result_data.get("recovered", False),
                    "retries_used": result_data.get("retries_used", 0),
                    "error": error_val or (None if is_task_success else f"External agent reported status: {status_val}"),
                    "message": str(result_val or ("Completed by HTTP agent" if is_task_success else f"Task reported status: {status_val}")),
                    "raw_output": result_data,
                    "observability_level": self.observability_level
                }

        except httpx.TimeoutException as te:
            duration_ms = round((time.perf_counter() - dispatch_start_time) * 1000, 2)
            timeout_msg = f"External HTTP agent timed out after {duration_ms}ms ({type(te).__name__})"
            if hasattr(tool_invoker, "record_http_error"):
                tool_invoker.record_http_error(
                    action="http_timeout",
                    error_message=timeout_msg,
                    duration_ms=duration_ms,
                    output_data={"url": run_url, "timeout_seconds": self.read_timeout, "duration_ms": duration_ms},
                    severity="high"
                )
            elif hasattr(tool_invoker, "recorder") and hasattr(tool_invoker.recorder, "record_event"):
                tool_invoker.current_step = getattr(tool_invoker, "current_step", 0) + 1
                tool_invoker.recorder.record_event(
                    step_index=tool_invoker.current_step,
                    event_type="error",
                    action_name="http_timeout",
                    severity="high",
                    output_data={"url": run_url, "timeout_seconds": self.read_timeout, "duration_ms": duration_ms},
                    duration_ms=duration_ms,
                    error_message=timeout_msg
                )

            tool_invoker.record_decision(
                action="http_timeout",
                reasoning=f"External HTTP agent timed out: {str(te)}"
            )
            return {
                "status": "failed",
                "disrupted": True,
                "recovered": False,
                "error": f"HTTP Timeout contacting agent service ({type(te).__name__})",
                "message": f"External service failed to respond within configured timeout ({self.read_timeout}s)",
                "observability_level": self.observability_level
            }
        except Exception as e:
            duration_ms = round((time.perf_counter() - dispatch_start_time) * 1000, 2)
            sanitized_err = sanitize_text(str(e)) or "Unknown HTTP error"
            if self.secret_env_var:
                secret_val = os.environ.get(self.secret_env_var, "")
                if secret_val:
                    sanitized_err = sanitized_err.replace(secret_val, "[REDACTED_SECRET]")

            if hasattr(tool_invoker, "record_http_error"):
                tool_invoker.record_http_error(
                    action="http_error",
                    error_message=f"HTTP Agent adapter error: {sanitized_err}",
                    duration_ms=duration_ms,
                    output_data={"url": run_url, "error_type": type(e).__name__, "error": sanitized_err},
                    severity="high"
                )
            elif hasattr(tool_invoker, "recorder") and hasattr(tool_invoker.recorder, "record_event"):
                tool_invoker.current_step = getattr(tool_invoker, "current_step", 0) + 1
                tool_invoker.recorder.record_event(
                    step_index=tool_invoker.current_step,
                    event_type="error",
                    action_name="http_error",
                    severity="high",
                    output_data={"url": run_url, "error_type": type(e).__name__, "error": sanitized_err},
                    duration_ms=duration_ms,
                    error_message=f"HTTP Agent adapter error: {sanitized_err}"
                )

            tool_invoker.record_decision(
                action="http_error",
                reasoning=f"HTTP Agent adapter error: {sanitized_err}"
            )
            return {
                "status": "failed",
                "disrupted": True,
                "recovered": False,
                "error": sanitized_err,
                "message": f"HTTP Agent call failed: {sanitized_err}",
                "observability_level": self.observability_level
            }

    def cancel(self) -> None:
        pass

    def dispose(self) -> None:
        pass
