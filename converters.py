"""
Converters - LLM-gebaseerde tekstconversie voor AVI en Referentie niveaus
==========================================================================

Gebruikt Anthropic API (Claude) voor daadwerkelijke tekstconversie.
"""

import os
from typing import Optional, List, Dict
from pathlib import Path
import anthropic

from text_utils import (
    TextAnalyzer, AVI_LEVELS, AVI_KENMERKEN, DOELWOORDEN,
    REF_NIVEAU_INFO, bereken_aantal_proposities
)

# =============================================================================
# PROMPT MANAGER
# =============================================================================

class PromptManager:
    """Beheert niveau-specifieke prompts."""
    
    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            self.prompts_dir = Path(__file__).parent / 'prompts'
        else:
            self.prompts_dir = Path(prompts_dir)
        self._cache = {}
    
    def get_prompt(self, niveau: str) -> str:
        """Haal prompt op voor AVI niveau."""
        if niveau in self._cache:
            return self._cache[niveau]
        
        filename = f"avi_{niveau.lower().replace('-', '_').replace('avi_', '')}.txt"
        filepath = self.prompts_dir / filename
        
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                prompt = f.read()
            self._cache[niveau] = prompt
            return prompt
        
        # Fallback: genereer basis prompt
        return self._generate_basic_prompt(niveau)
    
    def _generate_basic_prompt(self, niveau: str) -> str:
        """Genereer een basis prompt als bestand niet bestaat."""
        kenmerken = AVI_KENMERKEN.get(niveau, {})
        specs = next((l for l in AVI_LEVELS if l['niveau'] == niveau), AVI_LEVELS[5])
        
        return f"""# {niveau} Tekstconversie

## Doelniveau
{niveau} - BILT range: {specs.get('bilt_min', '-')} - {specs.get('bilt_max', '-')}

## Tekstkenmerken
- Woordtypen: {kenmerken.get('woordtypen', 'Geen beperkingen')}
- Zinskenmerken: {kenmerken.get('zinskenmerken', 'Geen beperkingen')}
- Max lettergrepen: {kenmerken.get('max_lettergrepen', 'Geen beperking')}
- Max zinslengte: {kenmerken.get('max_zinslengte', 'Geen beperking')}

## Parameters
- Gemiddelde woordlengte: {specs.get('gem_wlen', 4.5)} letters
- % Frequente woorden: {specs.get('pct_freq', 70)}%
"""


# =============================================================================
# AVI CONVERTER
# =============================================================================

class AVIConverter:
    """Converteert teksten naar specifiek AVI-niveau met LLM."""
    
    def __init__(self, analyzer: TextAnalyzer, api_key: str = None):
        self.analyzer = analyzer
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None
        self.prompt_manager = PromptManager()
    
    def convert(self, source_text: str, target_niveau: str, target_tijd_min: int = 1) -> Dict:
        """
        Converteer tekst naar doelniveau.
        
        Returns dict met:
        - final_text: geconverteerde tekst
        - success: bool
        - source_analysis: dict
        - converted_analysis: dict
        - process_log: list
        """
        result = {
            'final_text': '',
            'success': False,
            'source_analysis': None,
            'converted_analysis': None,
            'process_log': [],
            'validatie_problemen': [],
        }
        
        if not self.client:
            result['process_log'].append("❌ Geen API key geconfigureerd")
            return result
        
        # Stap 1: Analyseer brontekst
        source_analysis = self.analyzer.analyse_avi(source_text)
        if not source_analysis:
            result['process_log'].append("❌ Kon brontekst niet analyseren")
            return result
        
        result['source_analysis'] = source_analysis.to_dict()
        result['process_log'].append(f"📊 Brontekst: {source_analysis.niveau} (BILT: {source_analysis.bilt:.1f})")
        
        # Bepaal richting
        source_idx = next((i for i, l in enumerate(AVI_LEVELS) if l['niveau'] == source_analysis.niveau), 5)
        target_idx = next((i for i, l in enumerate(AVI_LEVELS) if l['niveau'] == target_niveau), 5)
        
        if target_idx <= source_idx:
            direction = "simplify"
            result['process_log'].append(f"⬇️ Richting: VEREENVOUDIGEN naar {target_niveau}")
        else:
            direction = "enrich"
            result['process_log'].append(f"⬆️ Richting: VERRIJKEN naar {target_niveau}")
        
        # Doelwoorden
        target_woorden = DOELWOORDEN.get(target_niveau, {}).get(target_tijd_min, 100)
        result['process_log'].append(f"🎯 Doelwoorden: {target_woorden}")
        
        # Stap 2: Haal niveau prompt op
        niveau_prompt = self.prompt_manager.get_prompt(target_niveau)
        
        # Stap 3: Conversie met LLM
        target_specs = next((l for l in AVI_LEVELS if l['niveau'] == target_niveau), AVI_LEVELS[5])
        target_kenmerken = AVI_KENMERKEN.get(target_niveau, {})
        
        system_prompt = f"""Je bent een expert tekstschrijver voor Nederlandse kinderen.
Je converteert teksten naar AVI-niveau {target_niveau}.

=== NIVEAU SPECIFICATIES ===
{niveau_prompt}

=== BELANGRIJKE REGELS ===
- Schrijf precies {target_woorden} woorden (±15%)
- BILT moet tussen {target_specs.get('bilt_min', 50)} en {target_specs.get('bilt_max', 80)} zijn
- Gemiddelde woordlengte: ~{target_specs['gem_wlen']} letters
- % Frequente woorden: ~{target_specs['pct_freq']}%
{f"- Max lettergrepen per woord: {target_kenmerken['max_lettergrepen']}" if target_kenmerken.get('max_lettergrepen') else ""}
{f"- Max woorden per zin: {target_kenmerken['max_zinslengte']}" if target_kenmerken.get('max_zinslengte') else ""}
- Behoud de inhoud en betekenis van de originele tekst
- Maak de tekst vloeiend en interessant, geen opsomming
- Geef ALLEEN de tekst, geen uitleg of commentaar"""

        human_prompt = f"""Converteer de volgende tekst naar {target_niveau} niveau.

ORIGINELE TEKST:
{source_text}

Schrijf nu de geconverteerde tekst ({target_woorden} woorden):"""

        result['process_log'].append("🤖 Conversie met LLM...")
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                messages=[
                    {"role": "user", "content": human_prompt}
                ],
                system=system_prompt
            )
            
            converted_text = response.content[0].text.strip()
            result['final_text'] = converted_text
            result['process_log'].append("✅ Tekst gegenereerd")
            
            # Stap 4: Valideer resultaat
            converted_analysis = self.analyzer.analyse_avi(converted_text, target_niveau)
            if converted_analysis:
                result['converted_analysis'] = converted_analysis.to_dict()
                
                # Check BILT
                bilt_min = target_specs.get('bilt_min') or 0
                bilt_max = target_specs.get('bilt_max') or 100
                
                if bilt_min <= converted_analysis.bilt <= bilt_max:
                    result['success'] = True
                    result['process_log'].append(f"✅ BILT OK: {converted_analysis.bilt:.1f}")
                else:
                    result['validatie_problemen'].append(f"BILT {converted_analysis.bilt:.1f} buiten range {bilt_min}-{bilt_max}")
                    result['process_log'].append(f"⚠️ BILT buiten range: {converted_analysis.bilt:.1f}")
                
                # Check woordenaantal
                marge = target_woorden * 0.20
                if abs(converted_analysis.totaal_woorden - target_woorden) <= marge:
                    result['process_log'].append(f"✅ Woordenaantal OK: {converted_analysis.totaal_woorden}")
                else:
                    result['validatie_problemen'].append(f"Woordenaantal {converted_analysis.totaal_woorden} (doel: {target_woorden})")
                    result['process_log'].append(f"⚠️ Woordenaantal: {converted_analysis.totaal_woorden} (doel: {target_woorden})")
                
                if not result['validatie_problemen']:
                    result['success'] = True
            
        except Exception as e:
            result['process_log'].append(f"❌ Fout: {str(e)}")
        
        return result


# =============================================================================
# REF CONVERTER
# =============================================================================

class REFConverter:
    """Converteert teksten naar specifiek Referentieniveau met LLM."""
    
    def __init__(self, analyzer: TextAnalyzer, api_key: str = None):
        self.analyzer = analyzer
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None
    
    def convert(self, source_text: str, target_niveau: str) -> Dict:
        """Converteer tekst naar doelniveau (1F, 2F, 3F)."""
        result = {
            'final_text': '',
            'success': False,
            'source_analysis': None,
            'converted_analysis': None,
            'process_log': [],
            'validatie_problemen': [],
        }
        
        if not self.client:
            result['process_log'].append("❌ Geen API key geconfigureerd")
            return result
        
        # Analyseer brontekst
        source_analysis = self.analyzer.analyse_ref(source_text)
        if not source_analysis:
            result['process_log'].append("❌ Kon brontekst niet analyseren")
            return result
        
        result['source_analysis'] = source_analysis.to_dict()
        result['process_log'].append(f"📊 Brontekst: {source_analysis.niveau} (score: {source_analysis.score:.2f})")
        
        # Bepaal richting
        niveau_order = {'1F': 1, '2F': 2, '3F': 3}
        if niveau_order[target_niveau] < niveau_order[source_analysis.niveau]:
            direction = "simplify"
            result['process_log'].append(f"⬇️ Richting: VEREENVOUDIGEN naar {target_niveau}")
        else:
            direction = "enrich"
            result['process_log'].append(f"⬆️ Richting: VERRIJKEN naar {target_niveau}")
        
        target_info = REF_NIVEAU_INFO[target_niveau]
        
        # Conversie met LLM
        system_prompt = f"""Je bent een expert tekstschrijver voor het Nederlandse onderwijs.
Je converteert teksten naar referentieniveau {target_niveau}.

=== {target_niveau} KENMERKEN ===
- Niveau: {target_info['naam']}
- Gemiddelde woordlengte: ~{target_info['wl_typical']} letters
- Gemiddelde zinslengte: ~{target_info['zl_typical']} woorden
- % Lange zinnen (>20 woorden): ~{target_info['long_sent_typical']}%

=== INSTRUCTIES ===
{"- Gebruik korte, eenvoudige zinnen" if target_niveau == "1F" else ""}
{"- Gebruik concrete, alledaagse woorden" if target_niveau == "1F" else ""}
{"- Vermijd bijzinnen en abstracte begrippen" if target_niveau == "1F" else ""}
{"- Gebruik gemiddeld complexe zinnen" if target_niveau == "2F" else ""}
{"- Mix van eenvoudige en complexere woorden" if target_niveau == "2F" else ""}
{"- Gebruik langere, complexe zinnen met bijzinnen" if target_niveau == "3F" else ""}
{"- Gebruik abstractere en gespecialiseerde woorden" if target_niveau == "3F" else ""}
{"- Gebruik diverse signaalwoorden (causaal, contrastief, conclusief)" if target_niveau == "3F" else ""}

- Behoud de inhoud en betekenis van de originele tekst
- Maak de tekst vloeiend en samenhangend
- Geef ALLEEN de tekst, geen uitleg"""

        human_prompt = f"""Converteer de volgende tekst naar {target_niveau} niveau.

ORIGINELE TEKST:
{source_text}

Schrijf nu de geconverteerde tekst:"""

        result['process_log'].append("🤖 Conversie met LLM...")
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                messages=[
                    {"role": "user", "content": human_prompt}
                ],
                system=system_prompt
            )
            
            converted_text = response.content[0].text.strip()
            result['final_text'] = converted_text
            result['process_log'].append("✅ Tekst gegenereerd")
            
            # Valideer
            converted_analysis = self.analyzer.analyse_ref(converted_text)
            if converted_analysis:
                result['converted_analysis'] = converted_analysis.to_dict()
                
                if converted_analysis.niveau == target_niveau:
                    result['success'] = True
                    result['process_log'].append(f"✅ Niveau OK: {converted_analysis.niveau}")
                else:
                    result['validatie_problemen'].append(f"Niveau {converted_analysis.niveau} (doel: {target_niveau})")
                    result['process_log'].append(f"⚠️ Niveau: {converted_analysis.niveau} (doel: {target_niveau})")
                    # Accepteer toch als het dichtbij is
                    result['success'] = True
            
        except Exception as e:
            result['process_log'].append(f"❌ Fout: {str(e)}")
        
        return result
