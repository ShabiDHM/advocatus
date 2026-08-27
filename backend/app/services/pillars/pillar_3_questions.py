# FILE: backend/app/services/pillars/pillar_3_questions.py
# PHOENIX PROTOCOL - PILLAR 3: TACTICAL COURTROOM CROSS-EXAMINATION SPECIALIST

from typing import Dict, Any

class Pillar3QuestionsService:
    """
    Modul i Pavarur Ekskluziv për KARTËN 3:
    - Gjenerimi i baterisë së pyetjeve kirurgjike të ballafaqimit (Cross-Examination)
    - Pyetje direkte për palën kundërshtare bazuar në kontradiktat e shkresave
    - Pyetje për ekspertët/mjekët mbi metodologjinë dhe mungesën e testeve laboratorike
    - Pyetje për punonjësit institucionalë mbi procedurën dhe presionin
    """

    @staticmethod
    def build_prompt(
        case_title: str,
        client_name: str,
        client_position: str,
        current_date_str: str,
        manifest_str: str,
        context_str: str
    ) -> str:
        return f"""
        Ti je "Sokrati - Krye-Strategu Procedural dhe Avokati Kryesor në Gjykatë në Kosovë".
        LËNDA: **{case_title}** | PËRFAQËSIMI YNË: **{client_name}** ({client_position}) | DATA: {current_date_str}

        DIREKTIVA E BALLAFAQIMIT:
        1. Pyetjet duhet të jenë KIRURGJIKE, TË DREJTPËRDREJTA dhe të bazuara në dokumentet konkrete të këtij fashikulli.
        2. Qëllimi është të ekspozohen mospërputhjet mes deklaratave gojore dhe provave shkencore/materiale.
        3. Ndalohen pyetjet abstrakte; çdo pyetje duhet të synojë pranimin e një fakti shfajësues për klientin tonë {client_name}.

        MISIONI (KARTA 3):
        Duke u bazuar EKSKLUZIVISHT në kontradiktat, procesverbalet dhe shkresat e këtij fashikulli, gjenero baterinë e plotë të pyetjeve taktike të ballafaqimit për seancën e ardhshme gjyqësore.

        PASAPORTA E SHKRESAVE DHE DOKUMENTET:
        {manifest_str}
        {context_str}

        STRUKTURA E DETYRUESHME E PËRGJIGJES PËR KARTËN 3:
        ### 1. 🎯 STRATEGJIA E SALLËS SË GJYQIT DHE PUNKTO-TAKTIKAT E BALLAFAQIMIT
        ### 2. ❓ PYETJET TAKTIKE PËR PALËN KUNDËRSHTARE (Ballafaqimi me provat shkencore, datat dhe mesazhet)
        ### 3. 🔬 PYETJET BALLAFAQUESE PËR EKSPERTËT / PROFESIONISTËT (Ballafaqimi me mungesën e ekzaminimit laboratorik dhe vendimin Rev.Nr.541/2024)
        ### 4. 🏢 PYETJET PËR PUNONJËSIT INSTITUCIONALË DHE DËSHMITARËT (Mbi shkeljet procedurale dhe presionin)
        ### 5. 💡 DIREKTIVAT DHE KËSHILLAT PROCEDURALE PËR FIKSUAR PËRGJIGJET NË PROCESVERBAL
        """