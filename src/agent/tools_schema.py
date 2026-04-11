"""Tool definitions for the Anthropic Claude agent."""

from __future__ import annotations

TOOLS = [
    {
        "name": "get_enterprise_metrics",
        "description": (
            "Recupera metriche aggregate di utilizzo Copilot a livello enterprise "
            "per un giorno specifico o gli ultimi 28 giorni. Include dati su completions, "
            "chat IDE, chat GitHub.com, CLI e PR."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "day": {
                    "type": "string",
                    "description": "Data specifica YYYY-MM-DD. Se omesso, recupera gli ultimi 28 giorni.",
                },
                "period": {
                    "type": "string",
                    "enum": ["1-day", "28-day"],
                    "description": "Periodo del report: singolo giorno o ultimi 28 giorni",
                },
            },
        },
    },
    {
        "name": "get_organization_metrics",
        "description": "Recupera metriche aggregate di utilizzo Copilot a livello organizzazione.",
        "input_schema": {
            "type": "object",
            "properties": {
                "org": {"type": "string", "description": "Nome organizzazione GitHub"},
                "day": {"type": "string", "description": "Data YYYY-MM-DD (opzionale)"},
                "period": {"type": "string", "enum": ["1-day", "28-day"]},
            },
            "required": ["org"],
        },
    },
    {
        "name": "get_team_metrics",
        "description": (
            "Recupera metriche di utilizzo Copilot per un team specifico di un'organizzazione. "
            "Disponibile solo se il team ha almeno 5 membri con licenza attiva."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "org": {"type": "string"},
                "team_slug": {
                    "type": "string",
                    "description": "Slug del team (es: 'backend-team')",
                },
                "since": {"type": "string", "description": "Data inizio YYYY-MM-DD"},
                "until": {"type": "string", "description": "Data fine YYYY-MM-DD"},
            },
            "required": ["org", "team_slug"],
        },
    },
    {
        "name": "get_user_metrics",
        "description": (
            "Recupera metriche di utilizzo Copilot per singoli utenti "
            "dell'enterprise o organizzazione."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scope": {"type": "string", "enum": ["enterprise", "organization"]},
                "org": {
                    "type": "string",
                    "description": "Nome org (richiesto se scope=organization)",
                },
                "day": {"type": "string", "description": "Data YYYY-MM-DD"},
                "period": {"type": "string", "enum": ["1-day", "28-day"]},
            },
        },
    },
    {
        "name": "get_seat_info",
        "description": (
            "Recupera informazioni sulle licenze Copilot: seat totali, assegnati, "
            "attivi, inattivi, ultima attività per utente."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "org": {"type": "string", "description": "Nome organizzazione"},
            },
            "required": ["org"],
        },
    },
    {
        "name": "analyze_data",
        "description": (
            "Esegue analisi e calcoli sui dati già recuperati: trend temporali, "
            "confronti tra team, top/bottom performers, acceptance rate, rapporti di adozione. "
            "Usa questo tool dopo aver recuperato i dati grezzi."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "analysis_type": {
                    "type": "string",
                    "enum": [
                        "adoption_trend",
                        "engagement_breakdown",
                        "acceptance_rate_by_language",
                        "acceptance_rate_by_editor",
                        "top_users",
                        "inactive_users",
                        "team_comparison",
                        "feature_usage_distribution",
                        "loc_impact",
                        "pr_lifecycle_impact",
                        "cli_vs_ide_usage",
                        "custom",
                    ],
                },
                "params": {
                    "type": "object",
                    "description": "Parametri specifici dell'analisi (es: top_n, date_range, filter_by)",
                },
            },
            "required": ["analysis_type"],
        },
    },
    {
        "name": "generate_chart",
        "description": (
            "Genera un grafico dai dati analizzati. Per il terminale produce barre ASCII. "
            "Per il web produce grafici Plotly interattivi. Per export produce immagini PNG."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["line", "bar", "pie", "heatmap", "stacked_bar", "scatter", "table"],
                },
                "title": {"type": "string"},
                "data": {
                    "type": "object",
                    "description": "Dati da visualizzare con labels e values",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["terminal", "web", "png", "all"],
                    "description": "Dove rendere il grafico",
                },
            },
            "required": ["chart_type", "title", "data"],
        },
    },
    {
        "name": "export_report",
        "description": (
            "Esporta un report completo in formato file. "
            "Può includere tabelle, grafici e testo narrativo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["csv", "excel", "pdf"],
                    "description": "Formato di export",
                },
                "title": {"type": "string", "description": "Titolo del report"},
                "sections": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Sezioni del report con dati, grafici, note",
                },
                "filename": {
                    "type": "string",
                    "description": "Nome file di output (senza estensione)",
                },
            },
            "required": ["format", "title"],
        },
    },
    {
        "name": "get_org_structure_summary",
        "description": (
            "Recupera un riepilogo della struttura organizzativa caricata dal file Excel: "
            "distribuzione per fascia d'età, job family, location, livello organizzativo, genere. "
            "Utile per capire la composizione dell'organizzazione prima di incrociare con i dati Copilot."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "analyze_org_copilot_usage",
        "description": (
            "Analizza l'utilizzo di Copilot incrociando i dati GitHub con la struttura organizzativa. "
            "Permette di rispondere a domande come: utenti attivi per fascia d'età, per livello organizzativo "
            "(Sup Org Level 2-10), per job family, per location, per genere, per management level. "
            "Richiede che i dati utente GitHub siano già stati recuperati con get_user_metrics."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "group_by": {
                    "type": "string",
                    "enum": [
                        "age_range",
                        "gender",
                        "location",
                        "location_country",
                        "job_family",
                        "job_title",
                        "job_level",
                        "job_category",
                        "management_level",
                        "sup_org_level_2",
                        "sup_org_level_3",
                        "sup_org_level_4",
                        "sup_org_level_5",
                        "sup_org_level_6",
                        "sup_org_level_7",
                        "sup_org_level_8",
                        "sup_org_level_9",
                        "sup_org_level_10",
                    ],
                    "description": (
                        "Dimensione organizzativa per cui raggruppare. "
                        "Usa 'sup_org_level_N' per il livello N della gerarchia organizzativa."
                    ),
                },
                "metric": {
                    "type": "string",
                    "enum": [
                        "active_users",
                        "total_completions",
                        "total_chat_turns",
                        "total_lines_accepted",
                        "total_activity",
                        "acceptance_rate",
                    ],
                    "description": "Metrica da aggregare per ciascun gruppo",
                },
                "filter_field": {
                    "type": "string",
                    "description": "Campo opzionale su cui filtrare (es: 'sup_org_level_5')",
                },
                "filter_value": {
                    "type": "string",
                    "description": "Valore del filtro (es: nome di un'unità organizzativa)",
                },
            },
            "required": ["group_by"],
        },
    },
]
