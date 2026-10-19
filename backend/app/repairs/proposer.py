import uuid
from typing import Any
from app.repairs.templates import REPAIR_TEMPLATES

class RepairProposer:
    """
    Constructs concrete repair proposals from diagnoses and pre-defined patch templates.
    """
    def create_proposal_for_diagnosis(
        self,
        diagnosis_id: str,
        run_id: str,
        target_agent_id: str,
        base_version: str,
        template_id: str | None = None
    ) -> dict[str, Any]:
        tid = template_id or "TEMPLATE_IDEMPOTENCY_CHECK"
        template = REPAIR_TEMPLATES.get(tid, REPAIR_TEMPLATES["TEMPLATE_IDEMPOTENCY_CHECK"])

        candidate_version_tag = f"{base_version}-patch-{uuid.uuid4().hex[:6]}"

        return {
            "id": f"PROP-{uuid.uuid4().hex[:10]}",
            "diagnosis_id": diagnosis_id,
            "run_id": run_id,
            "template_id": template["id"],
            "title": template["title"],
            "proposed_change": template["proposed_change"],
            "rationale": template["rationale"],
            "expected_benefit": template["expected_benefit"],
            "potential_risks": template["potential_risks"],
            "patch_diff": template["patch_diff"],
            "target_agent_id": target_agent_id,
            "base_version": base_version,
            "candidate_version_tag": candidate_version_tag,
            "candidate_strategy": template["candidate_strategy"],
            "candidate_config": template["candidate_config"],
            "approval_status": "pending",
            "verification_status": "unverified",
            "verification_summary": {}
        }

repair_proposer = RepairProposer()
