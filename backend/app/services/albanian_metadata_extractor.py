"""
Albanian Legal Metadata Extractor
Phase 1, Step 1.3: Extract legal-specific metadata from Albanian documents
"""

import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class AlbanianMetadataExtractor:
    def __init__(self):
        # Albanian legal patterns with improved regex for better matching
        self.patterns = {
            'contract_section': re.compile(r'Neni\s+(\d+\.?\d*)[:\-]\s*(.+?)(?=\n|$)', re.IGNORECASE),
            'date': re.compile(r'(\d{1,2}\s+(Janar|Shkurt|Mars|Prill|Maj|Qershor|Korrik|Gusht|Shtator|Tetor|Nëntor|Dhjetor)\s+\d{4})', re.IGNORECASE),
            'case_reference': re.compile(r'Çështja\s+(Nr\.?\s*[\w\-]+)', re.IGNORECASE),
            'party': re.compile(r'(Paditësi|Padituesi|Pale)\s*[:\-]\s*(.+?)(?=\n|$)', re.IGNORECASE),
            'document_type': re.compile(r'\b(Kontratë|Vendim|Ankesë|Apel|Dëshmi|Procesverbal|Deklaratë|Marreveshje)\b', re.IGNORECASE),
            'amount': re.compile(r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(€|EUR|euro|LEK|lek)', re.IGNORECASE),
            'court': re.compile(r'(Gjykat[aë]s?\s+(e|ë)\s+[\w\s]+)', re.IGNORECASE),
            'judge': re.compile(r'(Gjykat[aë]s(it)?\s+[\w\s]+)', re.IGNORECASE),
            'deadline': re.compile(r'(afat|deri\s+më|data\s+limit)\s*[:\-]?\s*(\d{1,2}\s+\w+\s+\d{4})', re.IGNORECASE),
            'clause': re.compile(r'(klauzol[ëa]|pika)\s+(\d+[\.\d]*)', re.IGNORECASE)
        }
        
        # Albanian month mappings for date parsing
        self.albanian_months = {
            'janar': 1, 'shkurt': 2, 'mars': 3, 'prill': 4,
            'maj': 5, 'qershor': 6, 'korrik': 7, 'gusht': 8,
            'shtator': 9, 'tetor': 10, 'nëntor': 11, 'dhjetor': 12
        }
        
        logger.info("Albanian Metadata Extractor initialized")
    
    def extract(self, text: str, document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract Albanian legal metadata from text
        
        Args:
            text: Input text to analyze
            document_id: Optional document identifier
            
        Returns:
            Dictionary with extracted metadata and analysis
        """
        if not text:
            return self._create_empty_metadata(document_id)
        
        metadata: Dict[str, Any] = {
            "document_id": document_id,
            "language": "albanian",
            "extraction_timestamp": datetime.now().isoformat(),
            "sections": [],
            "dates": [],
            "case_references": [],
            "parties": [],
            "document_types": [],
            "amounts": [],
            "courts": [],
            "judges": [],
            "deadlines": [],
            "clauses": [],
            "extraction_stats": {}
        }
        
        # Extract each type of metadata
        metadata["sections"] = self._extract_sections(text)
        metadata["dates"] = self._extract_dates(text)
        metadata["case_references"] = self._extract_case_references(text)
        metadata["parties"] = self._extract_parties(text)
        metadata["document_types"] = self._extract_document_types(text)
        metadata["amounts"] = self._extract_amounts(text)
        metadata["courts"] = self._extract_courts(text)
        metadata["judges"] = self._extract_judges(text)
        metadata["deadlines"] = self._extract_deadlines(text)
        metadata["clauses"] = self._extract_clauses(text)
        
        # Calculate document complexity and statistics
        metadata["complexity_score"] = self._calculate_complexity_score(metadata)
        metadata["extraction_stats"] = self._calculate_extraction_stats(metadata)
        
        logger.debug(f"Extracted metadata for document {document_id}: {len(metadata['sections'])} sections, {len(metadata['dates'])} dates")
        
        return metadata
    
    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        """Extract contract/article sections"""
        sections = []
        matches = self.patterns['contract_section'].findall(text)
        for match in matches:
            sections.append({
                "section_number": match[0].strip(),
                "section_text": match[1].strip(),
                "type": "contract_section",
                "confidence": 0.9
            })
        return sections
    
    def _extract_dates(self, text: str) -> List[Dict[str, Any]]:
        """Extract dates in Albanian format"""
        dates = []
        matches = self.patterns['date'].findall(text)
        for match in matches:
            date_str = match[0]
            month_name = match[1].lower()
            month_num = self.albanian_months.get(month_name)
            
            dates.append({
                "date_string": date_str,
                "month_albanian": match[1],
                "month_numeric": month_num,
                "type": "albanian_date",
                "confidence": 0.8
            })
        return dates
    
    def _extract_case_references(self, text: str) -> List[Dict[str, Any]]:
        """Extract case references"""
        references = []
        matches = self.patterns['case_reference'].findall(text)
        for match in matches:
            references.append({
                "case_number": match.strip(),
                "type": "case_reference",
                "confidence": 0.85
            })
        return references
    
    def _extract_parties(self, text: str) -> List[Dict[str, Any]]:
        """Extract legal parties"""
        parties = []
        matches = self.patterns['party'].findall(text)
        for match in matches:
            parties.append({
                "role": match[0].strip(),
                "name": match[1].strip(),
                "type": "legal_party",
                "confidence": 0.8
            })
        return parties
    
    def _extract_document_types(self, text: str) -> List[Dict[str, Any]]:
        """Extract document types"""
        doc_types = []
        matches = self.patterns['document_type'].findall(text)
        for match in matches:
            doc_types.append({
                "document_type": match,
                "type": "document_classification",
                "confidence": 0.7
            })
        return doc_types
    
    def _extract_amounts(self, text: str) -> List[Dict[str, Any]]:
        """Extract monetary amounts"""
        amounts = []
        matches = self.patterns['amount'].findall(text)
        for match in matches:
            amounts.append({
                "amount": match[0],
                "currency": match[1],
                "type": "monetary_amount",
                "confidence": 0.9
            })
        return amounts
    
    def _extract_courts(self, text: str) -> List[Dict[str, Any]]:
        """Extract court mentions"""
        courts = []
        matches = self.patterns['court'].findall(text)
        for match in matches:
            courts.append({
                "court_name": match[0].strip(),
                "type": "court_reference",
                "confidence": 0.8
            })
        return courts
    
    def _extract_judges(self, text: str) -> List[Dict[str, Any]]:
        """Extract judge mentions"""
        judges = []
        matches = self.patterns['judge'].findall(text)
        for match in matches:
            judges.append({
                "judge_name": match[0].strip(),
                "type": "judge_reference",
                "confidence": 0.7
            })
        return judges
    
    def _extract_deadlines(self, text: str) -> List[Dict[str, Any]]:
        """Extract deadlines and time limits"""
        deadlines = []
        matches = self.patterns['deadline'].findall(text)
        for match in matches:
            deadlines.append({
                "deadline_type": match[0].strip(),
                "deadline_date": match[1].strip(),
                "type": "legal_deadline",
                "confidence": 0.75
            })
        return deadlines
    
    def _extract_clauses(self, text: str) -> List[Dict[str, Any]]:
        """Extract legal clauses"""
        clauses = []
        matches = self.patterns['clause'].findall(text)
        for match in matches:
            clauses.append({
                "clause_type": match[0].strip(),
                "clause_number": match[1].strip(),
                "type": "legal_clause",
                "confidence": 0.7
            })
        return clauses
    
    def _calculate_complexity_score(self, metadata: Dict[str, Any]) -> float:
        """Calculate document complexity based on extracted metadata"""
        score = 0.0
        
        # Weight different metadata types by importance
        weights = {
            "sections": 0.25,
            "dates": 0.10,
            "case_references": 0.15,
            "parties": 0.12,
            "amounts": 0.08,
            "courts": 0.08,
            "judges": 0.06,
            "deadlines": 0.08,
            "clauses": 0.08
        }
        
        for key, weight in weights.items():
            count = len(metadata.get(key, []))
            # Logarithmic scaling to prevent domination by single category
            category_score = min(count * 0.1, 1.0) * weight
            score += category_score
        
        return round(min(score, 1.0), 2)  # Cap at 1.0
    
    def _calculate_extraction_stats(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate extraction statistics"""
        stats: Dict[str, Any] = {}
        
        for key in ['sections', 'dates', 'case_references', 'parties', 
                   'amounts', 'courts', 'judges', 'deadlines', 'clauses']:
            stats[key] = len(metadata.get(key, []))
        
        stats['total_entities'] = sum(stats.values())
        stats['complexity_score'] = metadata.get('complexity_score', 0.0)
        
        return stats
    
    def _create_empty_metadata(self, document_id: Optional[str] = None) -> Dict[str, Any]:
        """Create empty metadata structure"""
        return {
            "document_id": document_id,
            "language": "albanian",
            "extraction_timestamp": datetime.now().isoformat(),
            "sections": [],
            "dates": [],
            "case_references": [],
            "parties": [],
            "document_types": [],
            "amounts": [],
            "courts": [],
            "judges": [],
            "deadlines": [],
            "clauses": [],
            "complexity_score": 0.0,
            "extraction_stats": {
                "sections": 0, "dates": 0, "case_references": 0, "parties": 0,
                "amounts": 0, "courts": 0, "judges": 0, "deadlines": 0, "clauses": 0,
                "total_entities": 0, "complexity_score": 0.0
            }
        }


# Global instance for easy import
albanian_metadata_extractor = AlbanianMetadataExtractor()


# Test function for development
def test_metadata_extractor():
    """Test the Albanian metadata extractor with sample legal text"""
    extractor = AlbanianMetadataExtractor()
    
    sample_text = """
    Çështja Nr. 2024-CV-1234
    Neni 5.2: Dënimi në vonesë është 0.1% në ditë nga shuma e pambuluar.
    Data e seancës: 15 Mars 2024 në Gjykatën e Tiranës.
    Paditësi: Petro Dhima
    Padituesi: Shpresa Llagami dhe Kompania ALBA Sh.p.k.
    Shuma e kërkuar: 450,000 €
    Gjykatësi Artan Kola do të prezidojë.
    Afati për paraqitjen e ankesës: 30 Prill 2024
    Kjo kontratë përmban disa klauzola të rëndësishme.
    Pika 3.1: Dorëzimi i mallrave brenda 30 ditësh.
    """
    
    print("Testing Albanian Metadata Extractor:")
    print("=" * 60)
    print("Sample Text:")
    print(sample_text)
    print("\n" + "=" * 60)
    
    metadata = extractor.extract(sample_text, "test_doc_001")
    
    print("Extracted Metadata:")
    print(f"Complexity Score: {metadata['complexity_score']}")
    print(f"Total Entities: {metadata['extraction_stats']['total_entities']}")
    
    # Print key extracted information
    if metadata['sections']:
        print(f"\nSections found: {len(metadata['sections'])}")
        for section in metadata['sections']:
            print(f"  - Neni {section['section_number']}: {section['section_text'][:50]}...")
    
    if metadata['case_references']:
        print(f"\nCase References: {[ref['case_number'] for ref in metadata['case_references']]}")
    
    if metadata['parties']:
        print(f"\nParties:")
        for party in metadata['parties']:
            print(f"  - {party['role']}: {party['name']}")
    
    if metadata['amounts']:
        print(f"\nAmounts:")
        for amt in metadata['amounts']:
            print(f"  - {amt['amount']} {amt['currency']}")
    
    if metadata['dates']:
        print(f"\nDates: {[date['date_string'] for date in metadata['dates']]}")
    
    if metadata['deadlines']:
        print(f"\nDeadlines:")
        for deadline in metadata['deadlines']:
            print(f"  - {deadline['deadline_type']}: {deadline['deadline_date']}")


if __name__ == "__main__":
    test_metadata_extractor()