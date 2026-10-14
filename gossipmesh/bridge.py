"""
Cross-Repo Wire Contract & Telemetry Schema Synchronizer.
Keeps DevProxy (Go) and Spryzen (Rust) type definitions in automated lockstep.
"""

from typing import Dict, Any, List

class WireContract:
    def __init__(self, name: str, version: int, fields: Dict[str, str], source_repo: str):
        self.name = name
        self.version = version
        self.fields = fields
        self.source_repo = source_repo

    def to_go_struct(self) -> str:
        """Generates idiomatic Go struct representation."""
        lines = [f"// {self.name} (v{self.version}) - Synchronized via GossipMesh from {self.source_repo}"]
        lines.append(f"type {self.name} struct {{")
        type_map = {
            "string": "string",
            "int64": "int64",
            "uint64": "uint64",
            "float64": "float64",
            "bool": "bool",
            "bytes": "[]byte",
            "map": "map[string]string",
        }
        for field, f_type in self.fields.items():
            go_type = type_map.get(f_type, "string")
            # PascalCase field name
            pascal_name = "".join(part.capitalize() for part in field.split("_"))
            lines.append(f"\t{pascal_name} {go_type} `json:\"{field}\"`")
        lines.append("}")
        return "\n".join(lines)

    def to_rust_struct(self) -> str:
        """Generates idiomatic Rust serde struct representation."""
        lines = [
            f"/// {self.name} (v{self.version}) - Synchronized via GossipMesh from {self.source_repo}",
            "#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]",
            f"pub struct {self.name} {{"
        ]
        type_map = {
            "string": "String",
            "int64": "i64",
            "uint64": "u64",
            "float64": "f64",
            "bool": "bool",
            "bytes": "Vec<u8>",
            "map": "std::collections.HashMap<String, String>",
        }
        for field, f_type in self.fields.items():
            rust_type = type_map.get(f_type, "String")
            lines.append(f"    pub {field}: {rust_type},")
        lines.append("}")
        return "\n".join(lines)

class CrossRepoBridge:
    """Manages shared wire schemas between Go and Rust repositories."""
    def __init__(self):
        self.contracts: Dict[str, WireContract] = {}

    def register(self, name: str, version: int, fields: Dict[str, str], source_repo: str) -> WireContract:
        contract = WireContract(name, version, fields, source_repo)
        self.contracts[name] = contract
        return contract

    def get_go_definitions(self) -> str:
        return "\n\n".join(c.to_go_struct() for c in self.contracts.values())

    def get_rust_definitions(self) -> str:
        return "\n\n".join(c.to_rust_struct() for c in self.contracts.values())
