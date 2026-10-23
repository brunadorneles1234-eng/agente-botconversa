# Agente Botconversa — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir um agente Python local que coleta dados diários da API do Botconversa, calcula métricas de atendimento respeitando LGPD, e gera um dashboard HTML com exportação de PDF para múltiplos clientes.

**Architecture:** Script Python executado diariamente via Windows Task Scheduler que, para cada cliente configurado, chama a API do Botconversa, anonimiza dados pessoais imediatamente, calcula métricas, detecta alertas e gera um dashboard HTML estático com opção de exportação PDF filtrada.

**Tech Stack:** Python 3.10+, `requests` (API), `jinja2` (HTML/PDF), `weasyprint` (PDF), `pytest` (testes), Windows Task Scheduler (agendamento).

**Spec:** `docs/superpowers/specs/2026-10-23-agente-botconversa-design.md`

## Global Constraints

- Python 3.10+ obrigatório
- Dados pessoais (nome, telefone, conteúdo de mensagens) NUNCA persistidos em disco
- Anonimização deve ocorrer antes de qualquer gravação
- Cada cliente isolado em sua própria pasta em `config/` e `dados/`
- Dashboard gerado como arquivo HTML estático (sem servidor web)
- Tempo de alerta padrão configurável via `config.json` (default: 5 min IA, 10 min equipe)
- Compatível com Windows 10/11

## Review Focus

- **API do Botconversa indisponível:** coleta falha graciosamente, registra em `logs/erros.log`, não sobrescreve o último dashboard válido
- **config.json inválido ou ausente:** agente loga o erro e pula o cliente, não interrompe os demais
- **Primeiro dia de uso (sem histórico):** dashboard de tendência exibe "dados insuficientes" sem erro
- **Conversa sem transferência para equipe:** métricas de "tempo até equipe assumir" registradas como `null`, não como zero
- **Múltiplos clientes com erro simultâneo:** cada cliente processado independentemente, um erro não bloqueia os demais

---

## Estrutura de Arquivos

```
agente-botconversa/
├── run.py                          # Orquestrador principal
├── setup_windows.py                # Configuração inicial (Task Scheduler + dependências)
├── config/
│   └── cliente_exemplo/
│       └── config.json             # Template de configuração
├── src/
│   ├── config_loader.py            # Lê e valida config.json
│   ├── collector.py                # Chama API Botconversa
│   ├── anonymizer.py               # Anonimização LGPD
│   ├── analyzer.py                 # Cálculo de métricas
│   ├── alert_detector.py           # Detecção de alertas
│   ├── dashboard_generator.py      # Geração do HTML
│   └── pdf_exporter.py             # Exportação PDF com filtros
├── templates/
│   ├── dashboard.html              # Template Jinja2 do dashboard
│   └── report_pdf.html             # Template Jinja2 do PDF
├── dados/                          # Criado automaticamente
├── relatorios/                     # Criado automaticamente
├── logs/                           # Criado automaticamente
└── tests/
    ├── test_config_loader.py
    ├── test_anonymizer.py
    ├── test_analyzer.py
    ├── test_alert_detector.py
    └── test_dashboard_generator.py
```

---

### Task 1: Setup do Projeto e Config Loader

**Files:**
- Create: `agente-botconversa/src/config_loader.py`
- Create: `agente-botconversa/config/cliente_exemplo/config.json`
- Create: `agente-botconversa/tests/test_config_loader.py`

**Interfaces:**
- Produz: `load_config(client_folder: str) -> dict` — retorna config validado ou lança `ConfigError`
- Produz: `list_clients(base_path: str) -> list[str]` — retorna lista de nomes de pastas em `config/`

- [ ] **Step 1: Criar estrutura de pastas do projeto**

```bash
mkdir -p agente-botconversa/src agente-botconversa/config/cliente_exemplo agente-botconversa/templates agente-botconversa/dados agente-botconversa/relatorios agente-botconversa/logs agente-botconversa/tests
```

- [ ] **Step 2: Criar `config/cliente_exemplo/config.json`**

```json
{
  "nome_cliente": "Cliente Exemplo",
  "botconversa_api_key": "SUA_CHAVE_AQUI",
  "tempo_alerta_ia_minutos": 5,
  "tempo_alerta_equipe_minutos": 10,
  "unidades": {
    "fluxo_abc123": "Unidade Centro",
    "fluxo_def456": "Unidade Norte"
  },
  "atendentes": {
    "user_001": "Unidade Centro",
    "user_002": "Unidade Norte"
  }
}
```

- [ ] **Step 3: Escrever testes falhando em `tests/test_config_loader.py`**

```python
def test_load_config_valid():
    config = load_config("tests/fixtures/valid_client")
    assert config["nome_cliente"] == "Cliente Teste"
    assert config["botconversa_api_key"] == "key_test_123"
    assert config["tempo_alerta_ia_minutos"] == 5

def test_load_config_missing_file():
    with pytest.raises(ConfigError):
        load_config("tests/fixtures/nonexistent_client")

def test_load_config_missing_api_key():
    with pytest.raises(ConfigError, match="botconversa_api_key"):
        load_config("tests/fixtures/invalid_client")

def test_list_clients():
    clients = list_clients("tests/fixtures/multi_client")
    assert "cliente_a" in clients
    assert "cliente_b" in clients
```

- [ ] **Step 4: Rodar testes para confirmar que falham**

```bash
cd agente-botconversa && pytest tests/test_config_loader.py -v
```
Esperado: FAIL com "ModuleNotFoundError" ou "ImportError"

- [ ] **Step 5: Implementar `src/config_loader.py`**

Campos obrigatórios a validar: `nome_cliente`, `botconversa_api_key`, `unidades`, `atendentes`. Usar defaults `5` e `10` para os tempos de alerta se ausentes. `ConfigError` é subclasse de `Exception`.

- [ ] **Step 6: Criar fixtures de teste** em `tests/fixtures/` com pastas `valid_client/`, `invalid_client/` e `multi_client/`

- [ ] **Step 7: Rodar testes para confirmar que passam**

```bash
pytest tests/test_config_loader.py -v
```
Esperado: 4 PASS

- [ ] **Step 8: Commit**

```bash
git add agente-botconversa/
git commit -m "feat: project structure and config loader"
```

---

### Task 2: Anonimizador LGPD

**Files:**
- Create: `agente-botconversa/src/anonymizer.py`
- Create: `agente-botconversa/tests/test_anonymizer.py`

**Interfaces:**
- Consome: raw conversation dict da API Botconversa
- Produz: `anonymize_conversation(conv: dict) -> dict` — retorna conversa sem dados pessoais, com `anon_id` no lugar de identificadores

- [ ] **Step 1: Escrever testes falhando**

```python
def test_anonymize_removes_phone():
    raw = {"id": "conv_123", "contact_phone": "51999999999", "messages": [...]}
    result = anonymize_conversation(raw)
    assert "contact_phone" not in result
    assert "contact_name" not in result

def test_anonymize_preserves_anon_id():
    raw = {"id": "conv_123", "contact_phone": "51999999999"}
    result = anonymize_conversation(raw)
    assert result["anon_id"].startswith("conv_")
    assert result["anon_id"] != "conv_123"

def test_anonymize_same_input_same_output():
    raw = {"id": "conv_123", "contact_phone": "51999999999"}
    assert anonymize_conversation(raw)["anon_id"] == anonymize_conversation(raw)["anon_id"]

def test_anonymize_removes_message_content():
    raw = {"id": "c1", "messages": [{"text": "meu cpf é 123", "sender": "contact"}]}
    result = anonymize_conversation(raw)
    assert "text" not in result["messages"][0]
    assert result["messages"][0]["sender"] == "contact"
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
pytest tests/test_anonymizer.py -v
```

- [ ] **Step 3: Implementar `src/anonymizer.py`**

Campos a remover: `contact_phone`, `contact_name`, `contact_email`, `contact_cpf` e qualquer campo `text`/`content` de mensagens. `anon_id` = `hmac-sha256(id, salt="botconv_lgpd")[:12]` prefixado com `"conv_"`. Salt fixo (não segredo — serve só para desidentificação, não criptografia).

- [ ] **Step 4: Rodar testes**

```bash
pytest tests/test_anonymizer.py -v
```
Esperado: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add agente-botconversa/src/anonymizer.py agente-botconversa/tests/test_anonymizer.py
git commit -m "feat: LGPD anonymizer strips personal data before storage"
```

---

### Task 3: Coletor da API Botconversa

**Files:**
- Create: `agente-botconversa/src/collector.py`
- Create: `agente-botconversa/tests/test_collector.py`

**Interfaces:**
- Consome: `load_config()` de Task 1, `anonymize_conversation()` de Task 2
- Produz: `collect_conversations(api_key: str, date: str) -> list[dict]` — lista de conversas anonimizadas do dia (`date` formato `"YYYY-MM-DD"`)

- [ ] **Step 1: Escrever testes com mock da API**

```python
def test_collect_returns_anonymized(requests_mock):
    requests_mock.get(
        "https://api.botconversa.com.br/v1/conversations",
        json={"data": [{"id": "c1", "contact_phone": "51999", "flow_id": "f1", ...}]}
    )
    result = collect_conversations("test_key", "2026-10-22")
    assert len(result) == 1
    assert "contact_phone" not in result[0]
    assert "anon_id" in result[0]

def test_collect_api_error_raises(requests_mock):
    requests_mock.get("https://api.botconversa.com.br/v1/conversations", status_code=401)
    with pytest.raises(CollectorError, match="401"):
        collect_conversations("bad_key", "2026-10-22")

def test_collect_empty_day(requests_mock):
    requests_mock.get("...", json={"data": []})
    result = collect_conversations("test_key", "2026-10-22")
    assert result == []
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
pytest tests/test_collector.py -v
```

- [ ] **Step 3: Implementar `src/collector.py`**

Endpoint base: `https://api.botconversa.com.br/v1/` (confirmar na documentação oficial). Header de auth: `Authorization: Bearer {api_key}`. Paginação: iterar enquanto houver `next_page`. Chamar `anonymize_conversation()` em cada item antes de retornar. `CollectorError` é subclasse de `Exception`.

- [ ] **Step 4: Rodar testes**

```bash
pytest tests/test_collector.py -v
```
Esperado: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add agente-botconversa/src/collector.py agente-botconversa/tests/test_collector.py
git commit -m "feat: Botconversa API collector with anonymization"
```

---

### Task 4: Analisador de Métricas

**Files:**
- Create: `agente-botconversa/src/analyzer.py`
- Create: `agente-botconversa/tests/test_analyzer.py`

**Interfaces:**
- Consome: lista de conversas anonimizadas de `collect_conversations()`
- Produz: `analyze(conversations: list[dict], config: dict) -> dict` — métricas completas do dia

- [ ] **Step 1: Escrever testes**

```python
def test_analyze_total_conversations():
    convs = [make_conv(), make_conv(), make_conv()]
    result = analyze(convs, config=SAMPLE_CONFIG)
    assert result["total_conversations"] == 3

def test_analyze_ai_response_time():
    convs = [make_conv(ai_response_seconds=120), make_conv(ai_response_seconds=60)]
    result = analyze(convs, config=SAMPLE_CONFIG)
    assert result["avg_ai_response_seconds"] == 90

def test_analyze_team_takeover_time():
    # Conversa com transferência em 300s, outra sem transferência
    convs = [make_conv(team_takeover_seconds=300), make_conv(team_takeover_seconds=None)]
    result = analyze(convs, config=SAMPLE_CONFIG)
    assert result["avg_team_takeover_seconds"] == 300  # Ignora None

def test_analyze_by_unit():
    convs = [make_conv(flow_id="f1"), make_conv(flow_id="f1"), make_conv(flow_id="f2")]
    config = {"unidades": {"f1": "Centro", "f2": "Norte"}, ...}
    result = analyze(convs, config=config)
    assert result["by_unit"]["Centro"]["total"] == 2
    assert result["by_unit"]["Norte"]["total"] == 1

def test_analyze_by_attendant():
    convs = [make_conv(attendant_id="u1"), make_conv(attendant_id="u1")]
    result = analyze(convs, config=SAMPLE_CONFIG)
    assert result["by_attendant"]["u1"]["total"] == 2
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
pytest tests/test_analyzer.py -v
```

- [ ] **Step 3: Implementar `src/analyzer.py`**

Estrutura do retorno:
```python
{
  "total_conversations": int,
  "ai_resolved": int,
  "transferred_to_team": int,
  "avg_ai_response_seconds": float | None,
  "avg_team_takeover_seconds": float | None,
  "by_unit": { "Nome Unidade": { "total": int, "avg_ai_response_seconds": float } },
  "by_attendant": { "user_id": { "total": int, "avg_response_seconds": float } }
}
```

- [ ] **Step 4: Rodar testes**

```bash
pytest tests/test_analyzer.py -v
```
Esperado: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add agente-botconversa/src/analyzer.py agente-botconversa/tests/test_analyzer.py
git commit -m "feat: metrics analyzer by unit and attendant"
```

---

### Task 5: Detector de Alertas

**Files:**
- Create: `agente-botconversa/src/alert_detector.py`
- Create: `agente-botconversa/tests/test_alert_detector.py`

**Interfaces:**
- Consome: lista de conversas anonimizadas, `config` com `tempo_alerta_ia_minutos` e `tempo_alerta_equipe_minutos`
- Produz: `detect_alerts(conversations: list[dict], config: dict) -> list[dict]` — lista de alertas com `anon_id`, `tipo`, `descricao`, `botconversa_url`

- [ ] **Step 1: Escrever testes**

```python
def test_alert_ai_slow_response():
    convs = [make_conv(anon_id="conv_abc", ai_response_seconds=400)]
    alerts = detect_alerts(convs, config={"tempo_alerta_ia_minutos": 5, ...})
    assert any(a["tipo"] == "ia_lenta" and a["anon_id"] == "conv_abc" for a in alerts)

def test_alert_team_slow_takeover():
    convs = [make_conv(anon_id="conv_xyz", team_takeover_seconds=700)]
    alerts = detect_alerts(convs, config={"tempo_alerta_equipe_minutos": 10, ...})
    assert any(a["tipo"] == "equipe_lenta" for a in alerts)

def test_alert_abandoned():
    convs = [make_conv(anon_id="conv_abn", status="abandoned")]
    alerts = detect_alerts(convs, config=SAMPLE_CONFIG)
    assert any(a["tipo"] == "abandono" for a in alerts)

def test_alert_ai_loop():
    convs = [make_conv(anon_id="conv_loop", repeated_messages=3)]
    alerts = detect_alerts(convs, config=SAMPLE_CONFIG)
    assert any(a["tipo"] == "loop_ia" for a in alerts)

def test_no_alert_for_normal_conversation():
    convs = [make_conv(ai_response_seconds=60, status="resolved")]
    alerts = detect_alerts(convs, config=SAMPLE_CONFIG)
    assert alerts == []
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
pytest tests/test_alert_detector.py -v
```

- [ ] **Step 3: Implementar `src/alert_detector.py`**

Tipos de alerta: `ia_lenta`, `equipe_lenta`, `abandono`, `loop_ia`, `transferencia_multipla`. Campo `botconversa_url` deve ser `None` por enquanto (preenchido com URL real quando a API confirmar o formato).

- [ ] **Step 4: Rodar testes**

```bash
pytest tests/test_alert_detector.py -v
```
Esperado: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add agente-botconversa/src/alert_detector.py agente-botconversa/tests/test_alert_detector.py
git commit -m "feat: alert detector for slow responses, abandonment and AI loops"
```

---

### Task 6: Gerador do Dashboard HTML

**Files:**
- Create: `agente-botconversa/src/dashboard_generator.py`
- Create: `agente-botconversa/templates/dashboard.html`
- Create: `agente-botconversa/tests/test_dashboard_generator.py`

**Interfaces:**
- Consome: `analyze()` de Task 4, `detect_alerts()` de Task 5, histórico de `dados/`
- Produz: `generate_dashboard(metrics: dict, alerts: list, history: list, client_name: str, date: str, output_path: str) -> str` — escreve HTML e retorna o caminho do arquivo

- [ ] **Step 1: Escrever testes**

```python
def test_dashboard_created(tmp_path):
    path = generate_dashboard(
        metrics=SAMPLE_METRICS, alerts=[], history=[],
        client_name="Teste", date="2026-10-22",
        output_path=str(tmp_path)
    )
    assert Path(path).exists()
    assert path.endswith(".html")

def test_dashboard_shows_total_conversations(tmp_path):
    metrics = {**SAMPLE_METRICS, "total_conversations": 47}
    path = generate_dashboard(metrics=metrics, alerts=[], history=[], ...)
    content = Path(path).read_text()
    assert "47" in content

def test_dashboard_shows_alert_count(tmp_path):
    alerts = [{"tipo": "ia_lenta", "anon_id": "conv_abc", "descricao": "..."}]
    path = generate_dashboard(metrics=SAMPLE_METRICS, alerts=alerts, ...)
    content = Path(path).read_text()
    assert "conv_abc" in content

def test_dashboard_no_history_shows_message(tmp_path):
    path = generate_dashboard(metrics=SAMPLE_METRICS, alerts=[], history=[], ...)
    content = Path(path).read_text()
    assert "dados insuficientes" in content.lower()
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
pytest tests/test_dashboard_generator.py -v
```

- [ ] **Step 3: Criar template `templates/dashboard.html`**

Template Jinja2 com seções: cabeçalho (nome cliente + data + 3 KPIs), visão geral, tabela por unidade, tabela por atendente, lista de alertas (com link se `botconversa_url` não for None), gráfico de tendência (Chart.js via CDN). Botão "Exportar PDF" que abre `pdf_exporter.html` com checkboxes de filtro.

- [ ] **Step 4: Implementar `src/dashboard_generator.py`**

Usar `jinja2.Environment` com `FileSystemLoader` apontando para `templates/`. Carregar histórico dos últimos 90 dias de arquivos JSON em `dados/{client}/`. Gravar HTML em `relatorios/{client}/YYYY-MM-DD.html`.

- [ ] **Step 5: Rodar testes**

```bash
pytest tests/test_dashboard_generator.py -v
```
Esperado: 4 PASS

- [ ] **Step 6: Commit**

```bash
git add agente-botconversa/src/dashboard_generator.py agente-botconversa/templates/dashboard.html agente-botconversa/tests/test_dashboard_generator.py
git commit -m "feat: HTML dashboard generator with history and alerts"
```

---

### Task 7: Exportador PDF

**Files:**
- Create: `agente-botconversa/src/pdf_exporter.py`
- Create: `agente-botconversa/templates/report_pdf.html`

**Interfaces:**
- Consome: métricas + alertas, filtros selecionados pelo usuário
- Produz: `export_pdf(metrics: dict, alerts: list, filters: dict, client_name: str, date: str, output_path: str) -> str` — grava PDF e retorna caminho

Filtros possíveis: `include_units: bool`, `include_attendants: bool`, `include_alerts: bool`, `date_range: int` (dias).

- [ ] **Step 1: Instalar weasyprint**

```bash
pip install weasyprint
```

- [ ] **Step 2: Criar template `templates/report_pdf.html`**

Jinja2 com layout de relatório: logo placeholder, nome do cliente, período, métricas selecionadas pelos filtros. CSS para impressão (sem botões, sem navegação).

- [ ] **Step 3: Implementar `src/pdf_exporter.py`**

Usar `weasyprint.HTML(string=html_content).write_pdf(output_path)`. Aplicar filtros antes de renderizar o template: omitir seções de atendentes se `include_attendants=False`, etc.

- [ ] **Step 4: Teste manual**

Rodar `python -c "from src.pdf_exporter import export_pdf; export_pdf(...)"` com dados de exemplo e verificar que o PDF abre corretamente.

- [ ] **Step 5: Commit**

```bash
git add agente-botconversa/src/pdf_exporter.py agente-botconversa/templates/report_pdf.html
git commit -m "feat: PDF exporter with section filters"
```

---

### Task 8: Orquestrador Principal e Agendador Windows

**Files:**
- Create: `agente-botconversa/run.py`
- Create: `agente-botconversa/setup_windows.py`

**Interfaces:**
- Consome: todos os módulos anteriores
- Produz: execução completa para todos os clientes + abertura do navegador

- [ ] **Step 1: Implementar `run.py`**

```python
# Fluxo por cliente:
# 1. load_config(client_folder)
# 2. collect_conversations(api_key, yesterday)
# 3. salvar JSON em dados/{client}/YYYY-MM-DD.json
# 4. analyze(conversations, config)
# 5. detect_alerts(conversations, config)
# 6. generate_dashboard(metrics, alerts, history, ...)
# 7. abrir dashboard no navegador: webbrowser.open(dashboard_path)
# Em caso de erro: logar em logs/erros.log, continuar para próximo cliente
```

- [ ] **Step 2: Implementar `setup_windows.py`**

Script a rodar uma única vez. Instala dependências (`pip install -r requirements.txt`), cria pastas necessárias, registra tarefa no Windows Task Scheduler via `schtasks /create` para rodar `run.py` todo dia às 06:00.

- [ ] **Step 3: Criar `requirements.txt`**

```
requests>=2.31.0
jinja2>=3.1.0
weasyprint>=60.0
pytest>=7.4.0
pytest-mock>=3.11.0
requests-mock>=1.11.0
```

- [ ] **Step 4: Teste de integração — rodar com cliente de exemplo**

```bash
python run.py
```
Verificar: arquivo JSON criado em `dados/`, HTML criado em `relatorios/`, navegador abre.

- [ ] **Step 5: Commit final**

```bash
git add agente-botconversa/run.py agente-botconversa/setup_windows.py agente-botconversa/requirements.txt
git commit -m "feat: main orchestrator and Windows Task Scheduler setup"
```

---

## Notas de Implementação

**Endpoint da API Botconversa:** O plano usa `https://api.botconversa.com.br/v1/` como base. Verificar na documentação oficial do Botconversa o endpoint exato para listar conversas por data e o formato dos campos antes de implementar a Task 3.

**weasyprint no Windows:** Requer GTK instalado. O `setup_windows.py` deve incluir instrução para baixar o instalador GTK ou usar alternativa como `pdfkit` + `wkhtmltopdf` se GTK for problemático.

**Primeiro cliente configurado:** Usar o cliente grande (6-10 unidades) como piloto na Task 8, validando todas as métricas antes de replicar para os demais clientes.
