"""
.bottle Protocol — Unified Cross-Repo Communication

Replaces the current chaos of ad-hoc bottles, .nail files, and vector DBs.
One format, one parser, all repos speak the same language.

Message format (YAML, human readable):
---
apiVersion: bottle/v1
kind: observation | hypothesis | experiment | result | command | config
source: repo_name/agent_name
timestamp: 2026-06-03T20:00:00Z
bottle_id: <blake2b-16char>
payload:
  # Varies by kind
metadata:
  confidence: 0.0-1.0
  tags: [list, of, tags]
  references: [list, of, related, bottle_ids]
---

See ARCHITECTURE-V2.md §2 "Cross-Repo Communication Protocol" for full design.
"""

import yaml
import hashlib
import os
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Any, Dict

API_VERSION = "bottle/v1"

VALID_KINDS = {"observation", "hypothesis", "experiment", "result", "command", "config"}


@dataclass
class Bottle:
    """
    A typed message envelope for cross-repo agent communication.

    Bottles are YAML files stored in git repos (e.g. captains-log/i2i/).
    They replace ad-hoc markdown bottles with a machine-parseable format
    while staying git-native and human-readable.
    """

    kind: str  # observation, hypothesis, experiment, result, command, config
    source: str  # "repo_name/agent_name"
    payload: Dict[str, Any]
    confidence: float = 0.5
    tags: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    timestamp: str = ""
    bottle_id: str = ""

    def __post_init__(self):
        if self.kind not in VALID_KINDS:
            raise ValueError(f"Invalid kind '{self.kind}'. Must be one of {VALID_KINDS}")
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.bottle_id:
            content = f"{self.kind}:{self.source}:{self.timestamp}"
            self.bottle_id = hashlib.blake2b(content.encode(), digest_size=8).hexdigest()

    def to_yaml(self) -> str:
        """Serialize bottle to YAML string."""
        data = {
            "apiVersion": API_VERSION,
            "kind": self.kind,
            "source": self.source,
            "timestamp": self.timestamp,
            "bottle_id": self.bottle_id,
            "payload": self.payload,
            "metadata": {
                "confidence": self.confidence,
                "tags": self.tags,
                "references": self.references,
            },
        }
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    def to_dict(self) -> dict:
        """Serialize bottle to plain dict."""
        return asdict(self)

    def save(self, directory: str) -> str:
        """Save bottle to a directory as a YAML file.

        Returns the path written.
        """
        os.makedirs(directory, exist_ok=True)
        filename = f"BOTTLE-{self.kind}-{self.bottle_id}.yaml"
        path = os.path.join(directory, filename)
        with open(path, "w") as f:
            f.write(self.to_yaml())
        return path

    # -- Class methods for loading --

    @classmethod
    def from_yaml(cls, text: str) -> "Bottle":
        """Deserialize a bottle from a YAML string."""
        data = yaml.safe_load(text)
        if isinstance(data, dict) and "metadata" in data:
            # New format with metadata key
            metadata = data.pop("metadata", {})
            return cls(
                kind=data.get("kind", "observation"),
                source=data.get("source", "unknown"),
                payload=data.get("payload", {}),
                confidence=metadata.get("confidence", 0.5),
                tags=metadata.get("tags", []),
                references=metadata.get("references", []),
                timestamp=data.get("timestamp", ""),
                bottle_id=data.get("bottle_id", ""),
            )
        # Fallback: flat dict (from to_dict)
        return cls(
            kind=data.get("kind", "observation"),
            source=data.get("source", "unknown"),
            payload=data.get("payload", {}),
            confidence=data.get("confidence", 0.5),
            tags=data.get("tags", []),
            references=data.get("references", []),
            timestamp=data.get("timestamp", ""),
            bottle_id=data.get("bottle_id", ""),
        )

    @classmethod
    def from_file(cls, path: str) -> "Bottle":
        """Load a bottle from a YAML file."""
        with open(path) as f:
            return cls.from_yaml(f.read())

    @classmethod
    def load_directory(cls, directory: str) -> List["Bottle"]:
        """Load all bottles from a directory."""
        bottles: List["Bottle"] = []
        if not os.path.exists(directory):
            return bottles
        for fname in sorted(os.listdir(directory)):
            if fname.startswith("BOTTLE-") and fname.endswith(".yaml"):
                try:
                    bottles.append(cls.from_file(os.path.join(directory, fname)))
                except Exception as e:
                    print(f"Warning: failed to load {fname}: {e}")
        return bottles


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------


def observe(
    source: str,
    what: str,
    data: dict = None,
    confidence: float = 0.5,
    tags: list = None,
) -> Bottle:
    """Create an observation bottle."""
    return Bottle(
        kind="observation",
        source=source,
        payload={"what": what, **(data or {})},
        confidence=confidence,
        tags=tags or ["observation"],
    )


def hypothesize(
    source: str,
    hypothesis: str,
    evidence: list = None,
    confidence: float = 0.3,
) -> Bottle:
    """Create a hypothesis bottle."""
    return Bottle(
        kind="hypothesis",
        source=source,
        payload={"hypothesis": hypothesis, "evidence": evidence or []},
        confidence=confidence,
        tags=["hypothesis"],
    )


def experiment(
    source: str,
    design: str,
    expected: str,
    method: str = "",
) -> Bottle:
    """Create an experiment bottle."""
    return Bottle(
        kind="experiment",
        source=source,
        payload={"design": design, "expected_result": expected, "method": method},
        confidence=0.5,
        tags=["experiment"],
    )


def result(
    source: str,
    experiment_id: str,
    outcome: str,
    data: dict = None,
    confidence: float = 0.8,
) -> Bottle:
    """Create a result bottle."""
    return Bottle(
        kind="result",
        source=source,
        payload={"experiment_id": experiment_id, "outcome": outcome, **(data or {})},
        confidence=confidence,
        tags=["result"],
        references=[experiment_id],
    )


def command(
    source: str,
    action: str,
    target: str,
    params: dict = None,
) -> Bottle:
    """Create a command bottle (agent-to-agent)."""
    return Bottle(
        kind="command",
        source=source,
        payload={"action": action, "target": target, "params": params or {}},
        confidence=1.0,
        tags=["command", action],
    )


def config_change(
    source: str,
    setting: str,
    old_value: Any,
    new_value: Any,
    reason: str,
) -> Bottle:
    """Create a config change proposal bottle."""
    return Bottle(
        kind="config",
        source=source,
        payload={"setting": setting, "old": old_value, "new": new_value, "reason": reason},
        confidence=0.5,
        tags=["config", "proposal"],
    )
