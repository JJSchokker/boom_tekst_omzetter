# Boom Tekst Omzetter

Analyseer en converteer Nederlandse teksten naar specifieke leesniveaus.

## Twee Modi

### 🔤 AVI Tekst Omzetter (Technisch Lezen)
Voor het meten van technische leesvaardigheid bij kinderen (groep 3-8).

**Model:**
```
BILT = 43.21 - 0.23 × %frequente_woorden + 8.63 × gem_woordlengte
```
- Gekalibreerd op 18 officiële AVI-toetskaarten
- R² = 0.94
- Niveaus: AVI-M3 t/m AVI-Plus

### 📖 Referentie Tekst Omzetter (Begrijpend Lezen)
Voor het meten van begrijpend leesvaardigheid (1F/2F/3F).

**Model:**
```
niveau = -2.40 + 0.021 × %lange_zinnen + 0.34 × marker_diversiteit + 0.54 × woordlengte
```
- Gekalibreerd op 30 authentieke CvTE-teksten
- R² = 0.76, Accuracy = 80%
- Niveaus: 1F, 2F, 3F

## Installatie

```bash
pip install -r requirements.txt
```

## Gebruik

```bash
streamlit run app.py
```

## Bestanden

- `app.py` - Streamlit applicatie
- `text_utils.py` - Analyse logica en modellen
- `woordenlijst_1400.xlsx` - Frequente woorden lijst
- `requirements.txt` - Python dependencies

## Referenties

- AVI-methodiek: Boom Uitgevers
- Referentieniveaus: CvTE (College voor Toetsen en Examens)
- BILT: Boom Index Lezen Technisch

---
© 2025 Boom Uitgevers
