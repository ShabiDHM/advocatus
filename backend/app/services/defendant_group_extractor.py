# FILE: backend/app/services/defendant_group_extractor.py
# PHOENIX PROTOCOL - DEFENDANT GROUP EXTRACTOR V1.4
# V1.4: document_ids filter — extract defendants from specific documents only.

import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from bson import ObjectId

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# REGEX PATTERNS
# ────────────────────────────────────────────────────────────────────────────

GROUP_HEADER_PATTERN = re.compile(
    r'^GRUPI\s+([IVX]+)\s*:\s*(.+?)\s*$',
    re.MULTILINE
)

GROUP_SUBTITLE_PATTERN = re.compile(
    r'^\((.+?)\)\s*$',
    re.MULTILINE
)

DEFENDANT_LINE_PATTERN = re.compile(
    r'^(\d{1,3})\.\s+(.+?)\s*[—\-:]\s*(.+?)\s*$',
    re.MULTILINE
)

UPPERCASE_NAME_PATTERN = re.compile(r'^[A-ZËÇ\s\.\-]+$')

LOWERCASE_WORDS = {
    "i", "e", "të", "së", "nga", "me", "pa", "në", "dhe", "ose",
    "a", "te", "se", "ne", "qe",
}

TITLE_NORMALIZATION = {
    "dr": "Dr.", "dr.": "Dr.",
    "prof": "Prof.", "prof.": "Prof.",
    "mr": "Mr.", "mr.": "Mr.",
    "m.sc": "M.Sc.", "m.sc.": "M.Sc.",
    "msc": "M.Sc.", "msc.": "M.Sc.",
    "znj": "Znj.", "znj.": "Znj.",
    "z": "Z.", "z.": "Z.",
}

INSTITUTION_KEYWORDS = {
    "kolegji", "kolegj", "gjykata", "prokuroria",
    "inspektorati", "komisioni", "zyra", "ministria",
    "departamenti", "qendra", "odës", "oda",
}

KNOWN_ACRONYMS = {
    "QKUK", "OMK", "PSRK", "KGJK", "IPFK", "ZMV", "QPS",
    "KPPRK", "KPRK", "LPK", "LMD", "EULEX", "OKB", "KEDNJ",
    "KE", "PML", "PP", "CA",
}


# ────────────────────────────────────────────────────────────────────────────
# SERVICE
# ────────────────────────────────────────────────────────────────────────────

class DefendantGroupExtractor:
    """
    V1.4 — document_ids support.
    """

    def __init__(self, db):
        self.db = db

    # ────────────────────────────────────────────────────────────────────
    # PUBLIC
    # ────────────────────────────────────────────────────────────────────

    def extract_for_case(
        self,
        case_id: str,
        force: bool = False,
        document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Nxjerr grupet e të pandehurve për një lëndë dhe i ruan në DB.

        Args:
            case_id: ID e lëndës
            force: Nëse True, ri-ekstrakton edhe nëse ekziston
            document_ids: Nëse jepet, skanohen VETËM këto dokumente
        """
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id

        case_doc = self.db.cases.find_one({"_id": case_oid})
        if not case_doc:
            logger.warning(f"⚠️ [DEF_EXTRACT] Case {case_id} not found")
            return []

        # Nëse nuk kërkohet force DHE nuk ka document_ids filter → përdor cache
        existing = case_doc.get("defendants_groups") or []
        if existing and not force and not document_ids:
            logger.info(
                f"✅ [DEF_EXTRACT] Using existing groups for case {case_id} "
                f"({len(existing)} groups)"
            )
            return existing

        source_text, source_doc_id, source_file_name = self._find_source_document(
            case_id, case_oid, document_ids=document_ids
        )

        if not source_text:
            logger.info(
                f"ℹ️ [DEF_EXTRACT] No source document found for case {case_id} "
                f"(docs={document_ids or 'ALL'})"
            )
            return []

        groups = self._parse_groups(source_text)

        if not groups:
            logger.info(f"ℹ️ [DEF_EXTRACT] No groups parsed from {source_file_name}")
            return []

        # Ruaj në DB vetëm nëse nuk ka document_ids filter (case-scope)
        if not document_ids:
            self._save_groups(case_oid, groups, source_doc_id, source_file_name)

        total_defendants = sum(len(g.get("defendants", [])) for g in groups)
        logger.info(
            f"✅ [DEF_EXTRACT] Extracted {len(groups)} groups, "
            f"{total_defendants} defendants from {source_file_name} "
            f"for case {case_id}"
        )

        return groups

    # ────────────────────────────────────────────────────────────────────
    # FIND SOURCE
    # ────────────────────────────────────────────────────────────────────

    def _find_source_document(
        self,
        case_id: str,
        case_oid: Any,
        document_ids: Optional[List[str]] = None,
    ) -> Tuple[str, Optional[str], Optional[str]]:
        candidates: List[Tuple[int, str, str, str]] = []

        try:
            query: Dict[str, Any] = {
                "$or": [
                    {"case_id": case_id},
                    {"case_id": case_oid},
                    {"case_id": str(case_oid)},
                ],
                "status": {"$ne": "DELETED"},
            }

            # V1.4: filtro vetëm dokumentet e kërkuara
            if document_ids:
                doc_oids = [ObjectId(d) for d in document_ids if ObjectId.is_valid(d)]
                doc_strs = [str(d) for d in document_ids]
                query["_id"] = {"$in": doc_oids + doc_strs}

            cursor = self.db.documents.find(
                query,
                {
                    "_id": 1,
                    "file_name": 1,
                    "content": 1,
                    "extracted_text": 1,
                    "text": 1,
                },
            )

            for doc in cursor:
                text = (
                    doc.get("content")
                    or doc.get("extracted_text")
                    or doc.get("text")
                    or ""
                )
                if not text:
                    continue

                if re.search(r'GRUPI\s+[IVX]+\s*:', text, re.IGNORECASE):
                    candidates.append((
                        len(text),
                        text,
                        str(doc["_id"]),
                        doc.get("file_name", "unknown"),
                    ))

        except Exception as e:
            logger.error(f"❌ [DEF_EXTRACT] find_source_document failed: {e}")
            return "", None, None

        if not candidates:
            return "", None, None

        candidates.sort(key=lambda x: x[0], reverse=True)
        _, text, doc_id, file_name = candidates[0]
        return text, doc_id, file_name

    # ────────────────────────────────────────────────────────────────────
    # PARSE GROUPS
    # ────────────────────────────────────────────────────────────────────

    def _parse_groups(self, text: str) -> List[Dict[str, Any]]:
        group_matches = list(GROUP_HEADER_PATTERN.finditer(text))
        if not group_matches:
            return []

        groups: List[Dict[str, Any]] = []

        for i, match in enumerate(group_matches):
            group_key = match.group(1).strip().upper()
            group_title = self._normalize_title_casing(match.group(2).strip())

            start = match.end()
            end = group_matches[i + 1].start() if i + 1 < len(group_matches) else len(text)
            section = text[start:end]

            subtitle = ""
            sub_match = GROUP_SUBTITLE_PATTERN.search(section)
            if sub_match:
                subtitle = sub_match.group(1).strip()

            defendants = self._parse_defendants(section)

            if not defendants:
                continue

            groups.append({
                "group": group_key,
                "title": group_title,
                "subtitle": subtitle,
                "defendants": defendants,
            })

        return groups

    def _parse_defendants(self, section: str) -> List[Dict[str, str]]:
        defendants: List[Dict[str, str]] = []
        seen_numbers: set = set()

        for match in DEFENDANT_LINE_PATTERN.finditer(section):
            number = match.group(1).strip()
            raw_name = match.group(2).strip()
            raw_role = match.group(3).strip()

            if number in seen_numbers:
                continue

            if not self._looks_like_defendant(raw_name, raw_role):
                continue

            expanded = self._expand_multi_defendant(number, raw_name, raw_role)

            for entry in expanded:
                seen_numbers.add(entry["number"])
                defendants.append(entry)

        defendants.sort(key=self._sort_key)
        return defendants

    def _sort_key(self, d: Dict[str, str]) -> Tuple[int, int, str]:
        num_str = d.get("number", "").strip()
        try:
            if "." in num_str:
                major, minor = num_str.split(".", 1)
                return (int(major), int(minor), d.get("name", ""))
            else:
                return (int(num_str), 0, d.get("name", ""))
        except (ValueError, AttributeError):
            return (999, 999, d.get("name", ""))

    # ────────────────────────────────────────────────────────────────────
    # EXPAND MULTI-DEFENDANT
    # ────────────────────────────────────────────────────────────────────

    def _expand_multi_defendant(
        self,
        number: str,
        name: str,
        role: str,
    ) -> List[Dict[str, str]]:
        name_lower = name.lower()
        name_is_institution = any(kw in name_lower for kw in INSTITUTION_KEYWORDS)

        role_parts = [p.strip() for p in role.split(",") if p.strip()]

        if name_is_institution and len(role_parts) > 1:
            looks_like_names = all(
                len(p.split()) >= 2 and len(p) >= 5
                for p in role_parts
            )

            if looks_like_names:
                institution_clean = self._normalize_title_casing(name)

                expanded: List[Dict[str, str]] = []
                for idx, person_name in enumerate(role_parts, start=1):
                    normalized_person = self._normalize_name(person_name)
                    role_for_person = f"Anëtar i {institution_clean}"

                    if "kolegj" in name_lower and "apelit" in name_lower:
                        role_for_person = "Gjyqtar i Kolegjit të Gjykatës së Apelit"
                    elif "kolegj" in name_lower and "suprem" in name_lower:
                        role_for_person = "Gjyqtar i Kolegjit të Gjykatës Supreme"
                    elif "kolegj" in name_lower and "kushtetues" in name_lower:
                        role_for_person = "Gjyqtar i Kolegjit Kushtetues"

                    expanded.append({
                        "number": f"{number}.{idx}",
                        "name": normalized_person,
                        "role": role_for_person,
                    })

                logger.info(
                    f"🔗 [DEF_EXTRACT] Expanded '{name}' → "
                    f"{len(expanded)} individual defendants"
                )
                return expanded

        return [{
            "number": number,
            "name": self._normalize_name(name),
            "role": self._normalize_role(role),
        }]

    # ────────────────────────────────────────────────────────────────────
    # VALIDATION
    # ────────────────────────────────────────────────────────────────────

    def _looks_like_defendant(self, name: str, role: str) -> bool:
        if len(name) < 3 or len(role) < 3:
            return False

        blacklist = [
            "neni", "neneve", "ligji", "paragrafi", "pika",
            "faqe", "shkresa", "prova", "kualifikimi",
        ]
        name_lower = name.lower()
        if any(kw in name_lower for kw in blacklist):
            return False

        if not re.search(r'[A-ZËÇ]', name):
            return False

        return True

    # ────────────────────────────────────────────────────────────────────
    # SMART CASING
    # ────────────────────────────────────────────────────────────────────

    def _normalize_name(self, name: str) -> str:
        name = " ".join(name.split()).strip(".,;:")
        words = name.split()
        normalized: List[str] = []

        for w in words:
            w_clean = w.strip(".,")
            w_lower = w_clean.lower()

            if w_lower in TITLE_NORMALIZATION:
                normalized.append(TITLE_NORMALIZATION[w_lower])
                continue

            if w_lower in LOWERCASE_WORDS:
                normalized.append(w_lower)
                continue

            if w_clean.upper() in KNOWN_ACRONYMS:
                normalized.append(w_clean.upper())
                continue

            if w_clean:
                normalized.append(w_clean[0].upper() + w_clean[1:].lower())

        return " ".join(normalized)

    def _normalize_role(self, role: str) -> str:
        role = " ".join(role.split()).strip(".,;:")
        if not role:
            return role

        words = role.split()
        normalized: List[str] = []

        for w in words:
            w_clean = w.strip(".,")
            w_lower = w_clean.lower()

            if w_lower in LOWERCASE_WORDS:
                normalized.append(w_lower)
                continue

            if w_lower in TITLE_NORMALIZATION:
                normalized.append(TITLE_NORMALIZATION[w_lower])
                continue

            normalized.append(w)

        result = " ".join(normalized)

        for lower_word in LOWERCASE_WORDS:
            upper = lower_word.upper()
            result = re.sub(rf'\b{upper}\b', lower_word, result)

        return result[:300]

    def _normalize_title_casing(self, text: str) -> str:
        if not text:
            return text

        text = " ".join(text.split()).strip()

        letters = [c for c in text if c.isalpha()]
        if not letters:
            return text

        upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)

        if upper_ratio > 0.7:
            words = text.split()
            normalized: List[str] = []

            for i, w in enumerate(words):
                if "-" in w:
                    parts = w.split("-")
                    processed_parts: List[str] = []

                    for j, part in enumerate(parts):
                        part_clean = part.strip(".,")
                        part_upper = part_clean.upper()

                        if part_upper in KNOWN_ACRONYMS:
                            processed_parts.append(part_clean.upper())
                            continue

                        if j > 0 and part_clean:
                            processed_parts.append(part_clean.lower())
                            continue

                        if part_clean:
                            processed_parts.append(
                                part_clean[0].upper() + part_clean[1:].lower()
                            )

                    normalized.append("-".join(processed_parts))
                    continue

                w_clean = w.strip(".,")
                w_lower = w_clean.lower()

                if w_clean.upper() in KNOWN_ACRONYMS:
                    normalized.append(w_clean.upper())
                    continue

                if w_lower in LOWERCASE_WORDS and i > 0:
                    normalized.append(w_lower)
                    continue

                if w_clean:
                    normalized.append(w_clean[0].upper() + w_clean[1:].lower())

            return " ".join(normalized)

        return self._normalize_role(text)

    # ────────────────────────────────────────────────────────────────────
    # SAVE
    # ────────────────────────────────────────────────────────────────────

    def _save_groups(
        self,
        case_oid: Any,
        groups: List[Dict[str, Any]],
        source_doc_id: Optional[str],
        source_file_name: Optional[str],
    ) -> None:
        try:
            self.db.cases.update_one(
                {"_id": case_oid},
                {
                    "$set": {
                        "defendants_groups": groups,
                        "defendants_groups_meta": {
                            "source_document_id": source_doc_id,
                            "source_file_name": source_file_name,
                            "extracted_at": datetime.now(timezone.utc).isoformat(),
                            "total_groups": len(groups),
                            "total_defendants": sum(
                                len(g.get("defendants", [])) for g in groups
                            ),
                        },
                    }
                },
            )
        except Exception as e:
            logger.error(f"❌ [DEF_EXTRACT] save_groups failed: {e}")
            raise


# ────────────────────────────────────────────────────────────────────────────
# FACTORY
# ────────────────────────────────────────────────────────────────────────────

def get_defendant_group_extractor(db: Any) -> DefendantGroupExtractor:
    return DefendantGroupExtractor(db)