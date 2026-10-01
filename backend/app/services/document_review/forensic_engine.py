# FILE: backend/app/services/document_review/forensic_engine.py
# PHOENIX PROTOCOL - FORENSIC ENGINE V1.3
# V1.3: PROFESSIONAL LANGUAGE — Logger messages kaluan nga "flamuj" →
#       "konstatime" për konsistencë me forensic_service.py V1.3 dhe
#       PROFESSIONAL_LANGUAGE_RULE. Zero ndryshim funksional.
# V1.2 (FIX P2): _detect_age_threshold() dedup — një flag për case_number
#       unik, të gjitha dosjet mblidhen në evidence.files.
# V1.1: Shtuar keyword_absence, multi_event_same_date, self_reference.
# V1.0: Versioni fillestar.
#
# Motor detektimi me primitive GJENERIKE. Zero hardcoding rasti.
#
# PRIMITIVES:
#   - duplicate_value        → vlerë e njëjtë në N dokumente
#   - age_threshold          → vlerë datë > N vjet
#   - numeric_conflict       → vlera numerike kontradiktore
#   - keyword_absence        → fjalë kyçe të detyrueshme mungojnë
#   - multi_event_same_date  → >N evente në një datë
#   - self_reference         → own case number citohet si i huaj (placeholder)
#   - role_conflict          → role të ndryshme (placeholder)

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .forensic_extractor import DocumentForensicData

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent / "data" / "forensic_rules.json"


# ═══════════════════════════════════════════════════════════════════════════
# FLAG
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ForensicFlag:
    rule_id: str
    severity: str
    message: str
    legal_basis: str
    recommended_action: str
    evidence: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "legal_basis": self.legal_basis,
            "recommended_action": self.recommended_action,
            "evidence": self.evidence,
        }


# ═══════════════════════════════════════════════════════════════════════════
# CONFIG LOADER
# ═══════════════════════════════════════════════════════════════════════════

def load_forensic_config() -> Dict[str, Any]:
    if not _CONFIG_PATH.exists():
        logger.warning(f"⚠️ [FORENSIC] {_CONFIG_PATH} mungon.")
        return {"rules": [], "profiles": {}}
    try:
        with _CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(
            f"✅ [FORENSIC] Konfigurimi: {len(data.get('rules', []))} rregulla, "
            f"{len(data.get('profiles', {}))} profile."
        )
        return data
    except Exception as e:
        logger.error(f"❌ [FORENSIC] Config error: {e}")
        return {"rules": [], "profiles": {}}


def _resolve_active_rules(
    config: Dict[str, Any],
    profile_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    all_rules = {r.get("id"): r for r in config.get("rules", [])}

    if profile_name and profile_name in config.get("profiles", {}):
        profile = config["profiles"][profile_name]
        active_ids = profile.get("active_rules", [])
        resolved = [all_rules[rid] for rid in active_ids if rid in all_rules]
        logger.info(
            f"📋 [FORENSIC] Profili '{profile_name}' ({profile.get('label')}): "
            f"{len(resolved)} rregulla aktive."
        )
        return resolved

    return [r for r in config.get("rules", []) if r.get("enabled", True)]


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _format_template(template: str, **kwargs: Any) -> str:
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


def _get_field_values(doc: DocumentForensicData, field_name: str) -> List[Any]:
    val = getattr(doc, field_name, None)
    if val is None:
        return []
    if isinstance(val, (set, list, tuple)):
        return list(val)
    return [val]


def _match_doc_filter(doc: DocumentForensicData, doc_filter: Dict[str, Any]) -> bool:
    hints_required = doc_filter.get("doc_type_hints", [])
    if hints_required:
        if not any(h in doc.doc_type_hints for h in hints_required):
            return False
    return True


_RE_WORD_RE = re.compile(r'[a-zA-ZëçËÇ]{4,}', re.UNICODE)


def _context_roots(ctx: str, prefix_len: int = 4) -> Set[str]:
    words = _RE_WORD_RE.findall(ctx.lower())
    return {w[:prefix_len] for w in words if len(w) >= 4}


# ═══════════════════════════════════════════════════════════════════════════
# PRIMITIVE: duplicate_value
# ═══════════════════════════════════════════════════════════════════════════

def _detect_duplicate_value(
    structures: List[DocumentForensicData],
    rule: Dict[str, Any],
) -> List[ForensicFlag]:
    field_name = rule.get("field")
    if not field_name:
        return []

    min_occ = int(rule.get("min_occurrences", 2))
    filter_doc_type = rule.get("filter_by_doc_type")

    value_map: Dict[str, List[str]] = defaultdict(list)
    for doc in structures:
        if filter_doc_type and filter_doc_type not in doc.doc_type_hints:
            continue
        for v in _get_field_values(doc, field_name):
            if v is None:
                continue
            value_map[str(v)].append(doc.file_name)

    flags: List[ForensicFlag] = []
    for value, files in value_map.items():
        unique_files = sorted(set(files))
        if len(unique_files) < min_occ:
            continue
        message = _format_template(
            rule.get("message_template", "Vlerë e përsëritur: {value}"),
            value=value, count=len(unique_files),
            files=", ".join(unique_files),
        )
        flags.append(ForensicFlag(
            rule_id=rule.get("id", "?"),
            severity=rule.get("severity", "medium"),
            message=message,
            legal_basis=rule.get("legal_basis", ""),
            recommended_action=rule.get("recommended_action", ""),
            evidence=[{"value": value, "files": unique_files}],
        ))
    return flags


# ═══════════════════════════════════════════════════════════════════════════
# PRIMITIVE: age_threshold (V1.2: dedup)
# ═══════════════════════════════════════════════════════════════════════════

def _detect_age_threshold(
    structures: List[DocumentForensicData],
    rule: Dict[str, Any],
) -> List[ForensicFlag]:
    field_name = rule.get("field")
    prefix_filter = set(rule.get("prefix_filter", []))
    max_age = float(rule.get("max_age_years", 5))

    if not field_name:
        return []

    all_latest = [d.latest_date for d in structures if d.latest_date]
    if not all_latest:
        return []
    try:
        ref_date = date.fromisoformat(max(all_latest))
    except ValueError:
        return []

    # V1.2: dedup — grumbullo dosjet sipas case_number
    by_case: Dict[str, Dict[str, Any]] = {}

    for doc in structures:
        for case_val in _get_field_values(doc, field_name):
            case_str = str(case_val)
            m = re.match(r'([A-Z]+)\.nr\.\d+/(\d{4})', case_str)
            if not m:
                continue
            prefix = m.group(1)
            year = int(m.group(2))
            if prefix_filter and prefix not in prefix_filter:
                continue
            try:
                case_date = date(year, 1, 1)
            except ValueError:
                continue
            years = (ref_date - case_date).days / 365.25
            if years < max_age:
                continue

            entry = by_case.setdefault(case_str, {
                "year": year,
                "years": years,
                "files": [],
            })
            if doc.file_name not in entry["files"]:
                entry["files"].append(doc.file_name)

    flags: List[ForensicFlag] = []
    for case_str, entry in by_case.items():
        message = _format_template(
            rule.get("message_template", "Lënda '{value}' është {years} vjet e vjetër."),
            value=case_str,
            years=round(entry["years"], 1),
            reference_date=ref_date.isoformat(),
        )
        flags.append(ForensicFlag(
            rule_id=rule.get("id", "?"),
            severity=rule.get("severity", "medium"),
            message=message,
            legal_basis=rule.get("legal_basis", ""),
            recommended_action=rule.get("recommended_action", ""),
            evidence=[{
                "case_number": case_str,
                "year": entry["year"],
                "years_elapsed": round(entry["years"], 1),
                "reference_date": ref_date.isoformat(),
                "files": entry["files"],
            }],
        ))
    return flags


# ═══════════════════════════════════════════════════════════════════════════
# PRIMITIVE: numeric_conflict
# ═══════════════════════════════════════════════════════════════════════════

def _detect_numeric_conflict(
    structures: List[DocumentForensicData],
    rule: Dict[str, Any],
) -> List[ForensicFlag]:
    field_name = rule.get("field", "numeric_claims")
    unit_filter = set(rule.get("unit_filter", []))
    min_shared = int(rule.get("min_context_shared", 2))

    by_unit: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for doc in structures:
        claims = getattr(doc, field_name, []) or []
        for c in claims:
            unit = getattr(c, "unit", None)
            if unit_filter and unit not in unit_filter:
                continue
            by_unit[unit].append({
                "value": getattr(c, "value", None),
                "file": doc.file_name,
                "roots": _context_roots(getattr(c, "context", "")),
                "context": getattr(c, "context", ""),
            })

    flags: List[ForensicFlag] = []
    for unit, items in by_unit.items():
        if len(items) < 2:
            continue
        unique_values = sorted(set(it["value"] for it in items))
        if len(unique_values) <= 1:
            continue

        # Vetëm konflikti i parë për unit — shmang noise kur ka shumë palë.
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                shared = items[i]["roots"] & items[j]["roots"]
                if len(shared) < min_shared:
                    continue
                if items[i]["value"] == items[j]["value"]:
                    continue
                message = _format_template(
                    rule.get("message_template", "Vlera kontradiktore: {values}"),
                    unit=unit,
                    values=f"{items[i]['value']} vs {items[j]['value']}",
                )
                flags.append(ForensicFlag(
                    rule_id=rule.get("id", "?"),
                    severity=rule.get("severity", "medium"),
                    message=message,
                    legal_basis=rule.get("legal_basis", ""),
                    recommended_action=rule.get("recommended_action", ""),
                    evidence=[
                        {"value": items[i]["value"], "file": items[i]["file"],
                         "context": items[i]["context"][:200]},
                        {"value": items[j]["value"], "file": items[j]["file"],
                         "context": items[j]["context"][:200]},
                        {"shared_roots": sorted(shared)[:5]},
                    ],
                ))
                return flags
    return flags


# ═══════════════════════════════════════════════════════════════════════════
# PRIMITIVE: keyword_absence
# ═══════════════════════════════════════════════════════════════════════════

def _detect_keyword_absence(
    structures: List[DocumentForensicData],
    rule: Dict[str, Any],
) -> List[ForensicFlag]:
    doc_filter = rule.get("document_filter", {})
    required_any = [k.lower() for k in rule.get("required_keywords_any", [])]
    suspicious_any = [k.lower() for k in rule.get("suspicious_keywords_any", [])]

    if not required_any:
        return []

    flags: List[ForensicFlag] = []
    for doc in structures:
        if doc_filter and not _match_doc_filter(doc, doc_filter):
            continue

        full_text = getattr(doc, "full_text", "") or ""
        text_lower = full_text.lower()

        found_required = [k for k in required_any if k in text_lower]
        if found_required:
            continue

        found_suspicious = [k for k in suspicious_any if k in text_lower]

        message = _format_template(
            rule.get("message_template", "Element i detyrueshëm mungon: {missing_required}"),
            missing_required=", ".join(required_any[:3]),
            found_suspicious=", ".join(found_suspicious[:3]) or "(asnjë)",
            file=doc.file_name,
        )
        flags.append(ForensicFlag(
            rule_id=rule.get("id", "?"),
            severity=rule.get("severity", "medium"),
            message=message,
            legal_basis=rule.get("legal_basis", ""),
            recommended_action=rule.get("recommended_action", ""),
            evidence=[{
                "file": doc.file_name,
                "missing_required": required_any,
                "found_suspicious": found_suspicious,
            }],
        ))
    return flags


# ═══════════════════════════════════════════════════════════════════════════
# PRIMITIVE: multi_event_same_date
# ═══════════════════════════════════════════════════════════════════════════

def _detect_multi_event_same_date(
    structures: List[DocumentForensicData],
    rule: Dict[str, Any],
) -> List[ForensicFlag]:
    min_events = int(rule.get("min_events", 3))

    date_map: Dict[str, Set[str]] = defaultdict(set)
    for doc in structures:
        for d in doc.dates_iso:
            date_map[d].add(doc.file_name)

    flags: List[ForensicFlag] = []
    for dt, files in date_map.items():
        if len(files) < min_events:
            continue
        message = _format_template(
            rule.get("message_template", "{count} ngjarje në të njëjtën datë: '{date}'"),
            count=len(files), date=dt,
        )
        flags.append(ForensicFlag(
            rule_id=rule.get("id", "?"),
            severity=rule.get("severity", "medium"),
            message=message,
            legal_basis=rule.get("legal_basis", ""),
            recommended_action=rule.get("recommended_action", ""),
            evidence=[{"date": dt, "files": sorted(files)}],
        ))
    return flags


# ═══════════════════════════════════════════════════════════════════════════
# PRIMITIVE: self_reference (placeholder)
# ═══════════════════════════════════════════════════════════════════════════

def _detect_self_reference(
    structures: List[DocumentForensicData],
    rule: Dict[str, Any],
) -> List[ForensicFlag]:
    return []


# ═══════════════════════════════════════════════════════════════════════════
# PRIMITIVE: role_conflict (placeholder)
# ═══════════════════════════════════════════════════════════════════════════

def _detect_role_conflict(
    structures: List[DocumentForensicData],
    rule: Dict[str, Any],
) -> List[ForensicFlag]:
    return []


# ═══════════════════════════════════════════════════════════════════════════
# DISPATCH
# ═══════════════════════════════════════════════════════════════════════════

_DETECTORS = {
    "duplicate_value": _detect_duplicate_value,
    "age_threshold": _detect_age_threshold,
    "numeric_conflict": _detect_numeric_conflict,
    "keyword_absence": _detect_keyword_absence,
    "multi_event_same_date": _detect_multi_event_same_date,
    "self_reference": _detect_self_reference,
    "role_conflict": _detect_role_conflict,
}


def run_forensic_detectors(
    structures: List[DocumentForensicData],
    profile: Optional[str] = None,
) -> List[ForensicFlag]:
    config = load_forensic_config()
    rules = _resolve_active_rules(config, profile_name=profile)

    all_flags: List[ForensicFlag] = []

    for rule in rules:
        rule_type = rule.get("type")
        detector = _DETECTORS.get(rule_type)
        if not detector:
            logger.warning(
                f"⚠️ [FORENSIC] Rule '{rule.get('id')}': type '{rule_type}' "
                f"nuk ekziston. Skip."
            )
            continue

        try:
            flags = detector(structures, rule)
            all_flags.extend(flags)
            if flags:
                logger.info(
                    f"🔴 [FORENSIC] Rule '{rule.get('id')}' "
                    f"(severity={rule.get('severity')}): {len(flags)} konstatime"
                )
        except Exception as e:
            logger.error(f"❌ [FORENSIC] Rule '{rule.get('id')}' dështoi: {e}")

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_flags.sort(key=lambda f: severity_order.get(f.severity, 99))

    logger.info(
        f"✅ [FORENSIC] Total: {len(all_flags)} konstatime "
        f"(critical={sum(1 for f in all_flags if f.severity == 'critical')}, "
        f"high={sum(1 for f in all_flags if f.severity == 'high')})"
    )
    return all_flags