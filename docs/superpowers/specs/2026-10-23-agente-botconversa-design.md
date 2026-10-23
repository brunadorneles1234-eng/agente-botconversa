# Agente de Análise Botconversa

**Data:** 2026-10-23  
**Autora:** Bruna Dorneles

---

## Objetivo

Construir um agente local que coleta dados da API do Botconversa diariamente, processa métricas de atendimento respeitando a LGPD, e gera um dashboard HTML por cliente com relatórios de desempenho de IA e equipes humanas.

---

## Contexto

- A usuária gerencia **10+ clientes**, cada um com sua própria conta no Botconversa (API key separada)
- Um cliente possui **6-10 unidades** com múltiplos atendentes (caso piloto)
- Os outros clientes são menores (1 unidade, poucos atendentes)
- Dados incluem conversas com proteção LGPD — nomes e telefones nunca podem ser armazenados
- A usuária tem conhecimento técnico limitado — a solução precisa ser simples de configurar

---

## Arquitetura

```
Botconversa API (por cliente)
        ↓
  Agente Python (local, Windows)
        ↓
  Anonimização imediata dos dados
        ↓
  Cálculo de métricas
        ↓
  Arquivo JSON local (métricas, sem dados pessoais)
        ↓
  Dashboard HTML gerado
        ↓
  Navegador abre automaticamente às 6h
```

Tudo roda **localmente**. Nenhum dado sai da máquina. Sem custo de nuvem.

---

## Estrutura de Pastas

```
agente-botconversa/
├── run.py                  ← script principal (roda todo dia)
├── config/
│   ├── cliente_grande/
│   │   └── config.json     ← API key + configurações do cliente
│   └── cliente_02/
│       └── config.json
├── dados/
│   └── cliente_grande/
│       └── 2026-10-22.json ← métricas do dia (sem dados pessoais)
├── relatorios/
│   └── cliente_grande/
│       └── 2026-10-22.html ← dashboard do dia
└── logs/
    └── erros.log           ← log de falhas do agente
```

Adicionar um novo cliente = criar pasta em `config/` + preencher `config.json`. Tempo estimado: **10 minutos**.

---

## Arquivo de Configuração (`config.json`)

```json
{
  "nome_cliente": "Cliente Grande",
  "botconversa_api_key": "SUA_CHAVE_AQUI",
  "horario_coleta": "06:00",
  "tempo_alerta_minutos": 5,
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

---

## Proteção LGPD

| Dado | Tratamento |
|------|-----------|
| Nome do cliente | **Nunca armazenado** — descartado na coleta |
| Telefone | **Nunca armazenado** — descartado na coleta |
| Conteúdo das mensagens | **Nunca armazenado** — só métricas calculadas |
| ID de conversa | Armazenado como código interno anonimizado |
| Atendente | Armazenado por ID interno (mapeado no config) |

Conversas problemáticas no dashboard mostram apenas:
- Código interno da conversa
- Motivo do alerta (ex: "tempo de resposta > 5 min")
- Tempos calculados
- Link para abrir a conversa **no Botconversa** (não copia conteúdo)

---

## Métricas Calculadas

### Por dia (visão geral)
- Total de conversas iniciadas
- Total atendidas pela IA vs. transferidas para equipe
- Tempo médio de resposta da IA
- Tempo médio até equipe assumir (após transferência)
- Total de conversas sem resolução
- Total de alertas disparados

### Por unidade
- Volume de conversas
- Tempo médio de atendimento
- Taxa de resolução pela IA
- Atendentes ativos e suas métricas individuais

### Por atendente
- Conversas atendidas
- Tempo médio de resposta
- Tempo médio de resolução

### Comparativo entre unidades
- Ranking de unidades por volume
- Ranking de unidades por tempo de resposta
- Unidade com mais erros da IA

---

## Detector de Alertas

O agente marca uma conversa como problemática quando:

| Alerta | Condição |
|--------|---------|
| IA sem resposta | Mais de 5 min sem resposta da IA (configurável) |
| Espera longa na equipe | Mais de 10 min para equipe assumir após transferência |
| Abandono | Cliente saiu sem resolução |
| Loop de IA | Mesma mensagem repetida 3+ vezes |
| Transferência múltipla | Conversa transferida para equipe mais de 1 vez |

---

## Dashboard HTML

Uma página por cliente por dia. Seções:

1. **Cabeçalho** — nome do cliente, data, resumo em 3 números (conversas / alertas / tempo médio)
2. **Visão Geral** — gráficos de volume e tempo
3. **Por Unidade** — tabela comparativa + filtro
4. **Por Atendente** — tabela com métricas individuais
5. **Alertas do Dia** — lista de conversas problemáticas com link para Botconversa
6. **Tendência** — comparativo com os últimos 7, 30 e 90 dias
7. **Exportar PDF** — filtro para escolher o que incluir (unidades, atendentes, alertas) antes de gerar o arquivo para enviar ao cliente

---

## Execução Automática (Windows Task Scheduler)

- Horário: **06:00 todos os dias**
- Comando: `python C:\agente-botconversa\run.py`
- Ao finalizar: abre o dashboard no navegador automaticamente
- Em caso de falha: registra em `logs/erros.log` e envia notificação toast no Windows

---

## Plano de Implementação

1. **Fase 1 — Piloto** (cliente grande, 1 semana)
   - Instalar dependências Python
   - Configurar 1 cliente
   - Validar coleta da API e métricas
   - Validar dashboard

2. **Fase 2 — Expansão** (clientes adicionais, conforme disponibilidade)
   - Adicionar 1 cliente por vez (10 min cada)
   - Sem mudança no código

---

## Custos

- **Nuvem:** Zero (tudo local)
- **API Botconversa:** Verificar limite do plano (1 coleta/dia = baixo consumo)
- **Armazenamento:** ~50MB/mês para todos os clientes (apenas métricas JSON)
- **Histórico:** acumulado indefinidamente em `dados/` — permite comparativos de qualquer período
- **PDF para cliente:** gerado sob demanda com filtro (unidades, atendentes, alertas — você decide o que entra)
- **Python:** Gratuito

---

## Dependências

- Python 3.10+ (gratuito)
- Bibliotecas: `requests`, `jinja2` (para HTML), `schedule`
- Nenhum banco de dados necessário
