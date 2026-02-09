"""
Boom Tekst Omzetter - Streamlit Applicatie
==========================================

Twee modi:
1. AVI Tekst omzetter - voor technisch lezen
2. Referentie Tekst omzetter - voor begrijpend lezen (1F/2F/3F) + TOETS
"""

import os
import streamlit as st
import pandas as pd
from text_utils import (
    TextAnalyzer, AVI_LEVELS, DOELWOORDEN, AVI_KENMERKEN, REF_NIVEAU_INFO
)
from converters import AVIConverter, REFConverter
from toets_generator import ToetsGenerator

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Boom Tekst Omzetter",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CSS
# =============================================================================

st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: 700; color: #1a365d; margin-bottom: 0.2rem; }
    .sub-header { font-size: 0.95rem; color: #4a5568; margin-bottom: 1rem; }
    
    .niveau-card {
        padding: 0.8rem; border-radius: 8px; color: white;
        text-align: center; margin-bottom: 0.5rem;
    }
    .niveau-card h2 { font-size: 1.8rem; margin: 0; font-weight: 700; }
    .niveau-card p { margin: 0; opacity: 0.9; font-size: 0.85rem; }
    
    .avi-m3, .avi-e3 { background: linear-gradient(135deg, #4299e1, #3182ce); }
    .avi-m4, .avi-e4 { background: linear-gradient(135deg, #3182ce, #2c5282); }
    .avi-m5, .avi-e5 { background: linear-gradient(135deg, #2c5282, #1a365d); }
    .avi-m6, .avi-e6 { background: linear-gradient(135deg, #553c9a, #44337a); }
    .avi-m7, .avi-e7 { background: linear-gradient(135deg, #9c4221, #7b341e); }
    .avi-plus { background: linear-gradient(135deg, #1a202c, #171923); }
    
    .ref-1f { background: linear-gradient(135deg, #38a169, #2f855a); }
    .ref-2f { background: linear-gradient(135deg, #dd6b20, #c05621); }
    .ref-3f { background: linear-gradient(135deg, #e53e3e, #c53030); }
    
    .direction-up { background: #fef3c7; border-left: 4px solid #d69e2e; padding: 0.5rem 0.8rem; border-radius: 0 6px 6px 0; }
    .direction-down { background: #c6f6d5; border-left: 4px solid #38a169; padding: 0.5rem 0.8rem; border-radius: 0 6px 6px 0; }
    .direction-same { background: #e2e8f0; border-left: 4px solid #718096; padding: 0.5rem 0.8rem; border-radius: 0 6px 6px 0; }
    
    .feedback-box { background: #ebf8ff; border-left: 4px solid #3182ce; padding: 0.8rem; border-radius: 0 6px 6px 0; margin: 0.5rem 0; }
    .correct-box { background: #c6f6d5; border-left: 4px solid #38a169; padding: 0.6rem 0.8rem; border-radius: 0 6px 6px 0; margin: 0.3rem 0; }
    .incorrect-box { background: #fed7d7; border-left: 4px solid #e53e3e; padding: 0.6rem 0.8rem; border-radius: 0 6px 6px 0; margin: 0.3rem 0; }
    
    .stTextArea textarea { font-size: 14px !important; line-height: 1.5 !important; }
    div[data-testid="column"] { padding: 0 0.5rem; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SESSION STATE
# =============================================================================

if "input_text" not in st.session_state:
    st.session_state.input_text = ""
if "toets_data" not in st.session_state:
    st.session_state.toets_data = None
if "toets_fase" not in st.session_state:
    st.session_state.toets_fase = None
if "rapport" not in st.session_state:
    st.session_state.rapport = None

def reset_toets():
    st.session_state.toets_data = None
    st.session_state.toets_fase = None
    st.session_state.rapport = None

# =============================================================================
# INIT
# =============================================================================

@st.cache_resource
def load_analyzer():
    return TextAnalyzer()

analyzer = load_analyzer()

def get_avi_class(niveau): 
    return f"avi-{niveau.lower().replace('avi-', '')}"

def get_direction(source, target, mode='avi'):
    if mode == 'avi':
        s = next((i for i, l in enumerate(AVI_LEVELS) if l['niveau'] == source), 5)
        t = next((i for i, l in enumerate(AVI_LEVELS) if l['niveau'] == target), 5)
    else:
        order = {'1F': 1, '2F': 2, '3F': 3}
        s, t = order.get(source, 2), order.get(target, 2)
    
    if t < s: return "down", f"⬇️ {source} → {target}"
    elif t > s: return "up", f"⬆️ {source} → {target}"
    return "same", f"↔️ {target}"

# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown("## 📚 Tekst Omzetter")
    st.markdown("---")
    
    mode = st.radio("Modus:", ["🔤 AVI", "📖 Referentie"], on_change=reset_toets)
    
    st.markdown("---")
    api_key = st.text_input("API Key", type="password", value=os.environ.get("ANTHROPIC_API_KEY", ""))

# =============================================================================
# AVI MODE
# =============================================================================

if "AVI" in mode:
    st.markdown('<p class="main-header">🔤 AVI Tekst Omzetter</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Technisch lezen - analyseer en converteer naar AVI-niveau</p>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Conversie", "Info"])
    
    with tab1:
        input_text = st.text_area("Tekst:", height=140, placeholder="Plak hier je tekst...", key="avi_in")
        
        source = None
        if input_text.strip():
            source = analyzer.analyse_avi(input_text)
            if source:
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(f'<div class="niveau-card {get_avi_class(source.niveau)}"><h2>{source.niveau}</h2><p>BILT {source.bilt:.1f}</p></div>', unsafe_allow_html=True)
                c2.metric("Woorden", source.totaal_woorden)
                c3.metric("Woordlengte", f"{source.gem_woordlengte:.2f}")
                c4.metric("% Frequent", f"{source.pct_frequent:.0f}%")
        
        st.markdown("---")
        c1, c2, c3 = st.columns([1, 1, 2])
        target = c1.selectbox("Naar:", [l['niveau'] for l in AVI_LEVELS], index=4)
        tijd = c2.selectbox("Tijd:", [1, 2, 3], format_func=lambda x: f"{x} min")
        if source:
            d, txt = get_direction(source.niveau, target, 'avi')
            c3.markdown(f'<div class="direction-{d}" style="margin-top:28px">{txt}</div>', unsafe_allow_html=True)
        
        if st.button("🚀 Converteer", type="primary", use_container_width=True):
            if not input_text.strip():
                st.error("Voer een tekst in")
            elif not api_key:
                st.error("Voer API key in")
            else:
                with st.spinner("Converteren..."):
                    conv = AVIConverter(analyzer, api_key)
                    res = conv.convert(input_text, target, tijd)
                if res.get('final_text'):
                    col1, col2 = st.columns(2)
                    col1.text_area("Origineel", input_text, height=250, disabled=True)
                    col2.text_area(target, res['final_text'], height=250)
                    if res.get('converted_analysis'):
                        ca = res['converted_analysis']
                        st.caption(f"Resultaat: {ca['niveau']} | BILT {ca['bilt']:.1f} | {ca['totaal_woorden']} woorden")
    
    with tab2:
        st.markdown("### AVI-niveaus")
        df = pd.DataFrame([{
            'Niveau': l['niveau'],
            'BILT': f"{l['bilt_min'] or '-'} – {l['bilt_max'] or '-'}",
            'Max lg': AVI_KENMERKEN.get(l['niveau'], {}).get('max_lettergrepen') or '∞',
            'Max zin': AVI_KENMERKEN.get(l['niveau'], {}).get('max_zinslengte') or '∞',
        } for l in AVI_LEVELS])
        st.dataframe(df, hide_index=True, use_container_width=True)

# =============================================================================
# REF MODE
# =============================================================================

else:
    # Check toets fase
    if st.session_state.toets_fase == 'maken':
        # === TOETS MAKEN ===
        toets = st.session_state.toets_data
        st.markdown(f'<p class="main-header">📝 Toets - {toets["niveau"]}</p>', unsafe_allow_html=True)
        
        if st.button("← Terug"):
            reset_toets()
            st.rerun()
        
        with st.expander("📄 Tekst bekijken"):
            st.write(toets['tekst'])
        
        st.markdown("---")
        st.markdown("### Deel A: Meerkeuzevragen")
        
        mc_answers = {}
        for i, v in enumerate(toets['mc_vragen']):
            st.markdown(f"**{i+1}. {v['vraag']}**")
            mc_answers[i] = st.radio(
                f"v{i+1}", ['A', 'B', 'C', 'D'],
                format_func=lambda x, v=v: f"{x}: {v['opties'][x]}",
                key=f"mc{i}", horizontal=True, label_visibility="collapsed"
            )
            st.markdown("")
        
        st.markdown("---")
        st.markdown("### Deel B: Open vragen")
        st.caption("Geen goed of fout – schrijf wat je denkt!")
        
        open_answers = {}
        for i, v in enumerate(toets['open_vragen']):
            st.markdown(f"**{i+7}. {v}**")
            open_answers[i] = st.text_area(f"o{i}", key=f"open{i}", height=80, label_visibility="collapsed")
        
        st.markdown("---")
        if st.button("✅ Indienen", type="primary", use_container_width=True):
            with st.spinner("Nakijken en feedback genereren..."):
                gen = ToetsGenerator(api_key)
                rapport = gen.genereer_rapport(toets, mc_answers, open_answers)
            st.session_state.rapport = rapport
            st.session_state.toets_fase = 'rapport'
            st.rerun()
    
    elif st.session_state.toets_fase == 'rapport':
        # === RAPPORT ===
        rapport = st.session_state.rapport
        st.markdown(f'<p class="main-header">📊 Rapport - {rapport["niveau"]}</p>', unsafe_allow_html=True)
        
        if st.button("← Nieuwe toets"):
            reset_toets()
            st.rerun()
        
        mc = rapport['mc_resultaat']
        c1, c2 = st.columns(2)
        c1.metric("Meerkeuze", f"{mc['score']}/{mc['max_score']}", f"{mc['percentage']}%")
        c2.metric("Open vragen", "Zie feedback 💬")
        
        st.markdown("---")
        st.markdown("### Deel A: Meerkeuze")
        for r in mc['resultaten']:
            if r['is_correct']:
                st.markdown(f"""<div class="correct-box">
                <b>Vraag {r['vraagnummer']}: ✓ Goed!</b><br>
                <small>{r['uitleg']}</small></div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class="incorrect-box">
                <b>Vraag {r['vraagnummer']}: ✗</b> Jij: {r['gekozen']} → Correct: {r['correct_antwoord']}<br>
                <small>{r['uitleg']}</small></div>""", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### Deel B: Feedback")
        for fb in rapport['open_feedback']:
            st.markdown(f"**Vraag {fb['vraagnummer']+6}:** {fb['vraag']}")
            if fb['antwoord']:
                st.markdown(f"*Jouw antwoord:* {fb['antwoord']}")
            st.markdown(f'<div class="feedback-box">💬 {fb["feedback"]}</div>', unsafe_allow_html=True)
            st.markdown("")
    
    else:
        # === NORMALE REF MODUS ===
        st.markdown('<p class="main-header">📖 Referentie Tekst Omzetter</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Begrijpend lezen - analyseer, converteer en toets op 1F/2F/3F niveau</p>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Conversie & Toets", "Info"])
        
        with tab1:
            examples = {
                "-- Voorbeeld --": "",
                "1F": "Het kan een drijvende stronkje zijn geweest of een onbekend geluid. Het blijft gissen waarom de 120 mantelbavianen van Dierenpark Emmen volledig in paniek zijn. Sinds maandag zitten ze, dicht tegen elkaar, op een hoek van een rots. Een woordvoerder van het park noemt het massahysterie.",
                "2F": "Omdat boeren honderd jaar geleden hun kinderen in de zomer op het land nodig hadden, zitten we nu nog steeds met die veel te lange zomervakanties. De leerplicht was prima, maar in de zomer golden de wetten van het boerenbedrijf. Maar er zijn inmiddels goede argumenten om de zomervakantie te verkorten.",
                "3F": "Steeds indringender bemoeit de overheid zich tegenwoordig met het privéleven van de burger. Gold overheidsbemoeienis vroeger uitsluitend het terrein van het kwaad dat een individu anderen kan berokkenen, thans wordt het grondgebied uitgebreid met het kwaad dat burgers zichzelf kunnen aandoen.",
            }
            
            ex = st.selectbox("Voorbeeld:", list(examples.keys()))
            default = examples[ex] if ex != "-- Voorbeeld --" else st.session_state.input_text
            
            input_text = st.text_area("Tekst:", value=default, height=140, placeholder="Plak hier je tekst...")
            if ex == "-- Voorbeeld --":
                st.session_state.input_text = input_text
            
            source = None
            if input_text.strip():
                source = analyzer.analyse_ref(input_text)
                if source:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.markdown(f'<div class="niveau-card ref-{source.niveau.lower()}"><h2>{source.niveau}</h2><p>Score {source.score:.2f}</p></div>', unsafe_allow_html=True)
                    c2.metric("Woorden", source.totaal_woorden)
                    c3.metric("Zinslengte", f"{source.gem_zinslengte:.1f}")
                    c4.metric("Lange zinnen", f"{source.long_sent_ratio*100:.0f}%")
            
            st.markdown("---")
            c1, c2 = st.columns([1, 2])
            target = c1.selectbox("Naar:", ['1F', '2F', '3F'], index=1)
            if source:
                d, txt = get_direction(source.niveau, target, 'ref')
                c2.markdown(f'<div class="direction-{d}" style="margin-top:28px">{txt}</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            convert_btn = col1.button("🚀 Converteer", type="primary", use_container_width=True)
            toets_btn = col2.button("📝 Toets", use_container_width=True, disabled=not (input_text.strip() and source))
            
            if convert_btn:
                if not input_text.strip():
                    st.error("Voer een tekst in")
                elif not api_key:
                    st.error("Voer API key in")
                else:
                    with st.spinner("Converteren..."):
                        conv = REFConverter(analyzer, api_key)
                        res = conv.convert(input_text, target)
                    if res.get('final_text'):
                        c1, c2 = st.columns(2)
                        c1.text_area("Origineel", input_text, height=250, disabled=True)
                        c2.text_area(target, res['final_text'], height=250)
                        if res.get('converted_analysis'):
                            ca = res['converted_analysis']
                            st.caption(f"Resultaat: {ca['niveau']} | Score {ca['score']:.2f}")
            
            if toets_btn:
                if not api_key:
                    st.error("Voer API key in")
                else:
                    with st.spinner("Toets genereren..."):
                        gen = ToetsGenerator(api_key)
                        toets = gen.genereer_toets(input_text, source.niveau)
                    if toets['success']:
                        st.session_state.toets_data = toets
                        st.session_state.toets_fase = 'maken'
                        st.rerun()
                    else:
                        st.error(toets.get('error', 'Fout bij genereren'))
        
        with tab2:
            st.markdown("### Referentieniveaus")
            for niv in ['1F', '2F', '3F']:
                info = REF_NIVEAU_INFO[niv]
                st.markdown(f'<div class="niveau-card ref-{niv.lower()}"><h2>{niv}</h2><p>{info["naam"]}</p></div>', unsafe_allow_html=True)
                st.caption(f"Woordlengte ~{info['wl_typical']} | Zinslengte ~{info['zl_typical']}")
