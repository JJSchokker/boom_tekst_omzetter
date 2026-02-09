"""
Toets Generator - Begrijpend Lezen Toetsen
==========================================

Genereert toetsen bij teksten op referentieniveau (1F/2F/3F):
- 6 meerkeuzevragen (objectief nakijkbaar)
- 4 open vragen (Socratische feedback)
"""

import os
from typing import Dict, List
import anthropic
import json
import re

# =============================================================================
# VRAAGTYPE DEFINITIES PER NIVEAU
# =============================================================================

OPEN_VRAGEN_TEMPLATES = {
    '1F': [
        "Waar gaat deze tekst over? Vertel in je eigen woorden.",
        "Welk stukje uit de tekst vond je het leukst of het interessantst? Waarom?",
        "Wat heb je geleerd van deze tekst?",
        "Ken jij iemand of iets dat lijkt op wat in de tekst staat?",
    ],
    '2F': [
        "Vat de tekst samen in 2-3 zinnen.",
        "Waarom heeft de schrijver deze tekst geschreven, denk je?",
        "Welk punt van de schrijver vind jij het belangrijkst? Leg uit waarom.",
        "Kun je een voorbeeld uit je eigen leven bedenken dat past bij deze tekst?",
    ],
    '3F': [
        "Wat is de hoofdgedachte van deze tekst?",
        "Wat wil de schrijver bereiken met deze tekst?",
        "Ben je het eens met de redenering van de schrijver? Waarom wel of niet?",
        "Hoe zou je de informatie uit deze tekst kunnen gebruiken?",
    ],
}


class ToetsGenerator:
    """Genereert begrijpend lezen toetsen met MC en open vragen."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None
    
    def genereer_toets(self, tekst: str, niveau: str) -> Dict:
        """Genereer een complete toets voor een tekst."""
        if not self.client:
            return {'mc_vragen': [], 'open_vragen': [], 'success': False, 'error': 'Geen API key'}
        
        mc_vragen = self._genereer_mc_vragen(tekst, niveau)
        open_vragen = OPEN_VRAGEN_TEMPLATES.get(niveau, OPEN_VRAGEN_TEMPLATES['2F'])
        
        return {
            'mc_vragen': mc_vragen,
            'open_vragen': open_vragen,
            'success': len(mc_vragen) > 0,
            'error': None if mc_vragen else 'Kon geen vragen genereren',
            'tekst': tekst,
            'niveau': niveau,
        }
    
    def _genereer_mc_vragen(self, tekst: str, niveau: str) -> List[Dict]:
        """Genereer 6 meerkeuzevragen."""
        
        niveau_instructie = {
            '1F': "Gebruik eenvoudige taal. Focus op: woordbetekenis, tekstverwijzing (wat betekent 'ze/hij/dit'), letterlijk begrip, volgorde.",
            '2F': "Gemiddelde complexiteit. Focus op: woordbetekenis, expliciet verband, impliciet verband, signaalwoorden, hoofdgedachte.",
            '3F': "Complexere vragen. Focus op: impliciet verband, signaalwoorden, tekststructuur, redenering volgen, samenvatten.",
        }

        system_prompt = f"""Je maakt 6 meerkeuzevragen voor een {niveau} begrijpend lezen toets.

{niveau_instructie.get(niveau, niveau_instructie['2F'])}

REGELS:
- 4 opties per vraag (A, B, C, D)
- Precies één correct antwoord
- Afleiders zijn plausibel maar fout
- Varieer positie van correcte antwoord
- Antwoord kan uit de tekst gehaald/afgeleid worden

Antwoord ALLEEN met JSON array:
[{{"vraag": "...", "opties": {{"A": "...", "B": "...", "C": "...", "D": "..."}}, "correct": "B", "uitleg": "..."}}]"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                messages=[{"role": "user", "content": f"Tekst:\n\n{tekst}"}],
                system=system_prompt
            )
            
            content = response.content[0].text.strip()
            if content.startswith("```"):
                content = re.sub(r'^```json?\n?', '', content)
                content = re.sub(r'\n?```$', '', content)
            
            return json.loads(content)[:6]
        except Exception as e:
            print(f"Error: {e}")
            return []
    
    def beoordeel_mc(self, mc_vragen: List[Dict], antwoorden: Dict[int, str]) -> Dict:
        """Beoordeel de meerkeuzevragen."""
        resultaten = []
        score = 0
        
        for i, vraag in enumerate(mc_vragen):
            gekozen = antwoorden.get(i, '')
            is_correct = gekozen.upper() == vraag.get('correct', '').upper()
            if is_correct:
                score += 1
            
            resultaten.append({
                'vraagnummer': i + 1,
                'vraag': vraag.get('vraag', ''),
                'gekozen': gekozen,
                'correct_antwoord': vraag.get('correct', ''),
                'is_correct': is_correct,
                'uitleg': vraag.get('uitleg', ''),
                'opties': vraag.get('opties', {}),
            })
        
        return {
            'score': score,
            'max_score': len(mc_vragen),
            'percentage': round(score / len(mc_vragen) * 100) if mc_vragen else 0,
            'resultaten': resultaten,
        }
    
    def genereer_feedback_open_vraag(self, tekst: str, vraag: str, antwoord: str, niveau: str) -> str:
        """Genereer Socratische feedback: erkennen, waarderen, verdiepen."""
        if not self.client or not antwoord or not antwoord.strip():
            return "Je hebt deze vraag nog niet beantwoord. Probeer het - er is geen goed of fout!"
        
        toon = {
            '1F': "Gebruik eenvoudige, enthousiaste taal voor een kind van 10-11.",
            '2F': "Gebruik toegankelijke, stimulerende taal voor 12-14 jarigen.",
            '3F': "Gebruik volwassen taal, daag uit tot dieper nadenken.",
        }
        
        system_prompt = f"""Geef feedback als warme leraar. Structuur:
1. ERKEN wat de leerling zegt
2. WAARDEER de gedachte positief  
3. VERDIEP met 1-2 vervolgvragen

NOOIT zeggen dat iets fout/onvolledig is. {toon.get(niveau, toon['2F'])}
Maximaal 4 zinnen."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": f"VRAAG: {vraag}\nANTWOORD: {antwoord}\n\nTEKST: {tekst[:1000]}"}],
                system=system_prompt
            )
            return response.content[0].text.strip()
        except:
            return "Bedankt voor je antwoord! Wat vond je zelf het belangrijkste van de tekst?"
    
    def genereer_rapport(self, toets: Dict, mc_antwoorden: Dict[int, str], 
                         open_antwoorden: Dict[int, str]) -> Dict:
        """Genereer compleet rapport met MC beoordeling en open feedback."""
        mc_resultaat = self.beoordeel_mc(toets['mc_vragen'], mc_antwoorden)
        
        open_feedback = []
        for i, vraag in enumerate(toets['open_vragen']):
            antwoord = open_antwoorden.get(i, '')
            feedback = self.genereer_feedback_open_vraag(
                toets['tekst'], vraag, antwoord, toets['niveau']
            )
            open_feedback.append({
                'vraagnummer': i + 1,
                'vraag': vraag,
                'antwoord': antwoord,
                'feedback': feedback,
            })
        
        return {
            'niveau': toets['niveau'],
            'mc_resultaat': mc_resultaat,
            'open_feedback': open_feedback,
        }
