# FILE: backend/app/services/synthesis/prompts/strict_rules.py
# PHOENIX PROTOCOL - STRICT RULES PROMPT V1.0
# Ekstraktuar nga synthesis_service.py V3.8 — ZERO ndryshim.

STRICT_RULES = """
⚠️ RREGULLA TË PAFEKSIONUESHME:

1. PËRDOR VETËM EMRAT, INSTITUCIONET DHE DATAT QË SHFAQEN NË TË DHËNAT 
   E MËSIPËRME. NUK lejohet të shpikësh emra, institucione, data ose 
   tituj që nuk janë në digest.

2. NUK SHKURTO OSE NDRYSHO EMRAT:
   - Emri i plotë duhet të shfaqet saktësisht siç është në digest.
   - NUK lejohet shkurtim, kombinim, ose ndryshim i emrave.
   - NUK lejohet dyfishimi i fjalëve (p.sh. "Naim Naim Qelaj").
   - NËSE emri nuk gjendet në digest, MOS E PËRDOR.

3. INSTITUCIONET E SAKTA (të dhëna në digest):
   - Për ÇDO person, cito VETËM institucionin që shfaqet në digest.
   - NUK shkëmbe institucionet ndërmjet personave.

4. NËSE DIGEST-i përmban "DOKUMENTI KRYESOR", fokusohu KRYESISHT në atë.

5. ⚠️ RREGULL ABSOLUT PËR NENET E LIGJEVE (KRITIKE):
   - Seksioni "🔒 CITIMET E VËRTETUARA (REGEX)" është BURIMI I VETËM 
     I SË VËRTETËS për citimet.
   - PËRDOR VETËM ligjet dhe nenet që shfaqen në atë seksion.
   - ÇDO ligj/nen që NUK është aty → KONSIDEROHET HALUDINACION.
   - NUK LEJOHET të ndryshosh numrin e ligjit (03/L-182 ≠ 06/L-006).
   - NUK LEJOHET të shpikësh emra ligjesh (LMDHF, KPK, etj.) që nuk 
     shfaqen në listën e ligjeve të verifikuara.
   - NENET: nëse neni shfaqet VETËM si numër, shkruaj VETËM 
     "Neni X i [Ligjit]" — PA shpikje përshkrimi.
   - NUK LEJOHET "[numri]", "[Ligji i panjohur]", "[i panjohur]", 
     "(i panjohur)", "[N/A]".

6. ⚠️ FORMATI I NENEVE (KRITIKE):
   - Shkruaj "Neni X" ose "Neni X, par. Y" — KURRË "Neni X.Y".
   - Shembull i saktë:
        ✅ "Neni 1 i LMDHF"
        ✅ "Neni 1, par. 2 i LMDHF"
        ✅ "Neni 248 i KPRK"
   - Shembull i GABUAR:
        ❌ "Neni 1.2 i LMDHF"
        ❌ "Neni 248 i LMDHF" (nëse 248 nuk është në LMDHF)
   - NËSE dyshon → shkruaj VETËM numrin, pa përshkrim.

7. ⚠️ PËRSHKRIMET E NENEVE:
   - NËSE digest-i etiketon përshkrimin si "kontekst dokumenti" → NUK 
     është përshkrim zyrtar → shkruaj VETËM "Neni X i [Ligjit]".
   - NËSE digest-i etiketon si "përshkrim zyrtar" → përdore fjalë për fjalë.
   - KURRË mos shpik "Rregullat për procedurat e veçanta" ose 
     përshkrime gjenerike.

8. ⚠️ AFATET PROCEDURALE (KRITIKE):
   - Cito afatin VETËM me burim: "Sipas [dokumenti/neni], afati është X".
   - NËSE dokumentet kanë afate të ndryshme → listoji TË GJITHA me burime.
   - NUK LEJOHET kontradiktë brenda raportit (p.sh. 6 muaj në një 
     seksion dhe 8 ditë në tjetrin).
   - Afatet e njohura nga dokumentet: 8 ditë ankim, 12 muaj urdhër 
     mbrojtjeje, 7 ditë ekspertizë psikiatrike, 10 ditë refuzim kërkese.
   - NËSE nuk gjendet afat → shkruaj "Afati: kontrollo manualisht".

9. ⚠️ LLOJI I LËNDËS:
   - NËSE digest-i përmban "🎯 LLOJI I LËNDËS", përdore atë lloj në 
     të gjithë raportin — MOS e ndrysho.

10. ⚠️ STATUSI I DOKUMENTIT:
    - NËSE dokumenti përmban "KËSHILLË JURIDIKE" ose "afat ankimi" 
      → NUK është i plotfuqishëm.
    - MOS e etiketо si "i plotfuqishëm" pa bazë në tekst.
"""