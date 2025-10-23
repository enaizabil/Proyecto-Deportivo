# Automatización con n8n + IA + Power BI

Este proyecto es un ejemplo de automatización de flujos deportivos:
- Obtiene partidos de TheSportsDB.
- Genera resúmenes automáticos con OpenAI.
- Exporta resultados a CSV listo para Power BI.

Este script permite extraer información de equipos deportivos desde la API pública de TheSportsDB, traducir sus descripciones al español y generar un resumen automático, guardando todo en un archivo CSV. Está diseñado con un sistema de fallbacks para funcionar incluso cuando algunos servicios externos no están disponibles.

Características principales:
- Obtiene datos de equipos desde TheSportsDB.
- Traduce descripciones al español usando, en este orden:
- googletrans 
- OpenAI
- Genera un resumen automático(OpenAI/TextRank)
- Exporta un CSV con todos los datos
- Manejo de errores y fallos sin detener la ejecución

Requisitos:
- Instalar dependencias base (requirements.txt)
- Token OpenAI: scripts -> .env -> OPENAI_API_KEY="TU_API_KEY"

Tecnologías utilizadas:
- Función	Librería
- Peticiones API	requests
- CSV pandas
- Traducción(googletrans / openai)
- Resumen	(openai/sumy)
- NLP básico	nltk

Uso independiente script:
- Edita la lista de equipos en el main:
    teams = [
        "Arsenal", "Chelsea", "Liverpool", "Manchester United", "Manchester City"
    ]
- Ejecuta el script:
    "python3 process_teams_safe.py"
- El CSV se generará en:
    "data/teams_list.csv"

Uso Procedural:
- N8N -> Lamada API / Seleccion Equipos / Peticion AI
- Codigo -> Filtra peticion / Entrega CSV
- PowerBI -> Visualiza dinamicamente CSV

Estructura del CSV generado(Personalizable)
- Columna	Contenido
- Equipo	Nombre del equipo
- Deporte	Deporte principal
- Liga	Competición
- Año de fundación	Año del club
- Estadio	Estadio del equipo
- Descripción (es)	Descripción traducida
- Resumen	Resumen en español

Comportamiento seguro:
- El script continúa funcionando incluso si hay errores:
- Si falla la traducción -> usa siguiente método
- Si falla el resumen con IA -> usa siguiente método
- Si un equipo no existe -> se omite sin detener el programa
- Si no hay descripción  -> se salta el equipo

API utilizada:
- TheSportsDB (gratuita): https://www.thesportsdb.com
- OpenAI