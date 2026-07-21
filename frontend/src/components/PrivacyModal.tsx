// FILE: src/components/PrivacyModal.tsx
// PHOENIX PROTOCOL - PRIVACY MODAL V6.2 (LINTER COMPILE FIXED)
// 1. FIX: Removed unused 'Eye' import from 'lucide-react' to resolve the TypeScript unused variable warning.

import React from 'react';
import { motion } from 'framer-motion';
import { X, Shield, Lock, Database, Globe } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface PrivacyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const scrollbarStyles = `
  .privacy-scroll::-webkit-scrollbar { width: 6px; }
  .privacy-scroll::-webkit-scrollbar-track { background: rgba(0,0,0,0.1); }
  .privacy-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }
  .privacy-scroll::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
`;

const PrivacyModal: React.FC<PrivacyModalProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-canvas/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <style>{scrollbarStyles}</style>
      <motion.div 
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="glass-panel border border-main rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col bg-canvas"
      >
        <div className="p-6 border-b border-main flex justify-between items-center bg-surface/30">
          <h2 className="text-xl font-bold text-text-primary flex items-center gap-2">
            <Shield className="text-primary-start h-5 w-5 animate-pulse" />
            {t('footer.privacyPolicy', 'Politika e Privatësisë & GDPR')}
          </h2>
          <button onClick={onClose} className="text-text-secondary hover:text-text-primary transition-colors focus:outline-none">
            <X size={24} />
          </button>
        </div>

        <div className="p-6 overflow-y-auto privacy-scroll space-y-6 text-text-secondary text-sm leading-relaxed">
          
          {/* Section 1: Intro */}
          <div className="space-y-2">
            <p className="text-text-primary font-medium">
              Mirë se vini në <strong>Juristi AI</strong> (një platformë nga <em>Data And Human Management</em>).
            </p>
            <p>
              Privatësia, konfidencialiteti dhe sovraniteti i të dhënave tuaja ligjore dhe financiare janë parimi ynë themelor. Ky dokument rregullon mënyrën se si platforma jonë përpunon, ruan dhe mbron shkresat tuaja gjyqësore, dëshmitë dhe regjistrat financiarë, në përputhje të plotë me **Rregulloren e Përgjithshme të BE-së për Mbrojtjen e të Dhënave (GDPR)** dhe **Ligjin Nr. 06/L-082 për Mbrojtjen e Të Dhënave Personale të Republikës së Kosovës**.
            </p>
          </div>

          {/* Section 2: Zero-Retention AI Pipeline */}
          <div className="space-y-2">
            <h3 className="text-text-primary font-bold text-base flex items-center gap-2">
                <Lock size={16} className="text-primary-start" /> 1. Përpunimi i Automatizuar (Zero-Retention AI)
            </h3>
            <p>
              Platforma Juristi AI shfrytëzon rrjete neuronale të avancuara (përmes API-ve të enkriptuara të OpenRouter) për të kryer analiza ligjore, ekstraktim të dhënash dhe simulime të lëndës.
            </p>
            <ul className="list-disc pl-5 space-y-1.5 opacity-90 text-xs">
                <li><strong> RAM-Only Parsing</strong>: Dokumentet tuaja përpunohen vetëm në kujtesën e përkohshme fluturuese (volatile RAM) të serverit gjatë kohës së gjenerimit dhe asgjësohen menjëherë pas përfundimit të analizës.</li>
                <li><strong>Jo Trajnim Modellesh</strong>: Të dhënat tuaja sensitive, emrat e palëve, dhe shifrat financiare nuk përdoren asnjëherë dhe në asnjë rrethanë për të trajnuar apo përmirësuar modelet publike apo private të AI.</li>
            </ul>
          </div>

          {/* Section 3: B2 Cloud Security */}
          <div className="space-y-2">
            <h3 className="text-text-primary font-bold text-base flex items-center gap-2">
                <Database size={16} className="text-primary-start" /> 2. Ruajtja e Sigurt & Enkriptimi AES-256
            </h3>
            <p>
              Të gjitha dokumentet e ngarkuara zyrtarisht në dosjen e lëndës suaj ruhen në infrastrukturën e enkriptuar të Backblaze B2:
            </p>
            <ul className="list-disc pl-5 space-y-1.5 opacity-90 text-xs">
                <li><strong>Enkriptimi në Transit dhe në Qetësi</strong>: Dosjet enkriptohen gjatë transmetimit përmes protokolleve të sigurta SSL/TLS dhe ruhen të enkriptuara në server me algoritmin ushtarak AES-256.</li>
                <li><strong>Akses i Kufizuar</strong>: Vetëm ju dhe anëtarët e autorizuar të organizatës suaj posedojnë çelësat e vërtetimit (JWT) për të gjeneruar linqe të përkohshme preview të dokumenteve.</li>
            </ul>
          </div>

          {/* Section 4: Irrevocable Cascading Erasure */}
          <div className="space-y-2">
            <h3 className="text-text-primary font-bold text-base flex items-center gap-2">
                <Shield size={16} className="text-primary-start" /> 3. E Drejta për t'u Harruar (Fshirja Kaskadë)
            </h3>
            <p>
              Në përputhje me Nenin 17 të GDPR (E drejta për fshirje), ne kemi ndërtuar një sistem të plotë të spastrimit kaskadë. Kur ju fshini një Dokument, një Shpenzim, apo një Lëndë të tërë nga paneli juaj:
            </p>
            <ul className="list-disc pl-5 space-y-1.5 opacity-90 text-xs">
                <li>Fshihen menjëherë të gjitha rekordet e databazës MongoDB.</li>
                <li>Spastrohen të gjithë vektorët semantikë (AI Memory embeddings) nga indeksi i kërkimit.</li>
                <li>Fshihen fizikisht të gjitha skedarët origjinalë, drafte, dhe preview nga serverat tanë Cloud B2 brenda sekondave, në mënyrë të pakthyeshme.</li>
            </ul>
          </div>

          {/* Section 5: Rights & Contact */}
          <div className="space-y-2">
            <h3 className="text-text-primary font-bold text-base flex items-center gap-2">
                <Globe size={16} className="text-primary-start" /> 4. Sovraniteti Gjeografik & Kontaktet
            </h3>
            <p>
              Sistemi ynë respekton parimet e sovranitetit të të dhënave, duke siguruar që të dhënat tuaja të mbrohen nga ndërhyrjet e paautorizuara. Për çdo kërkesë zyrtare të qasjes, shkarkimit të plotë të të dhënave tuaja (Data Portability), apo ankesë mbi privatësinë, ju lutemi na kontaktoni drejtpërdrejt në:
            </p>
            <p className="font-mono text-xs bg-surface/50 p-2.5 rounded-lg border border-main text-center">
              Email: <strong>info@juristi.tech</strong> <br />
              Prishtinë, Republika e Kosovës
            </p>
          </div>

          <div className="pt-4 border-t border-main/30 text-xs text-center opacity-50 select-none">
            Përditësuar së fundmi: Korrik 2026
          </div>
        </div>

        <div className="p-4 border-t border-main bg-surface/10 text-center shrink-0">
            <button onClick={onClose} className="btn-secondary px-8 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider transition-all hover-lift">
                {t('general.close', 'Mbyll')}
            </button>
        </div>
      </motion.div>
    </div>
  );
};

export default PrivacyModal;