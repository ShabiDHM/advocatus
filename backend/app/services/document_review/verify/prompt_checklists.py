# FILE: backend/app/services/document_review/verify/prompt_checklists.py
# PHOENIX PROTOCOL - VERIFY CHECKLISTS V1.0
# Ekstraktuar nga verify_prompts.py V1.14 (pa ndryshim logjike).

from typing import Any, Dict


DOC_TYPE_CHECKLISTS: Dict[str, Dict[str, Any]] = {

    "padi_civile": {
        "label": "Padi Civile",
        "required_parts": [
            "Emri i gjykatës kompetente",
            "Të dhënat e paditësit (emër, adresë, numër personal)",
            "Të dhënat e paditurit (emër, adresë)",
            "Përshkrimi i qartë dhe kronologjik i fakteve",
            "Objekti i padisë (kërkesa kryesore)",
            "Vlera e kontestit (ku aplikohet)",
            "Baza ligjore me nene specifike të cituara",
            "Petitumi — kërkesa konkrete ndaj gjykatës",
            "Lista e provave (dokumente, ekspertiza)",
            "Lista e dëshmitarëve me të dhënat e kontaktit",
            "Dokumentet bashkangjitur (kopje)",
            "Data dhe vendi i hartimit",
            "Nënshkrimi i paditësit ose përfaqësuesit ligjor",
            "Numri i kopjeve për palët",
        ],
    },

    "pergjigje_padi": {
        "label": "Përgjigje në Padi",
        "required_parts": [
            "Emri i gjykatës dhe numri i lëndës",
            "Të dhënat e paditurit (përgjigjësi)",
            "Të dhënat e paditësit",
            "Përgjigje për çdo pretendim të padisë (pikë për pikë)",
            "Kundërshtimet faktike",
            "Kundërshtimet ligjore",
            "Baza ligjore me nene specifike",
            "Kërkesa (refuzim i padisë / kundërpadí)",
            "Provat për kundërshtimet",
            "Lista e dëshmitarëve",
            "Nënshkrimi i përgjigjësit ose përfaqësuesit",
            "Data dhe vendi",
        ],
    },

    "kallzim_penal": {
        "label": "Kallëzim Penal",
        "required_parts": [
            "Organi kompetent (Prokuroria Themelore)",
            "Të dhënat e kallëzuesit (emër, adresë, statusi)",
            "Të dhënat e personit të kallëzuar",
            "Përshkrimi i veprës penale",
            "Koha e kryerjes së veprës",
            "Vendi i kryerjes së veprës",
            "Elementet objektive të veprës (actus reus)",
            "Elementet subjektive (mens rea — dashje/pakujdes)",
            "Neni i Kodit Penal që përshkruan veprën",
            "Dëmi i shkaktuar (material/moral/shëndetësor)",
            "Provat e bashkangjitura",
            "Kërkesa për ndjekje penale",
            "Statusi i kallëzuesit (viktimë/dëshmitar)",
            "Data dhe nënshkrimi",
        ],
    },

    "kontrate": {
        "label": "Kontratë",
        "required_parts": [
            "Identifikimi i plotë i palëve kontraktuese",
            "Objekti i kontratës (i përshkruar qartë)",
            "Çmimi ose kompensimi",
            "Afati i ekzekutimit",
            "Të drejtat dhe detyrimet e secilës palë",
            "Kushtet e pagesës (mënyra, koha)",
            "Pasojat e shkeljes së kontratës",
            "Klauzola e zgjidhjes së mosmarrëveshjeve",
            "Ligji i zbatueshëm dhe juridiksioni",
            "Kushtet e ndryshimit të kontratës",
            "Kushtet e ndërprerjes / anulimit",
            "Klauzola e force majeure (ku aplikohet)",
            "Konfidencialiteti (ku aplikohet)",
            "Data, vendi dhe nënshkrimet e palëve",
        ],
    },

    "kerkese_propozim": {
        "label": "Kërkesë / Propozim",
        "required_parts": [
            "Organi adresues (gjykata/prokuroria/organi)",
            "Të dhënat e kërkuesit",
            "Subjekti i qartë i kërkesës",
            "Baza faktike",
            "Baza ligjore me nene specifike",
            "Kërkesa specifike (çfarë kërkohet saktësisht)",
            "Afati i kërkuar (ku aplikohet)",
            "Provat mbështetëse",
            "Nënshkrimi dhe data",
        ],
    },

    "ankese_kundershtim": {
        "label": "Ankesë / Kundërshtim",
        "required_parts": [
            "Gjykata e ankimit (e shkallës së dytë)",
            "Numri i lëndës dhe vendimi i ankimuar",
            "Të dhënat e ankuesit",
            "Afati i ankesës (data e pranimit të vendimit)",
            "Bazat e ankesës (arsyet)",
            "Arsyetimi ligjor për secilën bazë",
            "Kërkesa (prishje / ndryshim / kthim në rigjykim)",
            "Provat e reja (nëse ka)",
            "Nënshkrimi dhe data",
        ],
    },

    "tjeter": {
        "label": "Dokument Tjetër",
        "required_parts": [
            "Identifikimi i palëve / subjekteve",
            "Objekti / subjekti i dokumentit",
            "Përshkrimi i fakteve ose kontekstit",
            "Baza ligjore (ku aplikohet)",
            "Kërkesa / dispozitivi",
            "Provat (ku aplikohet)",
            "Afatet (ku aplikohet)",
            "Data dhe vendi",
            "Nënshkrimi i autorit",
            "Struktura formale e dokumentit",
        ],
    },
}