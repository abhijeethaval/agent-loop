"""Audit logging for observability and compliance.

Each decision step persists: input snapshot, DSPy outputs, rationale, tool/HITL outcomes.
Enables deterministic replay, regression testing, and compliance audits.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class AuditEntry:
    """A single audit log entry."""
    
    def __init__(
        self,
        step: int,
        timestamp: str,
        input_snapshot: dict[str, Any],
        decision_output: dict[str, Any],
        outcome: dict[str, Any] | None = None,
    ):
        """Initialize audit entry.
        
        Args:
            step: Step number in the loop
            timestamp: ISO format timestamp
            input_snapshot: State snapshot at decision time
            decision_output: DSPy decision output
            outcome: Tool or HITL outcome if applicable
        """
        self.step = step
        self.timestamp = timestamp
        self.input_snapshot = input_snapshot
        self.decision_output = decision_output
        self.outcome = outcome
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step": self.step,
            "timestamp": self.timestamp,
            "input_snapshot": self.input_snapshot,
            "decision_output": self.decision_output,
            "outcome": self.outcome,
        }


class AuditLogger:
    """Logger for persisting audit trail.
    
    Supports file-based logging for compliance and replay.
    """
    
    def __init__(
        self,
        log_dir: Path | str | None = None,
        session_id: str | None = None,
    ):
        """Initialize audit logger.
        
        Args:
            log_dir: Directory to store audit logs (None for in-memory only)
            session_id: Unique session identifier
        """
        self._log_dir = Path(log_dir) if log_dir else None
        self._session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self._entries: list[AuditEntry] = []
        
        if self._log_dir:
            self._log_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def session_id(self) -> str:
        """Get the session ID."""
        return self._session_id
    
    @property
    def entries(self) -> list[AuditEntry]:
        """Get all audit entries."""
        return self._entries.copy()
    
    def log_decision(
        self,
        step: int,
        goal: str,
        history: list[dict],
        policy_context: dict[str, str],
        decision_type: str,
        decision_details: dict[str, Any],
        rationale: str,
    ) -> AuditEntry:
        """Log a decision step.
        
        Args:
            step: Step number
            goal: Current goal
            history: Current history
            policy_context: Policy context snapshot
            decision_type: Type of decision (tool/hitl/final)
            decision_details: Decision-specific details
            rationale: Reasoning for the decision
            
        Returns:
            The created audit entry
        """
        entry = AuditEntry(
            step=step,
            timestamp=datetime.now().isoformat(),
            input_snapshot={
                "goal": goal,
                "history_length": len(history),
                "policy_context": policy_context,
            },
            decision_output={
                "decision_type": decision_type,
                "rationale": rationale,
                **decision_details,
            },
        )
        self._entries.append(entry)
        self._persist_entry(entry)
        return entry
    
    def log_outcome(
        self,
        step: int,
        outcome_type: str,
        status: str,
        result: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Log the outcome of an action.
        
        Args:
            step: Step number this outcome belongs to
            outcome_type: Type of outcome (tool/hitl)
            status: Status (success/error/feedback)
            result: Result message
            data: Additional data
        """
        # Find the entry for this step and update outcome
        for entry in reversed(self._entries):
            if entry.step == step:
                entry.outcome = {
                    "type": outcome_type,
                    "status": status,
                    "result": result,
                    "data": data,
                }
                self._persist_entry(entry, update=True)
                break
    
    def _persist_entry(self, entry: AuditEntry, update: bool = False) -> None:
        """Persist entry to file if log_dir is configured."""
        if not self._log_dir:
            return
        
        log_file = self._log_dir / f"session_{self._session_id}.jsonl"
        
        if update:
            # Re-write the entire log for updates (simple approach)
            self._persist_all()
        else:
            # Append new entry
            with open(log_file, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
    
    def _persist_all(self) -> None:
        """Persist all entries to file."""
        if not self._log_dir:
            return
        
        log_file = self._log_dir / f"session_{self._session_id}.jsonl"
        with open(log_file, "w") as f:
            for entry in self._entries:
                f.write(json.dumps(entry.to_dict()) + "\n")
    
    def export_session(self) -> dict[str, Any]:
        """Export the entire session as a dictionary.
        
        Returns:
            Dictionary containing session ID and all entries
        """
        return {
            "session_id": self._session_id,
            "entries": [e.to_dict() for e in self._entries],
        }
    
    @classmethod
    def load_session(cls, log_file: Path | str) -> "AuditLogger":
        """Load a session from a log file.
        
        Args:
            log_file: Path to the JSONL log file
            
        Returns:
            AuditLogger with loaded entries
        """
        log_file = Path(log_file)
        logger = cls(log_dir=log_file.parent)
        
        with open(log_file) as f:
            for line in f:
                data = json.loads(line)
                entry = AuditEntry(
                    step=data["step"],
                    timestamp=data["timestamp"],
                    input_snapshot=data["input_snapshot"],
                    decision_output=data["decision_output"],
                    outcome=data.get("outcome"),
                )
                logger._entries.append(entry)
        
        return logger
