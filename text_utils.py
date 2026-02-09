"""
Text Utilities - AVI & Referentie Tekst Omzetter
=================================================

Bevat analyse-logica voor beide modi:
- AVI: Technisch lezen (BILT-gebaseerd)
- REF: Begrijpend lezen (1F/2F/3F niveau-gebaseerd)

Gebaseerd op calibratie met:
- 18 officiële AVI-toetskaarten
- 30 authentieke CvTE referentieteksten
"""

import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
import pandas as pd

# =============================================================================
# CONSTANTEN - AVI MODEL
# =============================================================================

# BILT = 43.21 - 0.23 × %frequente_woorden + 8.63 × gem_woordlengte
BILT_INTERCEPT = 43.21
BILT_COEF_FREQ = -0.23
BILT_COEF_WLEN = 8.63

# AVI niveau specificaties
AVI_LEVELS = [
    {'niveau': 'AVI-M3', 'bilt_min': None, 'bilt_max': 56.0, 'bilt_typical': 51, 'pct_freq': 91, 'gem_wlen': 3.3, 'max_lettergrepen': 1, 'max_zinslengte': 6, 'leeftijd': 6.9},
    {'niveau': 'AVI-E3', 'bilt_min': 56.0, 'bilt_max': 60.0, 'bilt_typical': 58, 'pct_freq': 80, 'gem_wlen': 3.9, 'max_lettergrepen': 2, 'max_zinslengte': 7, 'leeftijd': 7.2},
    {'niveau': 'AVI-M4', 'bilt_min': 60.0, 'bilt_max': 62.0, 'bilt_typical': 61, 'pct_freq': 79, 'gem_wlen': 4.1, 'max_lettergrepen': 3, 'max_zinslengte': 8, 'leeftijd': 7.9},
    {'niveau': 'AVI-E4', 'bilt_min': 62.0, 'bilt_max': 64.5, 'bilt_typical': 63, 'pct_freq': 76, 'gem_wlen': 4.4, 'max_lettergrepen': 4, 'max_zinslengte': 9, 'leeftijd': 8.2},
    {'niveau': 'AVI-M5', 'bilt_min': 64.5, 'bilt_max': 66.5, 'bilt_typical': 65, 'pct_freq': 75, 'gem_wlen': 4.5, 'max_lettergrepen': None, 'max_zinslengte': None, 'leeftijd': 8.9},
    {'niveau': 'AVI-E5', 'bilt_min': 66.5, 'bilt_max': 68.0, 'bilt_typical': 67, 'pct_freq': 75, 'gem_wlen': 4.8, 'max_lettergrepen': None, 'max_zinslengte': None, 'leeftijd': 9.2},
    {'niveau': 'AVI-M6', 'bilt_min': 68.0, 'bilt_max': 71.0, 'bilt_typical': 69, 'pct_freq': 71, 'gem_wlen': 4.9, 'max_lettergrepen': None, 'max_zinslengte': None, 'leeftijd': 9.9},
    {'niveau': 'AVI-E6', 'bilt_min': 71.0, 'bilt_max': 73.0, 'bilt_typical': 72, 'pct_freq': 63, 'gem_wlen': 5.0, 'max_lettergrepen': None, 'max_zinslengte': None, 'leeftijd': 10.2},
    {'niveau': 'AVI-M7', 'bilt_min': 73.0, 'bilt_max': 75.0, 'bilt_typical': 74, 'pct_freq': 60, 'gem_wlen': 5.1, 'max_lettergrepen': None, 'max_zinslengte': None, 'leeftijd': 10.9},
    {'niveau': 'AVI-E7', 'bilt_min': 75.0, 'bilt_max': 77.0, 'bilt_typical': 76, 'pct_freq': 58, 'gem_wlen': 5.2, 'max_lettergrepen': None, 'max_zinslengte': None, 'leeftijd': 11.2},
    {'niveau': 'AVI-Plus', 'bilt_min': 77.0, 'bilt_max': None, 'bilt_typical': 79, 'pct_freq': 55, 'gem_wlen': 5.3, 'max_lettergrepen': None, 'max_zinslengte': None, 'leeftijd': 12.2},
]

DOELWOORDEN = {
    'AVI-M3':   {1: 45,  2: 80,  3: 107},
    'AVI-E3':   {1: 56,  2: 101, 3: 135},
    'AVI-M4':   {1: 65,  2: 117, 3: 156},
    'AVI-E4':   {1: 68,  2: 123, 3: 164},
    'AVI-M5':   {1: 83,  2: 152, 3: 206},
    'AVI-E5':   {1: 89,  2: 164, 3: 224},
    'AVI-M6':   {1: 96,  2: 179, 3: 247},
    'AVI-E6':   {1: 110, 2: 205, 3: 282},
    'AVI-M7':   {1: 116, 2: 218, 3: 302},
    'AVI-E7':   {1: 117, 2: 220, 3: 306},
    'AVI-Plus': {1: 118, 2: 224, 3: 306},
}

# Tekstkenmerken per AVI-niveau (technisch lezen specificaties)
AVI_KENMERKEN = {
    'AVI-M3': {
        'woordtypen': 'Alleen éénlettergrepige woorden (mkm-structuur: mak, pen, vis)',
        'zinskenmerken': 'Zeer korte zinnen, max 5-6 woorden',
        'max_lettergrepen': 1, 'max_zinslengte': 6,
        'voorbeelden': ['ik', 'pen', 'vis', 'mak', 'kom', 'bal'],
        'nieuw': 'Enkelvoudige mkm-woorden',
        'verboden': 'Tweelettergrepige woorden, medeklinkerclusters',
    },
    'AVI-E3': {
        'woordtypen': 'Éénlettergrepig plus sch-, -ng, -nk, eenvoudige tweelettergrepig',
        'zinskenmerken': 'Korte zinnen, max 6-7 woorden',
        'max_lettergrepen': 2, 'max_zinslengte': 7,
        'voorbeelden': ['school', 'bang', 'denk', 'mama', 'papa', 'water'],
        'nieuw': 'sch-, -ng, -nk clusters, eenvoudige tweelettergrepige',
        'verboden': 'Voorvoegsels be-, ge-, ver-, ont-',
    },
    'AVI-M4': {
        'woordtypen': 'Voorvoegsels be-, ge-, verkleinwoorden -je, open/gesloten lettergrepen',
        'zinskenmerken': 'Zinnen tot 8 woorden, eenvoudige bijzinnen',
        'max_lettergrepen': 3, 'max_zinslengte': 8,
        'voorbeelden': ['begin', 'geluk', 'hondje', 'bloempje', 'bomen', 'regen'],
        'nieuw': 'be-, ge-, verkleinwoorden, open lettergrepen',
        'verboden': 'Voorvoegsels ver-, ont-, achtervoegsels -heid, -lijk',
    },
    'AVI-E4': {
        'woordtypen': 'Voorvoegsels ver-, ont-, achtervoegsels -lijk, -ig, samenstellingen',
        'zinskenmerken': 'Zinnen tot 9 woorden, betrekkelijke bijzinnen',
        'max_lettergrepen': 4, 'max_zinslengte': 9,
        'voorbeelden': ['vertellen', 'ontdekken', 'vrolijk', 'vriendelijk', 'zonnebloem'],
        'nieuw': 'ver-, ont-, -lijk, -ig, samenstellingen',
        'verboden': 'Complexe leenwoorden, abstracte begrippen',
    },
    'AVI-M5': {
        'woordtypen': 'Woorden met x, -tie, c als /k/, uitbreiding woordenschat',
        'zinskenmerken': 'Geen beperkingen op zinslengte',
        'max_lettergrepen': None, 'max_zinslengte': None,
        'voorbeelden': ['taxi', 'politie', 'computer', 'actie', 'exact'],
        'nieuw': 'x, -tie, c als /k/',
        'verboden': 'Complexe leenwoorden met vreemde spelling',
    },
    'AVI-E5': {
        'woordtypen': 'Leenwoorden met eau, é, è, ch als /sj/',
        'zinskenmerken': 'Geen beperkingen',
        'max_lettergrepen': None, 'max_zinslengte': None,
        'voorbeelden': ['cadeau', 'café', 'crème', 'chocolade', 'chauffeur'],
        'nieuw': 'eau, é, è, ch als /sj/',
        'verboden': None,
    },
    'AVI-M6': {
        'woordtypen': 'Woorden met trema, minder frequente leenwoorden',
        'zinskenmerken': 'Geen beperkingen',
        'max_lettergrepen': None, 'max_zinslengte': None,
        'voorbeelden': ['ideeën', 'geïnteresseerd', 'skiën', 'egoïstisch'],
        'nieuw': 'Trema (ë, ï), uitgebreidere leenwoorden',
        'verboden': None,
    },
    'AVI-E6': {'woordtypen': 'Alle woordtypen, alleen BILT bepalend', 'zinskenmerken': 'Geen beperkingen', 'max_lettergrepen': None, 'max_zinslengte': None, 'voorbeelden': None, 'nieuw': 'Alle structuren toegestaan', 'verboden': None},
    'AVI-M7': {'woordtypen': 'Alle woordtypen, alleen BILT bepalend', 'zinskenmerken': 'Geen beperkingen', 'max_lettergrepen': None, 'max_zinslengte': None, 'voorbeelden': None, 'nieuw': 'Alle structuren toegestaan', 'verboden': None},
    'AVI-E7': {'woordtypen': 'Alle woordtypen, alleen BILT bepalend', 'zinskenmerken': 'Geen beperkingen', 'max_lettergrepen': None, 'max_zinslengte': None, 'voorbeelden': None, 'nieuw': 'Alle structuren toegestaan', 'verboden': None},
    'AVI-Plus': {'woordtypen': 'Alle woordtypen, alleen BILT bepalend', 'zinskenmerken': 'Geen beperkingen', 'max_lettergrepen': None, 'max_zinslengte': None, 'voorbeelden': None, 'nieuw': 'Alle structuren toegestaan', 'verboden': None},
}

# =============================================================================
# CONSTANTEN - REFERENTIE MODEL
# =============================================================================

REF_INTERCEPT = -2.3972
REF_COEF_LONG_SENT = 0.0208
REF_COEF_MARKER_DIV = 0.3423
REF_COEF_WL = 0.5405
REF_CUTOFF_1F_2F = 1.25
REF_CUTOFF_2F_3F = 2.35

REF_NIVEAU_INFO = {
    '1F': {'naam': 'Einde basisonderwijs / vmbo-bb', 'wl_typical': 4.73, 'zl_typical': 10.9, 'long_sent_typical': 7},
    '2F': {'naam': 'Einde vmbo / mbo-2,3', 'wl_typical': 4.91, 'zl_typical': 14.4, 'long_sent_typical': 15},
    '3F': {'naam': 'Einde havo / mbo-4', 'wl_typical': 5.27, 'zl_typical': 17.4, 'long_sent_typical': 31},
}

DISCOURSE_MARKERS = {
    'additief': ['en', 'ook', 'bovendien', 'daarnaast', 'verder', 'tevens', 'eveneens', 'daarbij'],
    'temporeel': ['toen', 'daarna', 'vervolgens', 'eerst', 'dan', 'later', 'eerder', 'voordat', 'nadat', 'terwijl', 'zodra', 'inmiddels', 'intussen', 'uiteindelijk'],
    'causaal': ['omdat', 'doordat', 'want', 'daardoor', 'daarom', 'dus', 'hierdoor', 'waardoor', 'aangezien', 'immers', 'namelijk'],
    'contrastief': ['maar', 'echter', 'toch', 'hoewel', 'ondanks', 'terwijl', 'daarentegen', 'integendeel', 'niettemin', 'desondanks', 'weliswaar'],
    'conclusief': ['kortom', 'samengevat', 'concluderend', 'samenvattend', 'aldus', 'derhalve', 'tenslotte', 'tot slot'],
}

# =============================================================================
# HULPFUNCTIES
# =============================================================================

def tel_lettergrepen(woord: str) -> int:
    woord = woord.lower().strip()
    if not woord:
        return 0
    klinkers = 'aeiouáéíóúàèìòùäëïöüâêîôûy'
    lettergrepen = 0
    i = 0
    while i < len(woord):
        if woord[i] in klinkers:
            lettergrepen += 1
            while i < len(woord) and woord[i] in klinkers:
                i += 1
        else:
            i += 1
    return max(1, lettergrepen)

def tokenize(text: str) -> List[str]:
    return re.findall(r'\b\w+\b', text.lower())

def split_sentences(text: str) -> List[str]:
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

def bereken_aantal_proposities(doelwoorden: int) -> int:
    if doelwoorden < 60: return 3
    elif doelwoorden < 90: return 5
    elif doelwoorden < 120: return 6
    elif doelwoorden < 160: return 8
    elif doelwoorden < 200: return 10
    else: return 12

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AVIResult:
    bilt: float
    niveau: str
    totaal_woorden: int
    gem_woordlengte: float
    pct_frequent: float
    gem_zinslengte: float
    lettergreep_verdeling: Dict[int, int] = field(default_factory=dict)
    te_lange_woorden: List[Tuple[str, int]] = field(default_factory=list)
    te_lange_zinnen: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'bilt': round(self.bilt, 2), 'niveau': self.niveau, 'totaal_woorden': self.totaal_woorden,
            'gem_woordlengte': round(self.gem_woordlengte, 2), 'pct_frequent': round(self.pct_frequent, 1),
            'gem_zinslengte': round(self.gem_zinslengte, 1), 'lettergreep_verdeling': self.lettergreep_verdeling,
        }

@dataclass
class REFResult:
    niveau: str
    score: float
    confidence: str
    totaal_woorden: int
    gem_woordlengte: float
    gem_zinslengte: float
    pct_frequent: float
    long_sent_ratio: float
    marker_diversity: int
    
    def to_dict(self) -> dict:
        return {
            'niveau': self.niveau, 'score': round(self.score, 3), 'confidence': self.confidence,
            'totaal_woorden': self.totaal_woorden, 'gem_woordlengte': round(self.gem_woordlengte, 2),
            'gem_zinslengte': round(self.gem_zinslengte, 1), 'pct_frequent': round(self.pct_frequent, 1),
            'long_sent_ratio': round(self.long_sent_ratio * 100, 1), 'marker_diversity': self.marker_diversity,
        }

# =============================================================================
# ANALYZER CLASS
# =============================================================================

class TextAnalyzer:
    def __init__(self, woordenlijst_path: str = None):
        if woordenlijst_path is None:
            woordenlijst_path = Path(__file__).parent / "woordenlijst_1400.xlsx"
        self.woordenlijst = self._laad_woordenlijst(woordenlijst_path)
    
    def _laad_woordenlijst(self, path) -> set:
        try:
            df = pd.read_excel(path)
            col = df.columns[0]
            return set(str(w).lower() for w in df[col].tolist() if pd.notna(w))
        except Exception as e:
            print(f"Waarschuwing: Kon woordenlijst niet laden: {e}")
            return set()
    
    def analyse_avi(self, tekst: str, target_niveau: str = None) -> Optional[AVIResult]:
        tokens = tokenize(tekst)
        sentences = split_sentences(tekst)
        if not tokens or len(tokens) < 10:
            return None
        
        totaal_woorden = len(tokens)
        gem_woordlengte = sum(len(t) for t in tokens) / totaal_woorden
        
        if self.woordenlijst:
            freq_count = sum(1 for t in tokens if t in self.woordenlijst)
            pct_frequent = (freq_count / totaal_woorden) * 100
        else:
            pct_frequent = 70
        
        if sentences:
            sentence_lengths = [len(tokenize(s)) for s in sentences]
            gem_zinslengte = sum(sentence_lengths) / len(sentence_lengths)
        else:
            sentence_lengths = [totaal_woorden]
            gem_zinslengte = totaal_woorden
        
        bilt = BILT_INTERCEPT + BILT_COEF_FREQ * pct_frequent + BILT_COEF_WLEN * gem_woordlengte
        niveau = self._bepaal_avi_niveau(bilt)
        
        verdeling = {}
        for woord in tokens:
            lg = tel_lettergrepen(woord)
            verdeling[lg] = verdeling.get(lg, 0) + 1
        
        te_lange_woorden = []
        te_lange_zinnen = []
        if target_niveau:
            kenmerken = AVI_KENMERKEN.get(target_niveau, {})
            max_lg = kenmerken.get('max_lettergrepen')
            max_zin = kenmerken.get('max_zinslengte')
            if max_lg:
                gezien = set()
                for woord in tokens:
                    if woord not in gezien:
                        lg = tel_lettergrepen(woord)
                        if lg > max_lg:
                            te_lange_woorden.append((woord, lg))
                            gezien.add(woord)
            if max_zin:
                for s in sentences:
                    wc = len(tokenize(s))
                    if wc > max_zin:
                        te_lange_zinnen.append({'tekst': s[:80], 'woorden': wc})
        
        return AVIResult(bilt=bilt, niveau=niveau, totaal_woorden=totaal_woorden,
            gem_woordlengte=gem_woordlengte, pct_frequent=pct_frequent, gem_zinslengte=gem_zinslengte,
            lettergreep_verdeling=verdeling, te_lange_woorden=te_lange_woorden, te_lange_zinnen=te_lange_zinnen)
    
    def _bepaal_avi_niveau(self, bilt: float) -> str:
        for level in AVI_LEVELS:
            bilt_min = level['bilt_min'] or float('-inf')
            bilt_max = level['bilt_max'] or float('inf')
            if bilt_min <= bilt < bilt_max:
                return level['niveau']
        return 'AVI-Plus'
    
    def get_niveau_specs(self, niveau: str) -> dict:
        for level in AVI_LEVELS:
            if level['niveau'] == niveau:
                return level
        return AVI_LEVELS[-1]
    
    def get_doelwoorden(self, niveau: str, minuten: int) -> int:
        if niveau in DOELWOORDEN:
            return DOELWOORDEN[niveau].get(minuten, DOELWOORDEN[niveau][1])
        return 100
    
    def get_avi_suggesties(self, result: AVIResult, target: str) -> List[str]:
        suggesties = []
        current_idx = next((i for i, l in enumerate(AVI_LEVELS) if l['niveau'] == result.niveau), 5)
        target_idx = next((i for i, l in enumerate(AVI_LEVELS) if l['niveau'] == target), 5)
        target_specs = AVI_LEVELS[target_idx]
        target_kenmerken = AVI_KENMERKEN.get(target, {})
        
        if target_idx < current_idx:
            if result.gem_woordlengte > target_specs['gem_wlen']:
                suggesties.append(f"📝 **Kortere woorden**: Huidige gem. {result.gem_woordlengte:.2f} letters, streef naar {target_specs['gem_wlen']:.1f}")
            if result.pct_frequent < target_specs['pct_freq']:
                suggesties.append(f"📚 **Frequentere woorden**: Nu {result.pct_frequent:.0f}% frequent, streef naar {target_specs['pct_freq']}%")
            if target_kenmerken.get('max_lettergrepen'):
                suggesties.append(f"✂️ **Max lettergrepen**: Gebruik maximaal {target_kenmerken['max_lettergrepen']}-lettergrepige woorden")
            if target_kenmerken.get('max_zinslengte'):
                suggesties.append(f"📏 **Kortere zinnen**: Maximaal {target_kenmerken['max_zinslengte']} woorden per zin")
            if target_kenmerken.get('verboden'):
                suggesties.append(f"🚫 **Vermijd**: {target_kenmerken['verboden']}")
        else:
            if result.gem_woordlengte < target_specs['gem_wlen']:
                suggesties.append(f"📝 **Langere woorden**: Huidige gem. {result.gem_woordlengte:.2f} letters, streef naar {target_specs['gem_wlen']:.1f}")
            if result.pct_frequent > target_specs['pct_freq']:
                suggesties.append(f"📚 **Minder frequente woorden**: Nu {result.pct_frequent:.0f}% frequent, streef naar {target_specs['pct_freq']}%")
            if target_kenmerken.get('nieuw'):
                suggesties.append(f"✨ **Nieuw toegestaan**: {target_kenmerken['nieuw']}")
        
        if target_kenmerken.get('woordtypen'):
            suggesties.append(f"📋 **Woordtypen {target}**: {target_kenmerken['woordtypen']}")
        
        return suggesties
    
    def analyse_ref(self, tekst: str) -> Optional[REFResult]:
        tokens = tokenize(tekst)
        sentences = split_sentences(tekst)
        if not tokens or len(tokens) < 20:
            return None
        
        totaal_woorden = len(tokens)
        gem_woordlengte = sum(len(t) for t in tokens) / totaal_woorden
        
        if sentences:
            sentence_lengths = [len(tokenize(s)) for s in sentences]
            gem_zinslengte = sum(sentence_lengths) / len(sentence_lengths)
        else:
            sentence_lengths = [totaal_woorden]
            gem_zinslengte = totaal_woorden
        
        long_sent_ratio = sum(1 for l in sentence_lengths if l > 20) / len(sentence_lengths)
        long_sent_pct = long_sent_ratio * 100
        
        marker_types = set()
        for t in tokens:
            for mtype, markers in DISCOURSE_MARKERS.items():
                if t in markers:
                    marker_types.add(mtype)
        marker_diversity = len(marker_types)
        
        if self.woordenlijst:
            freq_count = sum(1 for t in tokens if t in self.woordenlijst)
            pct_frequent = (freq_count / totaal_woorden) * 100
        else:
            pct_frequent = 65
        
        score = REF_INTERCEPT + REF_COEF_LONG_SENT * long_sent_pct + REF_COEF_MARKER_DIV * marker_diversity + REF_COEF_WL * gem_woordlengte
        
        if score < REF_CUTOFF_1F_2F:
            niveau = '1F'
            confidence = 'Hoog' if score < 1.0 else 'Gemiddeld'
        elif score < REF_CUTOFF_2F_3F:
            niveau = '2F'
            confidence = 'Hoog' if 1.5 <= score <= 2.1 else 'Gemiddeld (grensgebied)'
        else:
            niveau = '3F'
            confidence = 'Hoog' if score > 2.7 else 'Gemiddeld'
        
        return REFResult(niveau=niveau, score=score, confidence=confidence, totaal_woorden=totaal_woorden,
            gem_woordlengte=gem_woordlengte, gem_zinslengte=gem_zinslengte, pct_frequent=pct_frequent,
            long_sent_ratio=long_sent_ratio, marker_diversity=marker_diversity)
    
    def get_ref_suggesties(self, result: REFResult, target: str) -> List[str]:
        suggesties = []
        target_info = REF_NIVEAU_INFO[target]
        niveau_order = {'1F': 1, '2F': 2, '3F': 3}
        
        if niveau_order[target] < niveau_order[result.niveau]:
            if result.gem_woordlengte > target_info['wl_typical'] + 0.2:
                suggesties.append(f"📝 **Kortere woorden**: Huidige gem. {result.gem_woordlengte:.2f} letters, streef naar ~{target_info['wl_typical']:.1f}")
            if result.gem_zinslengte > target_info['zl_typical'] + 2:
                suggesties.append(f"✂️ **Kortere zinnen**: Huidige gem. {result.gem_zinslengte:.0f} woorden, streef naar ~{target_info['zl_typical']:.0f}")
            if result.long_sent_ratio * 100 > target_info['long_sent_typical'] + 5:
                suggesties.append(f"📏 **Minder lange zinnen**: Nu {result.long_sent_ratio*100:.0f}% >20 woorden, streef naar ~{target_info['long_sent_typical']}%")
            suggesties.append("💡 **Tip**: Gebruik korte, concrete zinnen. Vermijd bijzinnen en abstracte begrippen.")
        else:
            if result.gem_woordlengte < target_info['wl_typical'] - 0.2:
                suggesties.append(f"📝 **Langere woorden**: Huidige gem. {result.gem_woordlengte:.2f} letters, streef naar ~{target_info['wl_typical']:.1f}")
            if result.gem_zinslengte < target_info['zl_typical'] - 2:
                suggesties.append(f"✏️ **Langere zinnen**: Huidige gem. {result.gem_zinslengte:.0f} woorden, streef naar ~{target_info['zl_typical']:.0f}")
            if result.long_sent_ratio * 100 < target_info['long_sent_typical'] - 5:
                suggesties.append(f"📏 **Meer lange zinnen**: Nu {result.long_sent_ratio*100:.0f}% >20 woorden, streef naar ~{target_info['long_sent_typical']}%")
            if result.marker_diversity < 4:
                suggesties.append("🔗 **Meer signaalwoorden**: Gebruik diverse verbindingswoorden (causaal, contrastief, conclusief)")
            suggesties.append("💡 **Tip**: Voeg bijzinnen toe, gebruik abstractere begrippen en expliciete argumentatiestructuren.")
        
        return suggesties
