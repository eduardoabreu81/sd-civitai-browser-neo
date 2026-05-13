# Revamp Layout Proposal — CivitAI Browser Neo

> Status: DECISÓRIO  
> Branch: `revamp` | Data: 2026-05-13  
> Base: `docs/HTML_COMPONENT_ANALYSIS.md`  

---

## 1. Resumo Executivo

Este documento define o layout final do overlay de detalhe do modelo no Browser Neo. Não é uma exploração — é a especificação para implementação.

**Decisões tomadas:**
- Layout two-column sem tabs (v1)
- Coluna principal = conteúdo autoral da CivitAI (descrição + galeria)
- Sidebar = metadata, ações e camada local Browser Neo
- Trigger Words é condicional por tipo de modelo
- Local Model Status é camada local, nunca conteúdo CivitAI

---

## 2. Layout Final Recomendado

### 2.1 Estrutura Two-Column

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER: Model Title + Badges + Source/Uploader Line        │
├────────────────────────────────┬────────────────────────────┤
│                                │                            │
│  PRIMARY COLUMN                │  SIDEBAR COLUMN            │
│  ───────────────               │  ────────────────          │
│                                │                            │
│  ┌─────────────────────────┐   │  ┌─────────────────────┐   │
│  │  Model Description      │   │  │  Download Card      │   │
│  │  (rich HTML, scroll)    │   │  │  (state-aware)      │   │
│  └─────────────────────────┘   │  └─────────────────────┘   │
│                                │                            │
│  ┌─────────────────────────┐   │  ┌─────────────────────┐   │
│  │  Image Gallery          │   │  │  Trigger Words      │   │
│  │  (images/videos,        │   │  │  (type-conditional) │   │
│  │   prompt metadata)      │   │  └─────────────────────┘   │
│  └─────────────────────────┘   │                            │
│                                │  ┌─────────────────────┐   │
│                                │  │  Metadata Card      │   │
│                                │  │  (version, date,    │   │
│                                │  │   SHA256, etc.)     │   │
│                                │  └─────────────────────┘   │
│                                │                            │
│                                │  ┌─────────────────────┐   │
│                                │  │  Permissions        │   │
│                                │  │  (collapsible)      │   │
│                                │  └─────────────────────┘   │
│                                │                            │
│                                │  ┌─────────────────────┐   │
│                                │  │  Local Model Status │   │
│                                │  │  (Browser Neo layer)│   │
│                                │  └─────────────────────┘   │
│                                │                            │
│                                │  ┌─────────────────────┐   │
│                                │  │  Companion Banner   │   │
│                                │  │  (alert-only)       │   │
│                                │  └─────────────────────┘   │
│                                │                            │
└────────────────────────────────┴────────────────────────────┘
```

### 2.2 Ordem dos Cards na Sidebar (de cima para baixo)

| # | Card | Visibilidade | Prioridade |
|---|------|-------------|------------|
| 1 | **Download** | Sempre | Crítica — ação principal |
| 2 | **Trigger Words** | Condicional (tipo) | Alta para LoRA/LoCon/DoRA |
| 3 | **Metadata** | Sempre | Média — referência técnica |
| 4 | **Permissions** | Sempre | Baixa — colapsável por padrão |
| 5 | **Local Model Status** | Sempre | Média — camada local |
| 6 | **Companion Banner** | Alert-only | Baixa — só quando há problema |

> **Nota sobre ausência de tabs:** Na v1, não usamos tabs. A descrição fica acima da galeria na coluna principal. Se a galeria for muito grande, o usuário scrolla. Tabs foram consideradas mas rejeitadas para reduzir complexidade de estado e manter o layout previsível.

---

## 3. Comportamento por Tipo de Modelo

### 3.1 Checkpoint Baseline

```
PRIMARY:  Description → Gallery
SIDEBAR:  Download → Metadata → Permissions → Local Model Status
          [Trigger Words omitido]
          [Companion Banner se alerta]
```

**Justificativa:** Checkpoints não têm trigger words. A interface deve ser minimalista. Foco em:
- Leitura da descrição (estilo, caso de uso, recomendações)
- Preview da galeria (resultados possíveis)
- Download/instalação rápida
- Metadata técnica para referência

### 3.2 LoRA / LoCon / DoRA Baseline

```
PRIMARY:  Description → Gallery
SIDEBAR:  Download → Trigger Words → Metadata → Permissions → Local Model Status
          [Companion Banner se alerta]
```

**Justificativa:** Para LoRA, trigger words são **ação direta de uso no Forge**. O usuário precisa copiar a tag `<lora:name:1>` ou as palavras-chave antes de ir para o txt2img. Por isso o card Trigger Words é **segundo na sidebar**, logo abaixo de Download.

**Conteúdo do card Trigger Words para LoRA:**
- Row sintética `<lora:{filename}:1>` com botões copy + add to prompt
- Grupos de trigger words (local ou API) com botões copy + add
- Botão "Add all to prompt" quando há múltiplos grupos

### 3.3 Outros Tipos (Embedding, Upscaler, etc.)

| Tipo | Trigger Words? | Notas |
|------|---------------|-------|
| TextualInversion (Embedding) | Não | Similar a Checkpoint |
| Upscaler | Não | Similar a Checkpoint; pouca galeria |
| VAE | Não | Similar a Checkpoint |
| ControlNet | Não | Similar a Checkpoint |
| Wildcards | Não | Similar a Checkpoint |

---

## 4. Comportamento por Estado (Local vs Remoto)

### 4.1 Modelo Remoto (não instalado)

```
Download Card:
  - Filename: {model_filename}
  - Meta: {format} · {fp} · {filesize}
  - Estado: "Download model" (botão primário)
  - Subfolder selector (se auto-organize ativo)

Local Model Status Card:
  - Estado: "Not installed"
  - Ações: [Mark for review] (avaliação precoce)
```

### 4.2 Modelo Instalado

```
Download Card:
  - Filename: {installed_model_filename}
  - Meta: {format} · {fp} · {filesize}
  - Estado: "Installed" + botão Delete
  - Path: {folder_location}

Local Model Status Card:
  - Estado: "Installed at {relative_path}"
  - SHA256: {sha256_value}
  - Ações: [Mark for review] [Organize] [Open folder]
```

### 4.3 Modelo em Download

```
Download Card:
  - Progress bar (via download manager)
  - Estado: "Downloading..." / "Add to queue"
  - Botões: Cancel

Local Model Status Card:
  - Estado: "Downloading..."
  - Ações: [Mark for review] (desabilitado até completar)
```

### 4.4 Modelo Local-Only (sem registro CivitAI)

```
Download Card:
  - Filename: {model_filename}
  - Estado: "Local file only" (sem link de download)
  - Botão Delete disponível

Local Model Status Card:
  - Estado: "Local file only"
  - Ações: [Mark for review] [Organize]
```

---

## 5. O que Será Omitido do CivitAI Real

Conteúdo disponível no site da CivitAI mas **deliberadamente omitido** do Browser Neo:

| Conteúdo | Motivo da Omissão |
|----------|-------------------|
| **Suggested Resources** | Não agrega valor ao workflow de download/instalação. Adiciona ruído visual. |
| **Discussion / Comments** | Fora do escopo do Browser Neo. Usuário pode abrir o link do modelo no navegador se quiser ler comentários. |
| **Rating individual por versão** | Stats agregados (likes/downloads) já são mostrados como badges. Rating detalhado não é útil para decisão de download. |
| **Outros modelos do mesmo criador** | Não agrega valor no contexto de overlay de um modelo específico. |
| **Collections / Buzz** | Social features do site, não relevantes para gestão local de modelos. |
| **Generated images da comunidade** | A galeria do modelo já mostra previews oficiais. Imagens da comunidade são variáveis demais. |

---

## 6. Riscos e Mitigação

| # | Risco | Impacto | Mitigação |
|---|-------|---------|-----------|
| 1 | **Galeria reposicionada** — hoje ocupa coluna direita inteira; no revamp fica abaixo da descrição | Alto visual | Manter galeria com mesmas funcionalidades (viewer, prompt metadata, send-to-txt2img). Scroll nativo da coluna principal resolve espaço. |
| 2 | **Trigger Words omitido para Checkpoint** — usuários podem esperar ver trigger words em todos os modelos | Baixo | Checkpoints raramente têm trained words na API. Documentar comportamento condicional. |
| 3 | **Descrição longa empurra galeria para baixo** — usuário precisa scrollar muito para ver imagens | Médio | Considerar altura máxima na descrição com toggle "Show More" (já existe). Galeria começa após descrição colapsada. |
| 4 | **Sidebar muito longa para modelos LoRA** — Trigger Words + Metadata + Permissions + Local Status pode exceder viewport | Médio | Scroll independente na sidebar. Permissions colapsável por padrão. Companion Banner só quando necessário. |
| 5 | **CSS breaking change** — novo layout requer classes CSS novas; risco de regressão no layout atual | Alto | Implementar como toggle `revamp_layout` em setting, ou manter v2 como default após período de teste. |
| 6 | **Local Model Status vazio** — quando modelo não está instalado, o card pode parecer vazio demais | Baixo | Mostrar estado "Not installed" + ação "Mark for review" (avaliação precoce). |
| 7 | **Two-column responsivo** — em telas estreitas ( Forge Neo em modo janela ), duas colunas podem ficar apertadas | Médio | CSS deve usar `min-width` na sidebar (ex: 320px) e `flex-wrap` para fallback de uma coluna em viewports < 900px. |

---

## 7. Plano Incremental de Implementação

### Fase A — Estrutura HTML + CSS (sem lógica)
1. Criar `assemble_model_info_html_revamp` em `civitai_html_builder.py`
2. Adicionar classes CSS `.revamp-layout`, `.primary-column`, `.sidebar-column`, `.action-card`, `.info-card`
3. Atualizar `style_html.css` com estilos base (sem cores temáticas ainda)
4. Manter layout atual como fallback (não quebrar usuários)

### Fase B — Posicionamento dos Cards
1. Mover badges (type, base model, NSFW, downloads, likes) para header
2. Mover Metadata para sidebar card
3. Mover Permissions para sidebar card colapsável
4. Mover Trigger Words para sidebar (condicional por tipo)
5. Criar card Local Model Status na sidebar
6. Reposicionar Companion Banner para sidebar alert-only

### Fase C — Galeria na Coluna Principal
1. Extrair `build_image_gallery` para `civitai_html_builder.py` (Fase 2 da extração)
2. Posicionar galeria abaixo da descrição na coluna principal
3. Verificar que prompt metadata, viewer e send-to-txt2img funcionam

### Fase D — Polish e Toggle
1. Adicionar setting `civitai_neo_revamp_layout` (default: false)
2. Condicionar `update_model_info` a usar `assemble_model_info_html` vs `assemble_model_info_html_revamp`
3. Testes manuais em Checkpoint e LoRA
4. Coleta de feedback antes de tornar default

---

## 8. Checklist de Decisões para Aprovação

- [ ] Layout two-column aprovado (sem tabs v1)
- [ ] Ordem dos cards na sidebar aprovada
- [ ] Trigger Words condicional por tipo aprovado
- [ ] Local Model Status como card separado aprovado
- [ ] Lista de omissões do CivitAI real aprovada
- [ ] Plano incremental de implementação aprovado
- [ ] Fase A pronta para iniciar
