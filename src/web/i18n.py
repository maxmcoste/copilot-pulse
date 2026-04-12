"""Internationalization — English / Italian translation strings for the web UI."""

from __future__ import annotations

TRANSLATIONS: dict[str, dict[str, str]] = {
    # ── Navbar ───────────────────────────────────────────────
    "nav_dashboard": {"en": "Dashboard", "it": "Dashboard"},
    "nav_chat": {"en": "Chat", "it": "Chat"},
    "nav_setup": {"en": "Setup", "it": "Setup"},
    "nav_settings": {"en": "Settings", "it": "Impostazioni"},

    # ── Settings page ────────────────────────────────────────
    "settings_title": {"en": "LLM Settings", "it": "Impostazioni LLM"},
    "settings_subtitle": {
        "en": "Configure the AI provider used by the chat assistant.",
        "it": "Configura il provider AI utilizzato dall'assistente chat.",
    },
    "settings_provider_label": {"en": "AI Provider", "it": "Provider AI"},
    "settings_anthropic": {"en": "Anthropic (Claude)", "it": "Anthropic (Claude)"},
    "settings_github_copilot": {"en": "GitHub Copilot", "it": "GitHub Copilot"},
    "settings_api_key": {"en": "Anthropic API Key", "it": "Chiave API Anthropic"},
    "settings_api_key_hint": {
        "en": "Leave blank to keep the current key.",
        "it": "Lascia vuoto per mantenere la chiave attuale.",
    },
    "settings_github_token_note": {
        "en": "The GitHub Copilot LLM provider requires a Personal Access Token (PAT) with Copilot access. This token is used only for AI chat calls — it does not affect GitHub API authentication (which uses your existing GitHub App or GITHUB_TOKEN configuration).",
        "it": "Il provider LLM GitHub Copilot richiede un Personal Access Token (PAT) con accesso Copilot. Questo token viene usato solo per le chiamate AI chat — non influisce sull'autenticazione alle API GitHub (che usa la configurazione GitHub App o GITHUB_TOKEN esistente).",
    },
    "settings_llm_github_token": {
        "en": "GitHub Token (for Copilot LLM only)",
        "it": "GitHub Token (solo per LLM Copilot)",
    },
    "settings_llm_github_token_hint": {
        "en": "A PAT with 'copilot' scope. Leave blank to keep the current token. This does NOT change how the dashboard authenticates to GitHub APIs.",
        "it": "Un PAT con scope 'copilot'. Lascia vuoto per mantenere il token attuale. Questo NON modifica l'autenticazione alle API GitHub del dashboard.",
    },
    "settings_model": {"en": "Model override", "it": "Modello personalizzato"},
    "settings_model_hint": {
        "en": "Leave blank to use the provider default.",
        "it": "Lascia vuoto per usare il modello predefinito del provider.",
    },
    "settings_endpoint": {"en": "Custom endpoint URL", "it": "URL endpoint personalizzato"},
    "settings_endpoint_hint": {
        "en": "Leave blank for the default (models.inference.ai.azure.com). Change only if your org uses a custom gateway.",
        "it": "Lascia vuoto per il default (models.inference.ai.azure.com). Modifica solo se la tua org usa un gateway personalizzato.",
    },
    "settings_save": {"en": "Save Settings", "it": "Salva impostazioni"},
    "settings_saved": {"en": "\u2713 Settings saved and provider updated.", "it": "\u2713 Impostazioni salvate e provider aggiornato."},
    "settings_error": {"en": "Error: ", "it": "Errore: "},
    "settings_current": {"en": "Active provider", "it": "Provider attivo"},
    "settings_default_model": {"en": "default", "it": "default"},
    "settings_anthropic_models": {"en": "Anthropic models: claude-sonnet-4-20250514, claude-opus-4-5, claude-haiku-4-5-20251001", "it": "Modelli Anthropic: claude-sonnet-4-20250514, claude-opus-4-5, claude-haiku-4-5-20251001"},
    "settings_copilot_models": {"en": "GitHub Copilot models: gpt-4o, gpt-4o-mini, o1, o3-mini", "it": "Modelli GitHub Copilot: gpt-4o, gpt-4o-mini, o1, o3-mini"},

    # ── Dashboard ────────────────────────────────────────────
    "dash_title": {"en": "Copilot Usage Dashboard", "it": "Copilot Usage Dashboard"},
    "dash_active_users": {"en": "Active Users", "it": "Utenti attivi"},
    "dash_engaged_users": {"en": "Engaged Users", "it": "Utenti coinvolti"},
    "dash_acceptance_rate": {"en": "Acceptance Rate", "it": "Acceptance Rate"},
    "dash_active_seats": {"en": "Active Seats", "it": "Seat attivi"},
    "dash_adoption_trend": {"en": "Adoption Trend (28 days)", "it": "Trend di adozione (28 giorni)"},
    "dash_feature_usage": {"en": "Feature Adoption (Unique Users)", "it": "Adozione funzionalita' (utenti unici)"},
    "dash_loading": {"en": "Loading...", "it": "Caricamento..."},
    "dash_suggested": {"en": "Suggested", "it": "Suggerito"},
    "dash_accepted": {"en": "Accepted", "it": "Accettato"},
    "dash_help_adoption": {
        "en": "Active Users: users who had at least one Copilot interaction (completion, chat, CLI) on that day.\n\nEngaged Users: users who used Copilot at least once in the rolling 28-day window ending on that day.\n\nMetrics have a ~2 business-day delay from actual activity. Telemetry must be enabled in the user's IDE.",
        "it": "Utenti attivi: utenti che hanno avuto almeno un'interazione con Copilot (completamento, chat, CLI) in quel giorno.\n\nUtenti coinvolti: utenti che hanno usato Copilot almeno una volta nella finestra mobile di 28 giorni che termina in quel giorno.\n\nLe metriche hanno un ritardo di ~2 giorni lavorativi rispetto all'attivita' reale. La telemetria deve essere abilitata nell'IDE.",
    },
    "dash_help_features": {
        "en": "Unique users who used each feature at least once in the last 28 days.\n\nCode Completions: inline ghost-text suggestions.\nAgent Mode: agentic multi-file coding sessions in the IDE.\nAgent Edits: autonomous file changes performed by Agent.\n\nChat — Ask / Custom / Edit / Plan / Other: chat panel interactions by mode.\nInline Chat: Cmd+I / Ctrl+I quick edits in the editor.\nCLI Sessions: gh copilot terminal sessions.\n\nUsing unique-user counts makes all features directly comparable regardless of how many interactions each generates.",
        "it": "Utenti unici che hanno usato ogni funzionalita' almeno una volta negli ultimi 28 giorni.\n\nCode Completions: suggerimenti ghost-text inline.\nAgent Mode: sessioni di coding agentiche multi-file nell'IDE.\nAgent Edits: modifiche file autonome eseguite dall'Agent.\n\nChat — Ask / Custom / Edit / Plan / Other: interazioni nel pannello chat per modalita'.\nInline Chat: modifiche rapide con Cmd+I / Ctrl+I nell'editor.\nCLI Sessions: sessioni terminale gh copilot.\n\nUsare utenti unici rende tutte le funzionalita' direttamente confrontabili.",
    },
    "dash_top_users": {"en": "Top 10 Active Users (28 days)", "it": "Top 10 utenti attivi (28 giorni)"},
    "dash_suggested_vs_accepted": {"en": "Suggested vs Accepted Code (14 days)", "it": "Codice suggerito vs accettato (14 giorni)"},
    "dash_usage_trend": {"en": "28-Day Usage Trend", "it": "Trend di utilizzo (28 giorni)"},
    "dash_help_top_users": {
        "en": "Top 10 users ranked by total activity: code suggestions + chat turns + CLI interactions over the last 28 days.\n\nThis helps identify power users and adoption champions in your organization.",
        "it": "Top 10 utenti per attivita' totale: suggerimenti codice + turni chat + interazioni CLI negli ultimi 28 giorni.\n\nAiuta a identificare i power user e i campioni di adozione nella tua organizzazione.",
    },
    "dash_help_suggested_accepted": {
        "en": "Code Suggestions: total inline completions shown to users each day.\n\nCode Acceptances: suggestions that were accepted (Tab/Enter).\n\nThe gap between the two lines shows how much generated code is being discarded. A narrowing gap means developers trust Copilot more.",
        "it": "Suggerimenti codice: completamenti inline mostrati agli utenti ogni giorno.\n\nAccettazioni codice: suggerimenti accettati (Tab/Invio).\n\nIl divario tra le due linee mostra quanto codice generato viene scartato. Un divario che si riduce indica maggiore fiducia in Copilot.",
    },
    "dash_help_usage_trend": {
        "en": "Usage Score: a composite metric that sums all Copilot interactions per day — code suggestions + chat messages + PR summaries + CLI commands.\n\nThis gives a single-glance view of overall Copilot engagement across the organization. Rising trends indicate growing adoption.",
        "it": "Usage Score: metrica composita che somma tutte le interazioni Copilot per giorno — suggerimenti codice + messaggi chat + riepiloghi PR + comandi CLI.\n\nFornisce una visione d'insieme del coinvolgimento Copilot nell'organizzazione. Trend in crescita indicano un'adozione crescente.",
    },
    "roi_title": {"en": "ROI Calculator (28d)", "it": "Calcolatore ROI (28d)"},
    "roi_help": {
        "en": "Estimates the economic value of Copilot Agent based on time saved.\n\nFormula: Agent_Edits x (minutes_per_edit / 60) x (1 - review_factor) x hourly_rate.\n\nDefault assumptions:\n- 10 min saved per autonomous edit\n- 20% deducted for human review\n- 60 EUR/hour developer cost\n- 39 EUR/month per license\n\nAll parameters are adjustable. The calculation is based on the last 28 days of actual data.",
        "it": "Stima il valore economico di Copilot Agent basandosi sul tempo risparmiato.\n\nFormula: Agent_Edits x (minuti_per_edit / 60) x (1 - fattore_revisione) x costo_orario.\n\nAssunzioni di default:\n- 10 min risparmiati per edit autonomo\n- 20% dedotto per revisione umana\n- 60 EUR/ora costo sviluppatore\n- 39 EUR/mese per licenza\n\nTutti i parametri sono modificabili. Il calcolo si basa sugli ultimi 28 giorni di dati reali.",
    },
    "roi_params": {"en": "Parameters", "it": "Parametri"},
    "roi_hourly_rate": {"en": "Developer hourly rate", "it": "Costo orario sviluppatore"},
    "roi_license_cost": {"en": "License cost per user", "it": "Costo licenza per utente"},
    "roi_min_per_edit": {"en": "Minutes saved per edit", "it": "Minuti risparmiati per edit"},
    "roi_review_factor": {"en": "Human review overhead", "it": "Overhead revisione umana"},
    "roi_formula": {"en": "Formula", "it": "Formula"},
    "roi_estimated_value": {"en": "Estimated value", "it": "Valore stimato"},
    "roi_license_total": {"en": "License cost", "it": "Costo licenze"},
    "roi_net": {"en": "Net value", "it": "Valore netto"},
    "roi_value_per_seat": {"en": "Value per seat", "it": "Valore per seat"},
    "dash_agent_edits_wow": {"en": "Agent Edits / User — Week over Week (13w)", "it": "Agent Edits / Utente — Settimana per settimana (13s)"},
    "dash_help_agent_edits_wow": {
        "en": "Weekly trend of autonomous code edits per active user (agent_edit / monthly_active_users), sampled every Wednesday for the last 13 weeks.\n\nReference bands:\n< 10 (red): Cautious / Legacy — low agent usage, minimal ROI.\n10–50 (yellow): Standard Adopters — healthy integration, AI writes parts of logic.\n50–100 (green): Advanced — significant agent-driven development.\n> 100 (blue): Agent-First / Power Users — massive agent usage, highest ROI.",
        "it": "Trend settimanale delle modifiche autonome per utente attivo (agent_edit / monthly_active_users), campionato ogni mercoledi' per le ultime 13 settimane.\n\nBande di riferimento:\n< 10 (rosso): Cautious / Legacy — uso minimo dell'agent, ROI basso.\n10–50 (giallo): Standard Adopters — integrazione sana, l'IA scrive parti di logica.\n50–100 (verde): Advanced — sviluppo significativo guidato dall'agent.\n> 100 (blu): Agent-First / Power Users — uso massivo dell'agent, ROI altissimo.",
    },
    "dash_adoption_title": {"en": "CLI & Agent Adoption", "it": "Adozione CLI & Agent"},
    "dash_productivity_title": {"en": "Productivity Insights", "it": "Productivity Insights"},
    "dash_productivity_subtitle": {
        "en": "Compare productivity depth vs breadth and track weekly Agent Edits / User.",
        "it": "Confronta profondita' e ampiezza della produttivita' e monitora gli Agent Edits / Utente settimanali.",
    },
    "dash_productivity_trend": {
        "en": "Agent Edits / User — Weekly Trend (13 weeks)",
        "it": "Agent Edits / Utente — Trend settimanale (13 settimane)",
    },
    "dash_help_productivity_trend": {
        "en": "Weekly trend of autonomous code edits per active user, sampled every Wednesday for the last 13 weeks.\n\nThreshold bands are scaled dynamically using your organization's active seat ratio (avg active users \u00f7 total seats), so each band represents equivalent adoption breadth across all licensed seats:\nRed \u2014 Cautious / Legacy\nYellow \u2014 Standard Adopters\nGreen \u2014 Advanced\nBlue \u2014 Agent-First / Power Users",
        "it": "Trend settimanale delle modifiche autonome per utente attivo, campionato ogni mercoledi' per le ultime 13 settimane.\n\nLe soglie sono scalate dinamicamente in base al rapporto tra utenti attivi e totale licenze (media utenti attivi \u00f7 totale licenze), in modo che ogni banda rappresenti un'ampiezza di adozione equivalente sull'intera base licenziata:\nRosso \u2014 Cautious / Legacy\nGiallo \u2014 Standard Adopters\nVerde \u2014 Advanced\nBlu \u2014 Agent-First / Power Users",
    },
    "dash_productivity_trend_seats": {
        "en": "Agent Edits / Total Seats — Weekly Trend (13 weeks)",
        "it": "Agent Edits / Totale Licenze — Trend settimanale (13 settimane)",
    },
    "dash_help_productivity_trend_seats": {
        "en": "Weekly trend of autonomous code edits per licensed seat, sampled every Wednesday for the last 13 weeks.\n\nUnlike the Active Users chart, the denominator here is fixed (total seats), measuring breadth of adoption across the entire licensed population.",
        "it": "Trend settimanale delle modifiche autonome per licenza, campionato ogni mercoledi' per le ultime 13 settimane.\n\nA differenza del grafico per Utenti Attivi, il denominatore e' fisso (totale licenze), misurando l'ampiezza dell'adozione sull'intera base di utenti licenziati.",
    },
    "product_efficiency_title": {"en": "Agent Effectiveness", "it": "Efficacia Agente"},
    "product_efficiency_desc": {
        "en": "Agent Edits divided by active users over the last 28 days.",
        "it": "Agent Edits diviso Utenti Attivi negli ultimi 28 giorni.",
    },
    "product_real_adoption_title": {"en": "Real Adoption", "it": "Adozione Reale"},
    "product_real_adoption_desc": {
        "en": "Agent Edits divided by total licenses to expose true adoption breadth.",
        "it": "Agent Edits diviso Totale Licenze per evidenziare la reale ampiezza dell'adozione.",
    },
    "product_badge_advanced": {"en": "Advanced", "it": "Advanced"},
    "product_agent_edits": {"en": "Agent Edits", "it": "Agent Edits"},
    "product_active_users": {"en": "Active Users", "it": "Utenti Attivi"},
    "product_total_licenses": {"en": "Total Licenses", "it": "Totale Licenze"},
    "product_weekly_average": {"en": "13w avg", "it": "Media 13s"},
    "product_scale_cautious": {"en": "Cautious / Legacy", "it": "Cautious / Legacy"},
    "product_scale_standard": {"en": "Standard Adopters", "it": "Standard Adopters"},
    "product_scale_advanced": {"en": "Advanced", "it": "Advanced"},
    "product_scale_agent_first": {"en": "Agent-First / Power Users", "it": "Agent-First / Power Users"},
    "adopt_cli_users": {"en": "CLI Users", "it": "Utenti CLI"},
    "adopt_cli_users_desc": {
        "en": "Developers who used gh copilot today. Indicates base adoption of the CLI tool.",
        "it": "Sviluppatori che hanno usato gh copilot oggi. Indica l'adozione base dello strumento CLI.",
    },
    "adopt_cli_sessions": {"en": "CLI Sessions", "it": "Sessioni CLI"},
    "adopt_cli_sessions_desc": {
        "en": "Terminal sessions started with gh copilot. Measures how often devs prefer CLI over IDE.",
        "it": "Sessioni avviate nel terminale con gh copilot. Misura quanto spesso i dev preferiscono la CLI all'IDE.",
    },
    "adopt_agent_users": {"en": "Coding Agent Users", "it": "Utenti Coding Agent"},
    "adopt_agent_users_desc": {
        "en": "Developers who used Copilot as an autonomous agent for complex tasks (e.g. building entire apps).",
        "it": "Sviluppatori che hanno usato Copilot come agente autonomo per task complessi (es. creazione intere app).",
    },
    "adopt_cli_tokens": {"en": "CLI Tokens", "it": "Token CLI"},
    "adopt_cli_tokens_desc": {
        "en": "Total tokens exchanged in CLI sessions. High volume indicates complex tasks (writing entire files).",
        "it": "Token totali scambiati nelle sessioni CLI. Un alto volume indica task complessi (scrittura di file interi).",
    },
    "adopt_agent_edits_per_user": {"en": "Agent Edits / User", "it": "Agent Edits / Utente"},
    "adopt_agent_edits_per_user_desc": {
        "en": "Average autonomous code edits per active user. Higher values mean the agent is doing more heavy lifting.",
        "it": "Media di modifiche autonome per utente attivo. Valori alti indicano che l'agent sta facendo piu' lavoro pesante.",
    },
    "dash_insights_title": {"en": "Quick Insights", "it": "Insight rapidi"},
    "insight_top_langs": {"en": "Top 5 languages", "it": "Top 5 linguaggi"},
    "insight_top_models": {"en": "Top 5 models", "it": "Top 5 modelli"},
    "insight_top_ide": {"en": "Top IDE", "it": "IDE principale"},
    "insight_acc_trend": {"en": "Acceptance rate (7d trend)", "it": "Acceptance rate (trend 7gg)"},
    "insight_peak_day": {"en": "Peak day", "it": "Giorno di picco"},
    "insight_seat_util": {"en": "Seat utilization", "it": "Utilizzo seat"},

    # ── Chat ─────────────────────────────────────────────────
    "chat_greeting": {
        "en": "Hi! I'm your Copilot analyst. Ask me anything about GitHub Copilot usage in your organization.",
        "it": "Ciao! Sono il tuo analista Copilot. Chiedimi qualsiasi cosa sull'utilizzo di GitHub Copilot nella tua organizzazione.",
    },
    "chat_placeholder": {"en": "Type a question...", "it": "Scrivi una domanda..."},
    "chat_send": {"en": "Send", "it": "Invia"},
    "chat_analyzing": {"en": "Analyzing...", "it": "Analizzo..."},
    "chat_conn_lost": {"en": "Connection lost. Reload the page.", "it": "Connessione persa. Ricarica la pagina."},
    "chat_open_chat": {"en": "Open the Chat section to ask questions.", "it": "Apri la sezione Chat per fare domande."},

    # ── Setup — header & stepper ─────────────────────────────
    "setup_title": {"en": "Setup — Cross-Dimensional Analysis", "it": "Setup — Analisi incrociate"},
    "setup_subtitle": {
        "en": "Import the org structure and map GitHub users to enable cross-dimensional queries",
        "it": "Importa la struttura organizzativa e mappa gli utenti GitHub per abilitare le analisi incrociate",
    },
    "setup_step_import": {"en": "Import org structure", "it": "Importa struttura org"},
    "setup_step_usage": {"en": "Load Copilot data", "it": "Carica dati Copilot"},
    "setup_step_map": {"en": "Map users", "it": "Mappa utenti"},
    "setup_step_analyze": {"en": "Analyze", "it": "Analizza"},

    # ── Setup — KPI labels ───────────────────────────────────
    "setup_kpi_employees": {"en": "Imported employees", "it": "Dipendenti importati"},
    "setup_kpi_copilot_users": {"en": "Copilot users", "it": "Utenti Copilot"},
    "setup_kpi_matched": {"en": "Matched users", "it": "Utenti mappati"},
    "setup_kpi_match_rate": {"en": "Match rate", "it": "Match rate"},

    # ── Setup — Step 1: import ───────────────────────────────
    "import_title": {"en": "1. Import org structure", "it": "1. Importa struttura organizzativa"},
    "import_employees": {"en": "employees", "it": "dipendenti"},
    "import_desc": {
        "en": "Upload the Excel file (.xlsx) with the org structure. It will be imported into the local SQLite database.",
        "it": "Carica il file Excel (.xlsx) con la struttura organizzativa. Il file verra' letto e importato nel database SQLite locale.",
    },
    "import_drag": {"en": "Drag the Excel file here or", "it": "Trascina il file Excel qui oppure"},
    "import_choose": {"en": "Choose file", "it": "Scegli file"},
    "import_uploading": {"en": "Uploading file...", "it": "Caricamento file..."},
    "import_importing": {"en": "Importing...", "it": "Importazione in corso..."},
    "import_done": {"en": "Done!", "it": "Completato!"},
    "import_error": {"en": "Error", "it": "Errore"},
    "import_success": {"en": "Imported {n} employees into the database.", "it": "Importati {n} dipendenti nel database."},
    "import_unknown_error": {"en": "Unknown error", "it": "Errore sconosciuto"},
    "import_refresh_all": {"en": "Refresh all structure(s)", "it": "Aggiorna tutta la struttura"},
    "import_refresh_hint": {
        "en": "Replaces the entire org structure — existing GitHub mappings will be lost",
        "it": "Sostituisce l'intera struttura org — le mappature GitHub esistenti andranno perse",
    },
    "import_refresh_warning": {
        "en": "This will delete the entire existing organization structure, including all GitHub user mappings. This action cannot be undone. Continue?",
        "it": "Questa operazione cancellera' l'intera struttura organizzativa esistente, incluse tutte le mappature utenti GitHub. L'azione non puo' essere annullata. Continuare?",
    },
    "import_btn": {"en": "Import", "it": "Importa"},
    "import_analyze": {"en": "Analyse structure", "it": "Analizza struttura"},
    "import_analyzing": {"en": "Analysing file...", "it": "Analisi file in corso..."},
    "import_preview_title": {"en": "Column preview", "it": "Anteprima colonne"},
    "import_col_list_title": {"en": "Columns found", "it": "Colonne trovate"},
    "import_col_required": {"en": "Required", "it": "Obbligatorio"},
    "import_col_mapped": {"en": "Mapped", "it": "Mappato"},
    "import_col_unmapped": {"en": "Not recognised", "it": "Non riconosciuto"},
    "import_missing_required": {
        "en": "Required fields missing from file — import blocked: ",
        "it": "Campi obbligatori mancanti nel file — import bloccato: ",
    },
    "import_sample_preview": {"en": "Sample data", "it": "Dati di esempio"},
    "import_sample_rows": {"en": "rows", "it": "righe"},
    "import_proceed": {"en": "Proceed with import", "it": "Procedi con l'import"},
    "import_cancel": {"en": "Cancel", "it": "Annulla"},
    "import_preserved": {
        "en": "{n} GitHub mappings preserved.",
        "it": "{n} mappature GitHub preservate.",
    },

    # ── Setup — Step 2: usage ────────────────────────────────
    "usage_title": {"en": "2. Load Copilot usage data", "it": "2. Carica dati utilizzo Copilot"},
    "usage_users": {"en": "users", "it": "utenti"},
    "usage_desc": {
        "en": "Copilot usage data is downloaded automatically from GitHub APIs when you ask a question in Chat. Go to the <a href=\"/chat\">Chat</a> and ask for example:",
        "it": "I dati di utilizzo Copilot vengono scaricati automaticamente dalle API GitHub quando fai una domanda nella Chat. Vai alla <a href=\"/chat\">Chat</a> e chiedi ad esempio:",
    },
    "usage_example1": {
        "en": "Show me the org user metrics",
        "it": "Mostrami le metriche utente dell'organizzazione",
    },
    "usage_example2": {
        "en": "Who are the most active users?",
        "it": "Chi sono gli utenti piu' attivi?",
    },
    "usage_no_data": {
        "en": "No usage data available. <a href=\"/chat\">Open the Chat</a> and ask for user metrics.",
        "it": "Nessun dato di utilizzo presente. <a href=\"/chat\">Apri la Chat</a> e chiedi le metriche utente.",
    },
    "usage_loaded": {
        "en": "{n} Copilot users loaded into the database.",
        "it": "{n} utenti Copilot caricati nel database.",
    },

    # ── Setup — Step 3: mapping ──────────────────────────────
    "map_title": {"en": "3. Map GitHub users → Employees", "it": "3. Mappa utenti GitHub → Dipendenti"},
    "map_matched": {"en": "matched", "it": "mappati"},
    "map_desc": {
        "en": "Associate GitHub logins with employees in the org database. You can use automatic mapping (by email) or manual.",
        "it": "Associa i login GitHub ai dipendenti nel database organizzativo. Puoi usare il mapping automatico (per email) o manuale.",
    },
    "map_auto_title": {"en": "Automatic mapping", "it": "Mapping automatico"},
    "map_auto_desc": {
        "en": "Tries to match GitHub logins to employees via email patterns (e.g. <code>mario.rossi</code> → <code>MARIO.ROSSI@company.com</code>).",
        "it": "Tenta di associare i login GitHub ai dipendenti tramite pattern email (es. <code>mario.rossi</code> → <code>MARIO.ROSSI@company.com</code>).",
    },
    "map_pattern_label": {"en": "Email pattern", "it": "Pattern email"},
    "map_pattern_desc": {
        "en": "Choose how your organization builds email addresses from employee names.",
        "it": "Scegli come la tua organizzazione costruisce gli indirizzi email a partire dai nomi dei dipendenti.",
    },
    "map_pattern_ns": {"en": "name.surname", "it": "nome.cognome"},
    "map_pattern_sn": {"en": "surname.name", "it": "cognome.nome"},
    "map_pattern_n1s": {"en": "n.surname (first initial)", "it": "n.cognome (iniziale nome)"},
    "map_pattern_example": {"en": "Example", "it": "Esempio"},
    "map_dup_label": {"en": "Duplicate handling", "it": "Gestione duplicati"},
    "map_dup_desc": {
        "en": "When multiple employees produce the same email pattern (e.g. two \"Mario Rossi\"):",
        "it": "Quando piu' dipendenti producono lo stesso pattern email (es. due \"Mario Rossi\"):",
    },
    "map_dup_skip": {"en": "Skip — do not match (safest)", "it": "Salta — non associare (piu' sicuro)"},
    "map_dup_seq2": {
        "en": "Sequence number — match name.surname.01, name.surname.02, etc.",
        "it": "Numero sequenza — associa nome.cognome.01, nome.cognome.02, ecc.",
    },
    "map_dup_first": {"en": "First match — pick the first employee found", "it": "Primo risultato — prendi il primo dipendente trovato"},
    "map_auto_btn": {"en": "Run auto-mapping", "it": "Avvia auto-mapping"},
    "map_auto_running": {"en": "Mapping in progress...", "it": "Mapping in corso..."},
    "map_auto_no_match": {
        "en": "No new matches found. Try manual mapping.",
        "it": "Nessuna nuova corrispondenza trovata. Prova il mapping manuale.",
    },
    "map_auto_found": {
        "en": "{n} new matches found:",
        "it": "{n} nuove corrispondenze trovate:",
    },
    "map_manual_title": {"en": "Manual mapping", "it": "Mapping manuale"},
    "map_manual_search": {"en": "Search employee", "it": "Cerca dipendente"},
    "map_manual_placeholder": {
        "en": "Name, surname or employee ID...",
        "it": "Nome, cognome o ID dipendente...",
    },
    "map_manual_gh_label": {"en": "GitHub Login", "it": "GitHub Login"},
    "map_manual_gh_placeholder": {"en": "e.g. mario-rossi", "it": "es. mario-rossi"},
    "map_manual_btn": {"en": "Associate", "it": "Associa"},
    "map_manual_missing": {
        "en": "Select an employee and enter the GitHub login.",
        "it": "Seleziona un dipendente e inserisci il GitHub login.",
    },
    "map_manual_ok": {"en": "Mapped: {v}", "it": "Mappato: {v}"},
    "map_unmatched_title": {"en": "Unmatched GitHub users", "it": "Utenti GitHub non mappati"},
    "map_unmatched_btn": {"en": "Show unmatched users", "it": "Mostra utenti non mappati"},
    "map_unmatched_all_ok": {"en": "All GitHub users are matched!", "it": "Tutti gli utenti GitHub sono mappati!"},
    "map_unmatched_count": {
        "en": "{n} unmatched users:",
        "it": "{n} utenti non mappati:",
    },
    "map_by_method_title": {"en": "Mappings by method", "it": "Mappature per metodo"},
    "map_th_method": {"en": "Method", "it": "Metodo"},
    "map_th_count": {"en": "Count", "it": "Conteggio"},

    # ── Setup — Step 4: analyze ──────────────────────────────
    "analyze_title": {"en": "4. Cross-dimensional analysis", "it": "4. Analisi incrociate"},
    "analyze_ready": {"en": "Ready", "it": "Pronto"},
    "analyze_desc": {
        "en": "Once users are mapped, you can ask cross-dimensional questions in Chat. Examples:",
        "it": "Una volta mappati gli utenti, puoi fare domande incrociate nella Chat. Esempi:",
    },
    "analyze_ex1": {
        "en": "How many active users by age range?",
        "it": "Quanti utenti attivi per fascia d'eta'?",
    },
    "analyze_ex2": {
        "en": "Acceptance rate by Sup Org Level 6",
        "it": "Acceptance rate per Sup Org Level 6",
    },
    "analyze_ex3": {
        "en": "Usage distribution by job family",
        "it": "Distribuzione utilizzo per job family",
    },
    "analyze_ex4": {
        "en": "Active users by location",
        "it": "Utenti attivi per location",
    },
    "analyze_go_chat": {"en": "Go to Chat", "it": "Vai alla Chat"},
    "analyze_complete_steps": {
        "en": "Complete the previous steps to enable cross-dimensional analysis.",
        "it": "Completa i passi precedenti per abilitare le analisi incrociate.",
    },

    # ── Misc / shared ────────────────────────────────────────
    "error_prefix": {"en": "Error", "it": "Errore"},
}


def get_translations(lang: str) -> dict[str, str]:
    """Return a flat dict of translation key → string for the given language.

    Args:
        lang: Language code ('en' or 'it').

    Returns:
        Dict mapping translation keys to strings.
    """
    if lang not in ("en", "it"):
        lang = "en"
    return {key: vals.get(lang, vals["en"]) for key, vals in TRANSLATIONS.items()}
