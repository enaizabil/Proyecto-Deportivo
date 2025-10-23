#!/usr/bin/env python3
"""
process_teams_safe.py
- Extrae info de equipos desde TheSportsDB
- Traduce al español (googletrans si está; si no y hay OpenAI, usa IA)
- Resume con IA (si hay API key y funciona), si no, usa TextRank
- Guarda CSV sobrescribiendo
"""

import os
import time
import requests
import pandas as pd
from typing import Optional

# STextRank
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

# NLTK resources 
import nltk
try:
    nltk.download("punkt", quiet=True)
    nltk.download("stopwords", quiet=True)
except Exception as e:
    print("Warning: NLTK download issue:", e)

# googletrans 
try:
    from googletrans import Translator
    _translator_available = True
except Exception:
    Translator = None
    _translator_available = False

# OpenAI 
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
USE_OPENAI = False
ai_client = None
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        ai_client = OpenAI(api_key=OPENAI_API_KEY)
        USE_OPENAI = True
    except Exception as e:
        print("OpenAI client could not be initialized:", e)
        USE_OPENAI = False

# ---------- Utilities ----------

def summarise_text_rank(text: str, sentences_count: int = 4, word_limit: int = 50) -> str:
    """Resumen extractivo usando TextRank, luego truncado a word_limit palabras."""
    if not text or not text.strip():
        return "Resumen no disponible"
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("spanish"))
        summarizer = TextRankSummarizer()
        summary_sentences = summarizer(parser.document, sentences_count)
        summary_text = " ".join(str(s) for s in summary_sentences).strip()
        # Truncar a word_limit
        words = summary_text.split()
        if len(words) > word_limit:
            return " ".join(words[:word_limit]) + "..."
        return summary_text
    except Exception as e:
        print("TextRank error:", e)
        return "Resumen no disponible"

def summarise_with_ai(text: str, word_limit: int = 50) -> Optional[str]:
    """Intentar resumen con IA (OpenAI). """
    if not USE_OPENAI or ai_client is None:
        return None
    if not text or not text.strip():
        return None
    try:
        system_msg = {
            "role": "system",
            "content": "You are an assistant that generates concise summaries in Spanish. "
                       "Return only the summary text, without commentary."
        }
        user_msg = {
            "role": "user",
            "content": f"Resume el siguiente texto en castellano en un máximo de {word_limit} palabras. "
                       f"Devuélvelo solo como texto, sin títulos ni notas:\n\n{text}"
        }
        # Llamada a la API 
        resp = ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[system_msg, user_msg],
            max_tokens=200,
            temperature=0.2
        )
        summary = resp.choices[0].message.content.strip()
        # Forzar truncamiento a word_limit (por si la IA no respeta)
        words = summary.split()
        if len(words) > word_limit:
            summary = " ".join(words[:word_limit]) + "..."
        return summary
    except Exception as e:
        # Detectar errores comunes (quota, 429, invalid key)
        err_str = str(e).lower()
        if "quota" in err_str or "insufficient_quota" in err_str or "429" in err_str:
            print("OpenAI error (quota/429):", e)
        else:
            print("OpenAI call failed:", e)
        return None

def translate_text(text: str, dest: str = "es") -> str:
    """Traduce usando googletrans si está disponible; si no, intenta OpenAI (si está) como fallback; si no, devuelve original."""
    if not text:
        return ""
    # Googletrans (local)
    if _translator_available:
        try:
            translator = Translator()
            result = translator.translate(text, dest=dest)
            return result.text
        except Exception as e:
            print("googletrans failed:", e)
    # Fallback a OpenAI translate (si disponible)
    if USE_OPENAI and ai_client:
        try:
            sys_msg = {
                "role": "system",
                "content": "You are a translation assistant. Translate the provided English text to Spanish only."
            }
            user_msg = {
                "role": "user",
                "content": f"Traduce al español el siguiente texto (devuelve solo la traducción):\n\n{text}"
            }
            resp = ai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[sys_msg, user_msg],
                max_tokens=400,
                temperature=0.0
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print("OpenAI translate failed:", e)
    # Si todo falla
    print("No translation available, returning original English text.")
    return text

# ---------- Main processing ----------

def process_teams(teams, base_url="https://www.thesportsdb.com/api/v1/json/123", delay_between_calls=0.5):
    results = []
    for team in teams:
        try:
            search_url = f"{base_url}/searchteams.php?t={requests.utils.requote_uri(team)}"
            r = requests.get(search_url, timeout=10)
            r.raise_for_status()
            data = r.json()
            if not data or not data.get("teams"):
                print(f"No data for team '{team}'. Skipping.")
                continue
            team_info = data["teams"][0]
            name = team_info.get("strTeam", "N/A")
            sport = team_info.get("strSport", "N/A")
            league = team_info.get("strLeague", "N/A")
            year = team_info.get("intFormedYear", "N/A")
            stadium = team_info.get("strStadium", "N/A")
            description_en = team_info.get("strDescriptionEN")

            if not description_en or not description_en.strip():
                print(f"Team '{name}' has no English description. Skipping.")
                continue

            # Traducción
            description_es = translate_text(description_en, dest="es")

            # Intentar IA primero
            resumen = None
            if USE_OPENAI:
                resumen = summarise_with_ai(description_es, word_limit=50)
                if resumen is None:
                    print("Falling back to TextRank for team:", name)

            if resumen is None:
                resumen = summarise_text_rank(description_es, sentences_count=4, word_limit=50)

            results.append({
                "Equipo": name,
                "Deporte": sport,
                "Liga": league,
                "Año de fundación": year,
                "Estadio": stadium,
                "Descripción (es)": description_es,
                "Resumen": resumen
            })

            time.sleep(delay_between_calls)  # evitar sobrecarga en la API

        except Exception as e:
            print(f"Error processing team '{team}':", e)
            continue
    return results

def save_to_csv(items, path="data/teams_list.csv"):
    if not items:
        print("No rows to save.")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        df = pd.DataFrame(items)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"Saved CSV to {path} ({len(items)} rows).")
    except Exception as e:
        print("Error saving CSV:", e)

# ---------- Run ----------

if __name__ == "__main__":
    # Cambia aquí por la lista que quieras
    teams = [
        "Arsenal", "Chelsea", "Liverpool", "Manchester United", "Manchester City"
    ]

    print("OpenAI available:", USE_OPENAI)
    items = process_teams(teams)
    save_to_csv(items)
