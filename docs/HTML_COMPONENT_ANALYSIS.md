# Análise Estrutural dos Componentes HTML do Overlay

> Branch: `revamp` | Data: 2026-05-13  
> Modelo de referência: Hassaku XL (Illustrious) v3.4 (ID 6526, Version 2615702)

---

## 1. Tabela de Mapeamento — Builders Atuais

| # | Função Builder | Bloco Visual Gerado | Origem dos Dados | Tipo do Bloco | Posição Atual | Posição Recomendada (Revamp) | Observações de Risco |
|---|---------------|---------------------|------------------|---------------|---------------|------------------------------|----------------------|
| 1 | `build_model_page_html` | **Model Page** — nome do modelo + link externo para CivitAI | API Civitai (`item['name']`, `model_main_url`) | **Identidade** | Topo esquerdo, dentro de `.header-block` | **Card de Identidade** — topo, em destaque com nome grande e link | Baixo risco. Apenas link; se `is_local_only` vira texto estático. |
| 2 | `build_uploader_html` | **Uploader** — avatar + nome do criador + link para perfil | API Civitai (`creator['username']`, `creator['image']`) | **Identidade** | Topo esquerdo, abaixo do model page, dentro de `.header-block` | **Card de Identidade** — junto com model page, ou card separado de Criador | Baixo risco. Fallback para "User not found" já existe. Avatar placeholder externo (CDN). |
| 3a | `build_version_info_html` (badges) | **Badges Principais** — type, base model, NSFW, downloads, likes | API Civitai (`content_type`, `baseModel`, `nsfwLevel`, `stats.downloadCount`, `stats.thumbsUpCount`) | **Identidade** | Parte de `.version-info-block` esquerdo | **Header badges row** — abaixo do título do modelo | Baixo risco. Dados sempre presentes. Badges podem ser condicionais (NSFW só se `nsfwLevel > 0`). |
| 3b | `build_version_info_html` (details) | **Detalhes Técnicos** — version, published date, SHA256, download link, availability | API Civitai (`version`, `publishedAt`, `sha256`, `downloadUrl`, `availability`) | **Metadata** | Parte de `.version-info-block` esquerdo | **Card de Metadata Técnica** — sidebar, abaixo de Trigger Words | Médio risco. SHA256 pode ser "Unknown". Download link pode ser vazio. |
| 4 | `build_version_permissions_html` | **Permissions** — lista de 7 permissões com ícones SVG allow/deny | API Civitai (`allowNoCredit`, `allowCommercialUse[]`, `allowDerivatives`, `allowDifferentLicense`) | **Permissão** | Meio esquerdo, dentro de `.info-permissions-container`, abaixo de version_info | **Card de Permissões** — sidebar, colapsável, abaixo de Metadata Técnica | Baixo risco. Dados sempre presentes na API. Ícones SVG inline. |
| 5 | `build_description_html` | **Model Description** — HTML rico da descrição + toggle "Show More" + overlay | API Civitai (`item['description']` + `selected_version['description']` merge) | **Conteúdo Autoral** | Inferior esquerdo, abaixo de trained_words | **Painel Principal** — área de leitura central/esquerda, expansível | Médio risco. Descrição vem como HTML livre da API (pode conter `<img>`, `<code>`). Merge com "About this version" já sanitizado. `REVIEW_BLOCK_ANCHOR` injetado por `_inject_review_block_into_model_html` **depois** do builder. |
| 6 | `build_trigger_words_html` | **Trigger Words** — botões copy/add para cada grupo + botão "Add all" + row sintética `<lora:name:1>` para LORAs | **Misto**: Browser Neo local (`get_local_trigger_words` preferido) → fallback API (`trainedWords`) | **Ação Local / Uso no Forge** | Entre permissions e description, condicional (`if sanitized_groups or is_LORA`) | **Card de Ações Rápidas** — sidebar, **primeiro card abaixo de Download**, porque para LoRA é ação direta de uso no Forge | Médio risco. Local vs API fallback complexo. LORA tag sintética usa `os.path.splitext(model_filename)` — depende de arquivo local existir. Se `model_filename` for None, LORA row não aparece. |
| 8 | `build_image_gallery` *(ainza em `civitai_api.py`)* | **Image Gallery** — grid de imagens/vídeos com: preview media, "Send to txt2img", metadata expandível (prompt, negative, sampler, etc.), empty-state para vídeo/sem-metadata | API Civitai (`api_version['images']` → `url`, `width`, `type`, `meta`) | **Conteúdo Autoral + Uso no Forge** | Coluna direita inteira (`.images-section`) | **Galeria Principal** — mantida à direita ou em aba dedicada; prompt metadata preservada | **Alto risco.** Bloco mais complexo (~140 linhas). Lógica condicional densa: video vs imagem, meta_button, prompt_dict vazio, accordion "More details", empty-state SVG. Depende de `meta_btn` e `playback` opts. |
| 7 | `_file.get_companion_banner` | **Companion Banner** — aviso de arquivos companion (VAE/text_encoder) ausentes | Browser Neo (`output_basemodel`, `model_filename`, `model_name`) | **Ação Local** | Entre info-permissions-container e trained_words | **Banner contextual** — sidebar, próximo ao card de Download | Médio risco. Lógica de detecção de companion files reside em `civitai_file_manage.py`. Não faz parte do escopo do builder puro. |

---

## 2. Dados da API NÃO Renderizados Hoje

Campos disponíveis na API mas descartados pelo HTML atual:

| Campo API | Onde está | Valor de Exemplo (Hassaku XL) | Potencial de Uso no Revamp |
|-----------|-----------|------------------------------|---------------------------|
| `stats.downloadCount` | `model.stats` | 106.940 | Card de Popularidade |
| `stats.thumbsUpCount` | `model.stats` | 9.237 | Card de Popularidade |
| `stats.thumbsDownCount` | `model.stats` | 2 | Card de Popularidade |
| `stats.commentCount` | `model.stats` | 27 | *(Ignorar — Discussion é desnecessário)* |
| `stats.tippedAmountCount` | `model.stats` | 30 | Card de Popularidade (opcional) |
| `nsfw` / `nsfwLevel` | `model` / `version` | `true` / `7` | Badge/tag visual |
| `poi` | `model` | `false` | Badge de "Person of Interest" (raramente usado) |
| `minor` | `model` | `false` | Badge de conteúdo minor (alerta) |
| `sfwOnly` | `model` | `false` | — |
| `supportsGeneration` | `model` | `false` | Badge "Geração On-site disponível" |
| `userId` | `model` | `12345` | — |
| `cosmetic` | `model` | `null` | — |
| `version.stats.downloadCount` | `version.stats` | — | Card de Popularidade por versão |
| `version.stats.ratingCount` | `version.stats` | — | — |
| `version.stats.rating` | `version.stats` | — | — |

> **Decisão de produto:** Suggested Resources e Discussion são **desnecessários** e não serão renderizados no revamp.

---

## 3. Proposta de Árvore HTML — Layout Revamp

### Princípios
1. **Separação de concerns**: conteúdo Civitai (esquerda/central) vs. camada local Browser Neo (direita/sidebar)
2. **Cards de metadata/ações**: dados úteis da direita atual viram cards independentes
3. **Local Review é camada local**: não misturar com blocos de conteúdo da API
4. **Manter o que funciona**: galeria de imagens + prompt metadata preservadas

### Árvore Proposta

```html
<div class="main-container revamp-layout">

  <!-- ═══════════════════════════════════════════════ -->
  <!-- COLUNA PRINCIPAL (esquerda/centro) — Conteúdo Civitai -->
  <!-- ═══════════════════════════════════════════════ -->
  <div class="primary-column">

    <!-- Header compacto: identidade do modelo -->
    <header class="model-header">
      <h1 class="model-title">{model_name}</h1>
      <div class="model-meta-badges">
        <span class="badge type">{display_type}</span>
        <span class="badge base-model">{output_basemodel}</span>
        <span class="badge nsfw" data-level="{nsfwLevel}">NSFW</span>  <!-- condicional -->
        <span class="badge popularity">★ {thumbsUpCount}</span>       <!-- novo -->
        <span class="badge downloads">↓ {downloadCount}</span>        <!-- novo -->
      </div>
      <div class="model-source-line">
        {model_page_link} · {uploader_line}
      </div>
    </header>

    <!-- Review Local Banner — camada Browser Neo, não conteúdo Civitai -->
    <div class="local-review-banner">
      <!-- Injetado pelo sistema de review local -->
      <!-- REVIEW_BLOCK_ANCHOR vira aqui ou em sidebar -->
    </div>

    <!-- Tabs de conteúdo principal -->
    <nav class="content-tabs">
      <button class="tab-btn active" data-tab="description">Description</button>
      <button class="tab-btn" data-tab="gallery">Gallery ({image_count})</button>
    </nav>

    <!-- Painel: Descrição -->
    <section class="tab-panel description-panel" id="tab-description">
      <div class="description-content">
        {model_desc}
      </div>
    </section>

    <!-- Painel: Galeria (inicialmente hidden se description for default) -->
    <section class="tab-panel gallery-panel" id="tab-gallery">
      {img_html}
    </section>

  </div>

  <!-- ═══════════════════════════════════════════════ -->
  <!-- SIDEBAR (direita) — Metadata + Ações -->
  <!-- ═══════════════════════════════════════════════ -->
  <aside class="sidebar-column">

    <!-- Card: Download / Install State -->
    <div class="action-card download-card">
      <div class="file-info">
        <span class="filename">{model_filename}</span>
        <span class="file-meta">{format} · {fp} · {filesize}</span>
      </div>
      <!-- Botões Download/Delete/Queue (estado gerado por update_model_info) -->
    </div>

    <!-- Card: Trigger Words / Ações Rápidas -->
    <div class="action-card trigger-card" data-has-content="{bool(trained_words_section)}">
      {trained_words_section}
    </div>

    <!-- Card: Metadata Técnica -->
    <div class="info-card metadata-card">
      <h3>Metadata</h3>
      <dl>
        <dt>Version</dt><dd>{version_name}</dd>
        <dt>Availability</dt><dd>{model_availability}</dd>
        <dt>Published</dt><dd>{model_date_published}</dd>
        <dt>SHA256</dt><dd><code>{sha256_value}</code></dd>
      </dl>
      {tags_html}
    </div>

    <!-- Card: Permissões (colapsável) -->
    <details class="info-card permissions-card">
      <summary>Permissions</summary>
      {perms_html}
    </details>

    <!-- Card: Companion Files (condicional) -->
    <div class="banner-card companion-banner" data-visible="{bool(companion_banner)}">
      {companion_banner}
    </div>

    <!-- Card: Local Model Status (Browser Neo) -->
    <div class="local-model-status-card">
      <h3>Local Model Status</h3>
      <!-- Review status, file location, organize action, etc. -->
    </div>

  </aside>

</div>
```

---

## 4. Mapeamento de Movimentação — Atual → Revamp

| Bloco Atual | Posição Atual | Posição Revamp | Justificativa |
|-------------|---------------|----------------|---------------|
| Model name + link | Header esquerdo | **Header principal** (título grande) | Destaque de identidade |
| Uploader avatar + name | Header esquerdo | **Subheader** abaixo do título | Contexto de autoria |
| Type, Version, Base model, etc. | `.version-info-block` esquerdo | **Card Metadata** sidebar | Dados técnicos não são conteúdo principal |
| Permissions | `.permissions-block` esquerdo | **Card colapsável** sidebar | Informação legal secundária |
| Tags | Inline dentro de version_info | **Card Metadata** sidebar ou badge row | Descoberta por tag |
| SHA256 | Inline em version_info | **Card Metadata** com `<code>` | Dado técnico, cópia fácil |
| Description | `.description-block` esquerdo | **Painel principal** (tab "Description") | Conteúdo autoral = foco |
| Image gallery | `.images-section` direita | **Painel principal** (tab "Gallery") ou sidebar expandida | Galeria é conteúdo, não metadata |
| Trigger words | Entre permissions e description | **Card de Ações** sidebar | Ações rápidas = próximo aos botões |
| Companion banner | Entre info e trained words | **Banner condicional** sidebar | Alerta contextual |
| Local Review | Injetado em description-block | **Card Local Actions** sidebar ou banner acima | Camada local separada da API |

---

## 5. Riscos Agregados por Área

| Área | Risco | Mitigação |
|------|-------|-----------|
| **Galeria** (ainza em `civitai_api.py`) | Alto — 140 linhas de lógica condicional densa | Extrair em Fase 2 antes de mover de coluna |
| **Descrição** | Médio — HTML livre da API com `<img>`, `<code>` | Manter sanitização atual; review anchor já separado |
| **Trigger Words** | Médio — fallback local vs API; LORA tag sintética | Manter lógica de fallback em `update_model_info`; passar resultado pronto |
| **Companion Banner** | Médio — lógica externa em `_file.get_companion_banner` | Manter como componente externo; apenas posicionar |
| **Local Review** | Baixo — já é camada de injeção separada | Mover anchor para novo local no HTML; `_inject_review_block_into_model_html` já suporta múltiplos fallbacks |
| **Estado de Download** | Baixo — `BtnDownInt`, `BtnDel`, etc. | **Não mexer** — permanece em `update_model_info` |
| **Dados novos da API** (stats, badges) | Baixo — campos simples, opcionais | Adicionar como badges/cards condicionais; não quebrar se ausentes |

---

## 6. Recomendações para Próximos Passos

1. **Aprovar layout** → ajustar árvore HTML proposta conforme feedback
2. **Atualizar CSS** (`style_html.css`) — criar classes `.revamp-layout`, `.primary-column`, `.sidebar-column`, `.action-card`, `.info-card`, `.tab-panel`
3. **Fase 2 de extração** — mover `build_image_gallery` para `civitai_html_builder.py`
4. **Implementar novo assembly** — criar `assemble_model_info_html_revamp` (ou parâmetro `layout='revamp'`) em `civitai_html_builder.py`
5. **A/B test** — possibilitar toggle entre layout atual e revamp via setting
