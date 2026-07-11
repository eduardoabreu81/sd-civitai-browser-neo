# PROJECT_LOG

## Escopo Atual (v0.9.0)

- **Extension para Forge Neo** — Browse, download e organize modelos do CivitAI diretamente no WebUI com suporte a Gradio 4+
- **Auto-organização inteligente** — Modelos organizados por base model (SDXL/, Pony/, FLUX/, Wan/, etc.) com backup/rollback automático e suporte a subpastas por subtipo Wan (I2V/T2V/TI2V)
- **Download robusto com Aria2** — Queue persistente, hash validation, auto-reconnect e multi-connection
- **Dashboard e estatísticas** — Análise de disco por categoria/arquitetura, top files, orphan detection, export CSV/JSON
- **Curadoria de criadores** — Sistema de favoritos ⭐ e ban 🚫 com persistência em disco

---

## Estado Rápido

**Stack:** Python 3.x + Gradio 4.40.0 + Forge Neo + Aria2 + JavaScript vanilla  
**Features ativas:** Browse/Search, Download Queue, Auto-Organization, Update Detection, Dashboard, Creator Management, Local Models browser  
**Status (main):** v0.9.0 — Estável (CivitAI Domain Support, Update Mode Isolation, Download Resilience)  
**Status (branch `revamp`):** Beta-Revamp v0.1.0 — em desenvolvimento, não released. Aba Local Models self-contained (Update Models fundida), isolamento Browser↔Local, resiliência de fetch. Ver "Linha do Tempo — Branch `revamp`"  
**Twin project:** sd-civitai-browser-ex (Gradio 3, A1111/Forge Classic) — mudanças específicas do Neo não devem migrar automaticamente

---

## Linha do Tempo

### 2026-07-10 — Fix: Local Models outdated-card checkbox selection

**O que mudou (pt-BR):** Corrigido bug na aba Local Models em que os checkboxes dos cards **outdated** (laranja) não respondiam ao clique quando o usuário filtrava "Only models with updates". O problema era que o JavaScript detectava o checkbox como se fosse do Browser, atualizava os textboxes errados (`#selected_model_list`) e disparava um erro do Gradio (`Attempted to select a non-interactive or hidden tab`). A seleção em lote para **"Update selected"** agora funciona corretamente.
**Causa:** A detecção `_isLocalCheckbox(el)` usava apenas `el.closest('#local_list_html')`; no Gradio 4 o conteúdo HTML do Local Models é embrulhado de forma que essa ancestralidade falha.
**Solução:** Os checkboxes renderizados para `target='local'` agora carregam o marcador `data-local="true"`, e `_isLocalCheckbox()` verifica esse marcador antes de recorrer ao `closest()`.
**Arquivos alterados:** `scripts/civitai_api.py`, `javascript/civitai-html.js`.
**Validação:** `py_compile` limpo; suite `tests/` passou com **142 passed**; validação runtime no Forge Neo confirmou que checkboxes de outdated cards agora marcam e o botão "Update selected" enfileira o update.
**Próximos passos / Next steps:**
- Monitorar se a mesma detecção precisa ser aplicada a outros elementos do Local Models que usam `closest('#local_list_html')`.

### 2026-07-11 — Investigação: Update selected não enfileirou modelo da segunda página (não reproduzível)

**O que foi reportado:** Após aplicar o fix do checkbox, o usuário conseguiu atualizar 2 modelos outdated via "Update selected", mas um terceiro modelo localizado na **segunda página** da paginação do Local Models não foi baixado. No terminal apareceu apenas `[CivitAI Browser Neo] - [local refresh] download_finish → model_string=''` e nenhuma ação foi tomada. O bug **não foi reproduzível** em tentativas seguintes.
**Hipóteses levantadas:**
1. Checkbox da página 2 detectado como Browser em vez de Local (rotação errada), fazendo o item ir para `selectedModels` em vez de `selectedModelsLocal`.
2. Seleção Local perdida durante a re-renderização da paginação.
3. Race condition no Gradio 4: `update_selected_trigger` disparou antes do JS atualizar o valor.
4. Cache de JS antigo sem o fix `data-local` (a extensão foi recém-instalada/atualizada via GitHub).
**Ação tomada:** Adicionados **logs defensivos** para capturar a causa sem depender de reprodução manual:
- `javascript/civitai-html.js`: `multi_model_select` agora loga `isLocal`, nome do modelo, estado do checkbox e contadores das listas; também loga um warning se `data-local=true` não for detectado como local.
- `javascript/civitai-html.js`: `updateSelectedLocalModels` loga o array completo antes de disparar o trigger.
- `scripts/civitai_download.py`: `update_selected_models` loga o valor bruto recebido, remove entradas vazias com warning e loga a lista final enfileirada.
**Arquivos alterados:** `javascript/civitai-html.js`, `scripts/civitai_download.py`.
**Validação:** `py_compile` limpo; suite `tests/` passou com **142 passed**.
**Próximos passos / Next steps:**
- Monitorar logs no console do navegador e no terminal do Forge Neo nas próximas atualizações em lote que envolvam múltiplas páginas.
- Se o bug voltar e os logs indicarem rotação errada, reforçar a detecção local (ex.: usar atributo no card em vez de confiar em `closest`).
- Se os logs indicarem race condition no trigger, adicionar delay/sequenciamento entre o JS e o evento Python.

---

### 2026-07-10 — Browser "Paste model URL" search mode + Hugging Face removed from dropdown

**O que mudou (pt-BR):** Adicionado um novo modo de busca **URL** na aba Browser. O usuário pode colar uma URL direta de CivitAI, CivArchive, Hugging Face ou Arc en Ciel; o extension detecta o provider, busca o modelo, renderiza um único card e popula o model panel para download. Como consequência, o **Hugging Face foi removido do dropdown de Browser Source**; o adapter continua registrado, mas só é acessível via URL direta.
**Motivação:** A busca direta no Hugging Face retorna muito ruído (componentes Diffusers, repos sem arquivo baixável, falta de suporte a GGUF). Colar a URL é mais prático e alinhado com o produto até termos uma curadoria melhor.
**Arquitetura:** Criado `scripts/browser_sources/url_parser.py` com parser/dispatcher de URLs; adicionado atributo `visible_in_dropdown` em `BrowserSource` para controlar quais adapters aparecem no dropdown; ramo `use_search_term == 'URL'` em `initial_model_page` reaproveita todo o fluxo existente de cards/detail/download.
**Arquivos alterados:** `scripts/browser_sources/base.py`, `scripts/browser_sources/registry.py`, `scripts/browser_sources/huggingface.py`, `scripts/browser_sources/url_parser.py` (novo), `scripts/browser_sources/__init__.py`, `scripts/civitai_api.py`, `scripts/civitai_gui.py`, `tests/test_browser_sources.py`, `docs/PROJECT_LOG.md`.
**Validação:** `py_compile` dos módulos alterados limpo; testes `tests/test_browser_sources.py` passaram com **49 passed**; suite completa `tests/` passou com **142 passed**. Validação runtime no Forge Neo **concluída** — URL do Hugging Face, CivitAI, CivArchive e Arc en Ciel renderizaram cards, populararam o model panel e permitiram enfileirar download; URL inválida retornou mensagem de erro no grid.
**Próximos passos / Next steps:**
- Monitorar uso real do modo URL e coletar feedback sobre quais providers/padrões de URL ainda faltam.
- Quando o catálogo curado Hugging Face estiver pronto, reavaliar se HF volta ao dropdown.

---

### 2026-07-09 — Arc en Ciel local content/base filters

**O que mudou (pt-BR):** Corrigido o adapter **Arc en Ciel** para respeitar os filtros do Browser por `content_type` e `base_filter`. A API pública aceita parâmetros desconhecidos sem erro, mas testes live mostraram que `type=CHECKPOINT`, `type=LORA`, `modelClassId`, `modelClassIds` e `baseModel` não filtram de forma confiável; por isso o adapter agora busca uma janela maior e filtra localmente.
**Comportamento:** Se o usuário selecionar `Checkpoint`, LoRAs deixam de aparecer. Se selecionar uma base como `Anima`, o adapter mantém apenas modelos/versões compatíveis com essa base e remove versões de outras bases do dropdown. Sem filtro de base ativo, o browse volta a mostrar o default geral da plataforma.
**Arquivos alterados:** `scripts/browser_sources/arcenciel.py`, `tests/test_browser_sources.py`, `docs/PROJECT_LOG.md`.
**Validação:** Teste focado `tests/test_browser_sources.py` passou com **40 passed**; `py_compile scripts/browser_sources/arcenciel.py` e `git diff --check` ficaram limpos. Probes live em 2026-07-09 confirmaram que a API Arc en Ciel ignora os filtros nativos de tipo/base testados. Validação runtime no Forge Neo em 2026-07-10 **concluída** — busca vazia, filtro por content type/base model e paginação funcionaram conforme esperado.
**Próximos passos / Next steps:**
- Monitorar se a API Arc en Ciel publica filtros oficiais de tipo/base para trocar o filtro local por parâmetros nativos.
- Observar comportamento de download e sidecars em uso real com modelos Arc en Ciel.

---

### 2026-07-09 — External file size metadata fallback

**O que mudou (pt-BR):** Corrigido novo crash ao clicar em card do Hugging Face quando o arquivo externo vinha com `sizeKB=None`. O detail panel legado multiplicava `None * 1024`; agora o cálculo de tamanho aceita `None`, string numérica e valores inválidos com fallback seguro para `0`.
**Integração:** Criados helpers internos `_file_size_kb()` e `_file_size_bytes()` em `civitai_api.py`; `update_model_info()` e `update_file_info()` passaram a usar esses helpers nos pontos que exibem o file dropdown e calculam tamanho para detecção de Textual Inversion/PickleTensor.
**Arquivos alterados:** `scripts/civitai_api.py`, `tests/test_civitai_model_ids.py`, `docs/PROJECT_LOG.md`.
**Validação:** Testes focados `tests/test_civitai_model_ids.py tests/test_browser_sources.py` passaram com **43 passed**; `py_compile scripts/civitai_api.py` e `git diff --check` ficaram limpos.
**Próximos passos / Next steps:**
- Atualizar a extensão remota e repetir: Hugging Face → browse/base Anima → clicar em card.
- Se o detail panel abrir, validar file dropdown e iniciar um download pequeno/seguro.
- Observar se algum outro campo externo opcional (`metadata`, `hashes`, `images`) ainda assume o shape CivitAI completo.

---

### 2026-07-09 — External browser source string model IDs

**O que mudou (pt-BR):** Corrigido o crash ao clicar em cards do Hugging Face, causado por `extract_model_info()` converter sempre o ID do dropdown para `int`. Fontes externas como Hugging Face usam IDs string no formato `owner/repo`, então o parser agora mantém IDs CivitAI numéricos como `int` e preserva IDs externos como `str`.
**Integração:** Adicionado helper `model_id_matches()` para comparar IDs sem assumir formato numérico. O Browser detail panel, version dropdown, file list, download queue, early-access check, save-images e delete flow passaram a usar comparação segura nos pontos que podem receber dados de fontes externas.
**Arquivos alterados:** `scripts/civitai_api.py`, `scripts/civitai_download.py`, `scripts/civitai_file_manage.py`, `scripts/civitai_gui.py`, `tests/test_civitai_model_ids.py`, `docs/PROJECT_LOG.md`.
**Validação:** Testes focados `tests/test_browser_sources.py tests/test_civitai_model_ids.py` passaram com **42 passed**; `py_compile` dos módulos alterados e `git diff --check` ficaram limpos.
**Próximos passos / Next steps:**
- Atualizar a extensão remota e repetir: Hugging Face → browse/base Anima → clicar em card.
- Se o detail panel abrir, validar version dropdown, file dropdown e download de um item pequeno/seguro.
- Confirmar se o pós-download externo salva sidecars e preview sem novos casts numéricos.

---

### 2026-07-09 — Arc en Ciel empty browse mode

**O que mudou (pt-BR):** Corrigido o adapter **Arc en Ciel** para tratar busca vazia como modo browse. Antes, `query=''` retornava imediatamente uma lista vazia; agora o adapter chama `https://arcenciel.io/api/models/search?limit=...` sem `q`, preserva paginação e usa `totalCount`/`totalPages` quando a API retorna esses campos.
**Compatibilidade:** O payload real da API mostrou `activationTags` como string em alguns modelos; o adapter agora normaliza strings separadas por vírgula, ponto-e-vírgula ou quebra de linha para evitar trigger words quebradas caractere por caractere.
**Arquivos alterados:** `scripts/browser_sources/arcenciel.py`, `tests/test_browser_sources.py`, `docs/PROJECT_LOG.md`.
**Validação:** Chamada real em 2026-07-09 para `https://arcenciel.io/api/models/search?limit=3` retornou `data`, `totalCount` e `totalPages`. Teste focado `tests/test_browser_sources.py` passou com **38 passed** e `git diff --check` ficou limpo.
**Próximos passos / Next steps:**
- Atualizar a extensão remota e validar Arc en Ciel no Forge Neo: busca vazia, clique em card, Next/Prev e download.
- Se o detail panel abrir corretamente, validar sidecars e preview pós-download.
- Depois disso, decidir se Arc en Ciel sai de “adapter foundation” para “runtime validated” na documentação pública.

---

### 2026-07-08 — Documentação pública do Multi-Source Browser

**O que mudou (pt-BR):** O `README.md` passou a documentar o estado atual da fundação Multi-Source Browser na branch `revamp`: selector de fonte, adapters CivitAI/CivArchive/Hugging Face/Arc en Ciel, proveniência de fontes externas, normalização defensiva de metadata e filtros de compatibilidade do Hugging Face.
**Escopo público:** A documentação foi escrita como **revamp preview**, não como release estável da `main`. CivitAI continua descrita como fonte primária de verdade para metadata, previews, permissões e validação por SHA256.
**Decisões:** `Deleted from CivitAI` permanece documentado como filtro exclusivo do CivArchive e semanticamente separado do futuro `Not found on CivitAI`. GGUF foi documentado como suportado pelo Forge Neo, mas ainda bloqueado no Browser Neo até download, organização, revisão local, sidecars e metadata reconhecerem `.gguf` de forma segura.
**Arquivos alterados:** `README.md`, `docs/PROJECT_LOG.md`, `AGENTS.local.md`.
**Próximos passos / Next steps:**
- Validar runtime no Forge Neo: Hugging Face (`<browse>`, `anima`, `wan`, LoRA), CivArchive `Deleted from CivitAI`, e Arc en Ciel.
- Se a validação runtime fechar, decidir se a documentação de `revamp preview` vira changelog formal de `Revamp v0.1.0`.
- Implementar suporte GGUF somente como fluxo explícito, não como simples liberação de extensão no adapter HF.

---

### 2026-07-08 — Hugging Face live browse e diagnóstico de resultados vazios

**O que mudou (pt-BR):** O adapter **Hugging Face** deixou de retornar lista vazia silenciosa quando a busca vem sem termo. Agora o modo `<browse>` consulta o endpoint público com `sort=downloads`, `direction=-1`, `full=true` e o filtro HF equivalente ao content type quando aplicável (ex.: `Checkpoint` → `stable-diffusion`). A paginação client-side foi ajustada para buscar uma janela maior (`page * page_size`, com cap) antes do slice, evitando página 2 vazia por falta de offset no endpoint HF.
**Diagnóstico:** Adicionados logs `[HuggingFace]` com query efetiva, página, `page_size`, `fetch_limit`, filtro HF, quantidade de repositórios brutos, modelos normalizados, descartes por ausência de arquivo baixável e itens da página. Repositórios sem arquivo de modelo compatível deixam de gerar cards não baixáveis.
**Compatibilidade de arquivos:** A ordenação dos arquivos HF agora prioriza checkpoints/artefatos de modelo reais antes de componentes Diffusers como `text_encoder/`, `safety_checker/`, `scheduler/`, `tokenizer/` e `vae/`. Isso reduz o risco de selecionar um componente auxiliar como arquivo primário em repos com muitos `.safetensors`. O termo exato de busca `anima` também passou a ativar um filtro semântico local por `baseModel=Anima`, evitando resultados textuais genéricos como `AnimateDiff`. O filtro HF para checkpoints comuns mudou de `stable-diffusion` para `text-to-image`; buscas por famílias de vídeo aceitas no Forge Neo (ex.: `Wan`, `HunyuanVideo`, `Stable Video Diffusion`, `LTX`) usam `text-to-video` + `image-to-video`. O Forge Neo já lista/carrega `.gguf` como checkpoint, mas **o adapter HF ainda exclui GGUF nesta etapa** porque o Browser Neo precisa de suporte explícito em download, organização, revisão local e metadata antes de tratar `.gguf` como formato baixável seguro. Por enquanto, um repo com `gguf` no nome só aparece se também tiver um `.safetensors` de modelo real, enquanto `.gguf`, VAE/CLIP/T5 auxiliares e arquivos LoRA são descartados da busca `Checkpoint`.
**Arquivos alterados:** `scripts/browser_sources/huggingface.py`, `tests/test_browser_sources.py`.
**Validação:** Teste focado do adapter Hugging Face passou com **37 passed**. Suíte completa concluída com **126 passed + 2 subtests passed**, `py_compile` e `git diff --check`. Verificação live isolada com busca vazia (`Checkpoint`, `page_size=5`) retornou 5 itens e logs detalhados; `query='anima'` retornou checkpoints Anima/Animagine via `text-to-image`; `query='wan'` retornou checkpoints Wan via `text-to-video` + `image-to-video`.
**Próximos passos / Next steps:**
- Atualizar a extensão remota e validar no Forge Neo: Hugging Face → busca vazia, `flux`, `wan`, `lora`, Next/Prev.
- Se algum termo retornar zero, compartilhar os novos logs `[HuggingFace]` para distinguir resposta bruta vazia de descarte por arquivos incompatíveis.
- Depois iniciar a fundação do catálogo curado HF (`catalog/huggingface/curated.json` + scripts dev-only).

---

### 2026-07-08 — Filtro CivArchive para modelos deletados do CivitAI

**O que mudou (pt-BR):** Adicionado o checkbox **Deleted from CivitAI** aos filtros do Browser. Ele fica habilitado somente quando a fonte selecionada é `CivArchive`; ao trocar para qualquer outra fonte, o valor é desmarcado e o componente é desabilitado. O estado pode ser salvo nos defaults quando o CivArchive é a fonte padrão. Busca inicial, refresh, paginação Next/Prev e refresh pós-download compartilham o novo input.
**Integração:** O adapter CivArchive envia `is_deleted=true` para `/api/search`. A API pública foi validada em 2026-07-08: o parâmetro retornou 50/50 resultados com `is_deleted: true`, enquanto a mesma janela sem o parâmetro misturava itens ativos e deletados. O log de busca agora inclui `deleted_only=True|False`.
**Arquivos alterados:** `scripts/civitai_gui.py`, `scripts/civitai_api.py`, `scripts/browser_sources/civarchive.py`, `tests/test_browser_callback_contract.py`, `tests/test_browser_sources.py`.
**Decisões:** Este filtro significa exclusivamente “existia no CivitAI e foi removido”, conforme `is_deleted`/`deleted_at` do CivArchive. Ele não significa “modelo exclusivo de outra plataforma”. O futuro filtro **Not found on CivitAI** dependerá do double-check por SHA256 da Fase F e ficará separado para não misturar estados semanticamente diferentes.
**Roadmap de fontes:** Novas integrações devem priorizar adapters diretos quando a plataforma oferecer API oficial e download estável. Análise futura: TensorArt, SeaArt, PixAI, Shakker, Tungsten, Civision, TensorHub, Yodayo e Moescape. Também avaliar `LykosAI/StabilityMatrix` para identificar padrões reutilizáveis de autenticação, resolução de arquivos, cache e download de CivitAI/Hugging Face.
**Pontos sensíveis:** O CivArchive continua retornando uma janela fixa e o adapter pagina os IDs únicos client-side. Validação automatizada concluída com **117 passed + 2 subtests passed** e `git diff --check`; smoke test runtime ainda necessário no Forge Neo.
**Próximos passos / Next steps:**
- Atualizar a extensão remota e validar: CivArchive → marcar o checkbox → buscar sem termo e com termo → Next/Prev.
- Trocar para CivitAI, Hugging Face e Arc en Ciel e confirmar que o checkbox é desmarcado/desabilitado.
- Prosseguir com a validação das demais fontes antes da Fase E (ModelScope).

---

### 2026-07-08 — Harden preview matching and diagnostics for external downloads

**O que mudou (pt-BR):** `save_preview()` deixou de depender exclusivamente do SHA256 para localizar a versão baixada. O match continua priorizando hash normalizado e agora usa filename exato case-insensitive como fallback, necessário para fontes sem hash ou para diferenças entre o hash resolvido e o payload original. Todos os retornos antes silenciosos ganharam logs `[Preview]`: início, arquivo/target, match por hash ou nome, quantidade de imagens, status HTTP, falha de request/processamento, ausência de item/URL e caminho salvo. O fetch da imagem agora envia headers padrão e usa timeout. Em falha de uma imagem, o fluxo tenta as seguintes antes de desistir.
**Arquivos alterados:** `scripts/civitai_file_manage.py`, `tests/test_preview_matching.py`.
**Decisões:** Filename só é aceito quando o basename é exatamente igual; prefix matching não é usado para evitar associar previews ao modelo errado. `save_preview()` retorna booleano para tornar o resultado observável sem quebrar callers existentes.
**Pontos sensíveis:** Validação concluída com **115 passed + 2 subtests passed**, `py_compile` e `git diff --check`. O modelo Kiwimix já foi baixado e seus sidecars foram salvos; somente o preview precisa ser reprocessado no teste remoto.
**Próximos passos / Next steps:**
- Atualizar a extensão remota e executar a ação de salvar preview/imagens para o Kiwimix.
- Confirmar o log `[Preview] saved successfully` e a criação de `.preview.png`/`.preview.jpg`.
- Se ainda falhar, compartilhar toda a sequência de logs `[Preview]`, que agora identifica o ponto exato.

---

### 2026-07-08 — Fix canonical image shape for external source previews

**O que mudou (pt-BR):** Corrigido o crash `KeyError: 'type'` no pós-processamento de downloads do CivArchive. O helper compartilhado `canonical_image()` agora entrega o shape legado completo esperado pelo Browser: `type`, `nsfwLevel`, `meta`, `url`, `width`, `height` e `hash`. O tipo de mídia é preservado da origem ou inferido pela extensão; prompts são inseridos em `meta` sem apagar outros campos. `save_preview()` também passou a aceitar imagens antigas sem `type`, ignorar entradas sem URL e evitar substituição de largura quando ela não está disponível. A correção se aplica igualmente a Hugging Face e Arc en Ciel.
**Arquivos alterados:** `scripts/browser_sources/normalizer.py`, `scripts/civitai_file_manage.py`, `tests/test_browser_sources.py`.
**Decisões:** Corrigir o contrato na fronteira canônica e manter defesa no consumidor de filesystem; mídia desconhecida assume `image`, enquanto extensões comuns de vídeo são detectadas explicitamente.
**Pontos sensíveis:** O modelo e os sidecars já eram salvos antes do crash; a falha ocorria somente ao salvar preview/galeria. Validação concluída com **112 passed + 2 subtests passed**, `py_compile` e `git diff --check`.
**Próximos passos / Next steps:**
- Atualizar a extensão remota e validar o salvamento de preview sem baixar novamente um modelo grande, se possível usando a ação de salvar imagens.
- Confirmar refresh do card instalado após o pós-processamento.
- Investigar os resultados CivArchive descartados por ausência de arquivos utilizáveis.

---

### 2026-07-08 — Fix canonical file metadata for external source detail panels

**O que mudou (pt-BR):** Corrigido o crash `KeyError: 'metadata'` ao clicar em cards do CivArchive. O helper compartilhado `canonical_file()` agora sempre produz o objeto legado `metadata`, preserva `size`/`fp` fornecidos pela origem e preenche `format`; quando o formato não vem da API, ele é inferido pela extensão (`.safetensors`, `.ckpt`, `.pt`, `.pth`, `.bin`, `.onnx`). Os dois consumidores legados em `civitai_api.py` também passaram a usar acesso defensivo e fallback para o formato top-level. Como Hugging Face e Arc en Ciel usam o mesmo normalizador, a correção cobre as três fontes externas.
**Arquivos alterados:** `scripts/browser_sources/normalizer.py`, `scripts/civitai_api.py`, `tests/test_browser_sources.py`.
**Decisões:** Corrigir o contrato na fronteira canônica e manter defesa adicional nos consumidores legados; fontes externas desconhecidas exibem `Unknown` para size/fp sem interromper o detail panel.
**Pontos sensíveis:** Validação concluída com **111 passed + 2 subtests passed**, `py_compile` e `git diff --check`. Runtime na WebUI ainda necessário para confirmar detail panel, seleção de arquivo e download.
**Próximos passos / Next steps:**
- Atualizar a extensão remota e clicar novamente em um card do CivArchive.
- Validar troca de versão/arquivo e início do download.
- Depois investigar os modelos descartados por ausência de arquivos utilizáveis.

---

### 2026-07-08 — Fix CivArchive refresh routing and result pagination

**O que mudou (pt-BR):** Corrigido o refresh do Browser quando `from_update_tab=True`: tokens internos `browser_source://...` não são mais enviados ao `requests` como URLs HTTP e agora voltam ao adapter selecionado. O CivArchive ganhou logs com contagem de resultados brutos, IDs únicos e modelos normalizados. Como a API pública atualmente devolve uma janela fixa de 50 resultados e ignora `limit`/`offset`, a paginação passou a preservar a ordem dos IDs e fatiá-los client-side, evitando repetição da primeira página. Valores float vindos do Slider do Gradio são normalizados para inteiros antes do slicing. A busca sem termo agora funciona como modo de navegação padrão: o adapter omite `q` e usa os resultados default oferecidos pela API, mantendo paridade com a experiência do CivitAI.
**Arquivos alterados:** `scripts/civitai_api.py`, `scripts/browser_sources/civarchive.py`, `tests/test_browser_sources.py`.
**Decisões:** Manter `browser_source://` como token opaco restrito à camada de adapters; nunca encaminhá-lo ao cliente HTTP. Paginar apenas a janela retornada pelo CivArchive até existir um endpoint público com paginação real.
**Pontos sensíveis:** A busca do CivArchive ainda faz fetch de detalhe para os IDs da página atual porque o payload de search não contém arquivos completos. Validação estática concluída com **110 passed + 2 subtests passed**, `py_compile` e `git diff --check`; runtime na WebUI pendente.
**Próximos passos / Next steps:**
- Repetir a busca no CivArchive e confirmar os logs `raw_results`, `unique_model_ids`, `page_model_ids` e `normalized_models`.
- Validar cards, Next/Prev e detail panel do CivArchive.
- Prosseguir com a validação do Hugging Face e finalizar o Arc en Ciel.

---

### 2026-07-08 — Fix Browser source callback contract and diagnostics

**O que mudou (pt-BR):** Corrigida uma regressão da Fase A que quebrava todas as buscas da aba Browser, inclusive CivitAI. O dropdown `source` era o 12º input do callback Gradio, mas `initial_model_page` interpretava esse valor como `from_update_tab` e `next_model_page` como `isNext`. Como nomes de fonte são strings truthy, a busca inicial desviava para o fluxo de Update Mode sem chamar nenhum adapter, resultando apenas na mensagem genérica de erro e sem logs `[DEBUG]`. As assinaturas de busca inicial/Next/Prev agora compartilham a mesma ordem posicional, e os flags internos passaram a keyword-only. Também foi adicionado um wrapper de execução dos adapters com diagnóstico de início, tipo de retorno, exceção e traceback quando debug está ativo. A mensagem genérica deixou de citar exclusivamente a API CivitAI.
**Arquivos alterados:** `scripts/civitai_api.py`, `scripts/civitai_file_manage.py`, `tests/test_browser_callback_contract.py`; preservados também os ajustes locais em `scripts/browser_sources/arcenciel.py` e `tests/test_browser_sources.py`.
**Decisões:** Manter os 12 inputs compartilhados do Browser idênticos em `initial_model_page`, `next_model_page` e `prev_model_page`; usar argumentos keyword-only para controles internos que não vêm do Gradio; capturar exceções no limite comum dos adapters para que falhas futuras indiquem a fonte responsável.
**Pontos sensíveis:** Validação estática concluída (`py_compile`, `git diff --check`) e suíte completa com **108 passed + 2 subtests passed**. Validação runtime na WebUI ainda necessária para CivitAI, CivArchive, Hugging Face e Arc en Ciel, incluindo Next/Prev.
**Próximos passos / Next steps:**
- Reiniciar o Forge Neo e executar smoke test de busca + Next/Prev nas quatro fontes.
- Finalizar a validação runtime do Arc en Ciel: cards, detail panel, download, SHA256 e sidecars.
- Só iniciar a Fase E (ModelScope) após fechar a validação do Arc en Ciel.

---

### 2026-07-08 — Plano aprovado: Multi-Browser Neo (browser_sources)

**O que mudou (pt-BR):** Decidido expandir o Browser para suportar múltiplas fontes de modelos. A nomenclatura interna muda de `civitai_source` para `browser_source`, preparando terreno para um futuro rename do app para `sd-multi-browser-neo`. A prioridade mandatória é **não quebrar o módulo existente**: todas as funções atuais (search, download, update, organize, dashboard, LoraDex) continuam funcionando exatamente como hoje, e as novas origens agregam informações por cima.

**Estrutura planejada:**
- `scripts/browser_sources/` — módulo de adapters:
  - `base.py` → classe abstrata `BrowserSource`
  - `registry.py` → `get_browser_source(name)`
  - `normalizer.py` → converte payloads externos para formato canônico
  - `civitai.py`, `civarchive.py`, `huggingface.py`, `arcenciel.py`, `modelscope.py`
- Formato canônico mantém compatibilidade com o formato CivitAI já esperado por `model_list_html`, `selected_to_queue`, `save_model_info`, etc.
- Novos campos no sidecar: `browserSource`, `browserSourceId`, `browserSourceVersionId`, `browserSourceUrl`, `browserSourceDownloadUrl`, `browserSourceSha256`, `browserMirrors`.
- Settings novas usarão prefixo `browser_source_*`; settings antigas (`civitai_api_key`, etc.) permanecem inalteradas.
- UI: dropdown **Source** na aba Browser (`CivitAI`, `CivArchive`, `Hugging Face`, `arcenciel.io`, `ModelScope`).

**Fases de implementação aprovadas:**
1. **Fase A — Fundação:** criar `browser_sources/`, mover CivitAI para adapter, adicionar dropdown Source, garantir que CivitAI continua funcionando.
2. **Fase B — CivArchive:** search por ID/SHA256, download, fallback em Update Models para modelos deletados.
3. **Fase C — Hugging Face:** search por texto, download direto, mapeamento de repo → tipo/base model.
4. **Fase D — arcenciel.io:** metadados públicos, download via `externalDownloadUrl`, Link Key opcional.
5. **Fase E — ModelScope:** search + filtro SD/LoRA, download via `/resolve/`.
6. **Fase F — Cross-source:** comparação SHA-256, mirrors no sidecar, badges "available elsewhere".
7. **Fase G — Rename futuro:** renomear repo/app para `sd-multi-browser-neo` (sem data definida).

**Decisões:** O nome da aba e do repo permanecem "CivitAI Browser Neo" até a Fase G. Sidecars antigos continuam válidos; novos campos são adicionados sem remover os antigos (`modelId`, `modelVersionId`, etc.). A comparação cross-source será baseada em SHA-256.

**Arquivos envolvidos (Fase A):** `scripts/browser_sources/*`, `scripts/civitai_api.py`, `scripts/civitai_gui.py`.

---

### 2026-07-08 — Fase A implementada: adapter CivitAI + dropdown Source

**O que mudou (pt-BR):** Criada a fundação do Multi-Browser Neo. CivitAI foi refatorada para um adapter dentro de `scripts/browser_sources/`, e a aba Browser ganhou um dropdown **Source:** mantendo CivitAI como padrão. Todas as funções existentes continuam intactas; a nova camada apenas encapsula a origem da busca.

**Arquivos criados:**
- `scripts/browser_sources/__init__.py` — registra adapters built-in.
- `scripts/browser_sources/base.py` — classe abstrata `BrowserSource` com contrato de search, fetch, download e normalização.
- `scripts/browser_sources/registry.py` — `register_source`, `get_browser_source`, `source_choices`, `source_name_from_display`, `default_source`.
- `scripts/browser_sources/normalizer.py` — `canonical_model`, `canonical_version`, `canonical_file`, `canonical_image`, `paginated_result`, `get_sha256`.
- `scripts/browser_sources/civitai.py` — adapter `CivitAISource` que encapsula `create_api_url`, busca por SHA256, paginação e proveniência `browserSource*`.
- `tests/test_browser_sources.py` — testes unitários isolados para o adapter CivitAI.

**Arquivos alterados:**
- `scripts/civitai_global.py` — adicionado `current_browser_source` ao estado global.
- `scripts/civitai_api.py` — adicionados `_get_browser_source()` e `_source_display_to_name()`; `initial_model_page`, `next_model_page`, `prev_model_page` agora aceitam `source` e delegam para o adapter; `insert_metadata` é no-op para URLs `browser_source://`; paginação reconstrói URLs quando o cache não bate com a página solicitada.
- `scripts/civitai_gui.py` — adicionado dropdown `source`, parâmetro `src` em `saveSettings`, `source` salvo/restaurado nos defaults, `source` incluído em `page_inputs`, `refresh_inputs`, `load_to_browser_inputs`; `_post_download_page_refresh` reconhece URLs `browser_source://`.
- `scripts/civitai_file_manage.py` — `exit_update_mode` aceita o parâmetro `source` opcional para compatibilidade com `load_to_browser_inputs`.

**Decisões técnicas:**
- O adapter produz itens no formato canônico compatível com `model_list_html`, `update_model_versions`, `update_model_info` e `selected_to_queue`.
- URLs `browser_source://{name}/page/{n}` são tokens opacos; o adapter as ignora e reconstrói a partir dos parâmetros quando necessário.
- URLs reais do CivitAI são cacheadas em `gl.url_list` para saltos diretos de página, mas são validadas contra o número da página solicitada para evitar buscar a página errada.
- O default do dropdown é CivitAI (`_browser_sources.source_choices()[0]`), garantindo comportamento idêntico para usuários existentes.

**Testes:**
- `python -m pytest tests/` → 91 passed (incluindo os 8 novos do adapter).
- `python -m py_compile scripts/browser_sources/*.py scripts/civitai_api.py scripts/civitai_gui.py scripts/civitai_file_manage.py scripts/civitai_global.py` → sem erros de sintaxe.

**Próximo passo:** Fase B — adapter CivArchive para fallback de modelos deletados.

---

### 2026-07-08 — Fase B implementada: adapter CivArchive

**O que mudou (pt-BR):** Adicionado o segundo browser source, **CivArchive**, como fallback para modelos deletados do CivitAI. O dropdown Source agora lista `CivitAI` e `CivArchive`.

**Arquivos criados:**
- `scripts/browser_sources/civarchive.py` — adapter `CivArchiveSource` com:
  - Busca por nome via `/api/search?q=...` (suporta `type`, `base_model`, `limit`, `offset`).
  - Busca por SHA256 via `/api/sha256/{hash}`.
  - Detalhe de modelo via `/api/models/{id}?modelVersionId={vid}`.
  - Resolução de download preferindo mirrors ativos; fallback para `downloadUrl` do CivArchive.
  - Normalização para o formato canônico com campos `browserSource*`, mantendo compatibilidade com `model_list_html`, `update_model_info` e `selected_to_queue`.

**Arquivos alterados:**
- `scripts/browser_sources/__init__.py` — registra `civarchive` após `civitai`.
- `tests/test_browser_sources.py` — testes para `CivArchiveSource` (search types, mirror selection, normalização de payload real).

**Decisões técnicas:**
- CivArchive não expõe paginação numérica; `page`/`page_size` são mapeados para `limit`/`offset`.
- Resultados de search misturam `kind: file` e `kind: version`; o adapter coleta `model_id` únicos e busca o modelo completo para cada um, garantindo cards consistentes.
- Download prefere mirrors não deletados; se todos estiverem deletados, ainda usa o primeiro mirror como último recurso.
- O adapter reutiliza headers/proxies do helper de CivitAI (`_api.get_headers` / `_api.get_proxies`) para manter o mesmo comportamento de rede.

**Testes:**
- `python -m pytest tests/` → 95 passed.
- `python -m py_compile scripts/browser_sources/*.py scripts/civitai_api.py scripts/civitai_gui.py scripts/civitai_file_manage.py scripts/civitai_global.py` → sem erros.

**Próximo passo:** Fase C — adapter Hugging Face (search por texto + download direto de repos públicos).

---

### 2026-07-08 — Fase C implementada: adapter Hugging Face

**O que mudou (pt-BR):** Adicionado o terceiro browser source, **Hugging Face**, ao dropdown Source. O adapter permite buscar repositórios públicos do HF por nome e baixar arquivos de modelo diretamente via URLs `/resolve/main/`.

**Arquivos criados:**
- `scripts/browser_sources/huggingface.py` — adapter `HuggingFaceSource` com:
  - Busca por nome via `https://huggingface.co/api/models?search=...&full=true`.
  - Uso de `siblings` do resultado de busca para construir arquivos e previews sem requisições extras.
  - Detalhe de repositório via `https://huggingface.co/api/models/{repo_id}`.
  - Listagem de arquivos via `https://huggingface.co/api/models/{repo_id}/tree/main`.
  - Heurísticas para inferir **content type** (Checkpoint, LORA, TextualInversion, etc.) a partir de tags HF, `pipeline_tag` e nome do repo.
  - Heurísticas para inferir **base model** a partir de tags `base_model:...`, tags HF e nome do repo (SDXL, SD 1.5, Pony, FLUX, Anima, etc.).
  - Download URL direto: `https://huggingface.co/{repo_id}/resolve/main/{file}`.

**Arquivos alterados:**
- `scripts/browser_sources/__init__.py` — registra `huggingface` após `civarchive`.
- `tests/test_browser_sources.py` — atualiza expectativa de sources registradas e adiciona testes unitários para `HuggingFaceSource`.

**Decisões técnicas:**
- Hugging Face não fornece SHA256 nos endpoints públicos usados; o hash será calculado localmente após o download, como já acontece hoje.
- A paginação é feita client-side (slice sobre resultados da busca) porque o endpoint de search do HF é cursor-based e não expõe `offset` de forma confiável.
- Para **Checkpoint** e **LoRA** (incluindo LoCon/DoRA), apenas arquivos `.safetensors` são listados. Outros tipos mantêm `.ckpt`, `.pt`, `.pth`, `.bin`, `.onnx`.
- Quando as tags HF não trazem base model ou trigger words, o adapter baixa `README.md` do repo e extrai:
  - **Base model** a partir de linhas como `Base model: SDXL`, `Base_model: ...`, etc.
  - **Trigger words** a partir de linhas/seções como `Trigger words: ...`, `Trigger word: ...`, etc.
- Imagens nos siblings viram previews/galeria.
- O dropdown Source agora lista `CivitAI`, `CivArchive`, `Hugging Face` automaticamente via registry.

**Testes:**
- `python -m pytest tests/` → 102 passed.
- `python -m py_compile scripts/browser_sources/*.py scripts/civitai_api.py scripts/civitai_gui.py scripts/civitai_file_manage.py` → sem erros.
- Teste manual de API: search retornou repos, `/tree/main` listou arquivos `.safetensors`, `README.md` retornou texto, e `HEAD` na URL `/resolve/main/` retornou `200` com `Content-Length`.

**Próximo passo:** Fase D — adapter arcenciel.io (metadados públicos + download direto).

---

### 2026-07-08 — Fase D implementada: adapter arcenciel.io

**O que mudou (pt-BR):** Adicionado o quarto browser source, **arcenciel.io**, ao dropdown Source. A plataforma é focada em modelos anime/NoobAI/Anima e já fornece metadados ricos via API pública, incluindo base model, activation tags, SHA256 e imagens.

**Arquivos criados:**
- `scripts/browser_sources/arcenciel.py` — adapter `ArcencielSource` com:
  - Busca por nome via `https://arcenciel.io/api/models/search?q=...`.
  - Detalhe de modelo via `https://arcenciel.io/api/models/{id}`.
  - Detalhe de versão via `https://arcenciel.io/api/models/{id}/versions/{version_id}`.
  - Download direto via `https://uploads.arcenciel.io/api/models/{id}/versions/{version_id}/download` (descoberto inspecionando a UI do site).
  - Previews e galeria via `https://media.arcenciel.io/uploads/{filePath}`, preferindo variants webp (`w1024`, `w512`) quando disponíveis.
  - Normalização para formato canônico com base model, activation tags como `trainedWords`, SHA256 e estatísticas.

**Arquivos alterados:**
- `scripts/browser_sources/__init__.py` — registra `arcenciel` após `huggingface`.
- `tests/test_browser_sources.py` — atualiza expectativa de sources registradas e adiciona testes unitários para `ArcencielSource`.

**Decisões técnicas:**
- arcenciel.io já entrega `baseModel`, `sha256`, `activationTags` e `fileSizeKb` diretamente na API, então a experiência é mais completa que a do Hugging Face sem precisar de heurísticas extras.
- O download não precisa de Link Key para repos públicos; a URL `uploads.arcenciel.io/api/models/{id}/versions/{vid}/download` funciona sem autenticação.
- Imagens usam o CDN `media.arcenciel.io`; o adapter escolhe a variant webp de 1024px (ou 512px) para economizar banda, fallback para o arquivo original.
- A ordenação das versões respeita `versionOrder` retornado pela API.

**Testes:**
- `python -m pytest tests/` → 106 passed.
- `python -m py_compile scripts/browser_sources/*.py ...` → sem erros.
- Teste manual de API: search retornou modelos, `/models/{id}` retornou detalhes, `HEAD` na URL de download retornou `200 application/octet-stream` com `Content-Length`, e `HEAD` na URL de imagem retornou `200 image/webp`.

**Próximo passo:** Fase E — adapter ModelScope (search + filtro SD/LoRA, download via `/resolve/`).

---

### 2026-07-08 — Regra de ouro: CivitAI é a fonte principal; double-check por SHA256

**O que decidiu (pt-BR):** CivitAI continua sendo e sempre será a fonte principal de verdade para metadados, previews e validação. Quando um modelo for encontrado em fontes externas (Hugging Face, arcenciel.io, CivArchive, ModelScope, etc.), o extension deve sempre tentar fazer um **double-check pelo SHA256** contra a CivitAI.

**Comportamento planejado (Fase F — Cross-source):**
1. Para cada arquivo canônico vindo de uma fonte externa, obter seu SHA256 (quando a API da fonte entregar; caso contrário, calcular localmente após o download).
2. Consultar `https://civitai.com/api/v1/model-versions/by-hash/{sha256}` (e/ou `civitai.red`) para verificar se o CivitAI conhece aquele arquivo.
3. Se o CivitAI retornar um match:
   - Usar os metadados ricos do CivitAI (nome, versão, base model, trigger words, tags, previews, permissões) como fonte primária de exibição.
   - Manter a URL de download da fonte original (o usuário escolheu baixar de lá).
   - No **detail panel**, adicionar uma tag/visual indicando: **"Verified on CivitAI"** (ou similar) com link para a página do modelo no CivitAI.
4. Se não houver match:
   - Exibir os metadados da fonte externa mesmo.
   - Adicionar tag/visual: **"Not found on CivitAI"** ou **"CivitAI-independent"**.

**Por quê:**
- Evita duplicatas e confusão quando o mesmo arquivo existe em várias plataformas.
- Garante que o usuário tenha a melhor experiência de metadados possível (CivitAI é mais completo para SD/LoRA).
- Respeita a decisão do usuário de baixar de uma fonte alternativa (por fallback, velocidade, mirror, etc.) sem perder a riqueza da informação.

**Onde entra no código (futuro):**
- Novo helper cross-source em `scripts/browser_sources/cross_source.py`: `lookup_civitai_by_sha256(sha256)`.
- `scripts/civitai_api.py` no detalhe do modelo: após renderizar o bloco `Browser Source`, consultar CivitAI e injetar o badge de verificação.
- Sidecar `.api_info.json` pode armazenar `civitaiVerified`, `civitaiModelId`, `civitaiVersionId` para cache entre sessões.

**Arquivos envolvidos (planejado):** `scripts/browser_sources/cross_source.py`, `scripts/civitai_api.py`, `style.css`.

---

### 2026-07-08 — UI de proveniência: source badge no card e bloco Browser Source no detail panel

**O que mudou (pt-BR):** Adicionada indicação visual de origem do modelo tanto nos cards quanto no painel de detalhes, preparando a UI para o Multi-Browser Neo.

1. **Source badge no card:** modelos cuja origem é diferente de CivitAI (ex.: CivArchive) exibem um badge `CIVARCHIVE` no canto superior do card, com cor roxa distinta. Dados legados do CivitAI não exibem badge, mantendo a aparência atual.
2. **Bloco Browser Source no detail panel:** novo quadro posicionado entre *Version Information* e *Permissions*, visível apenas para modelos de fontes externas. Mostra:
   - **Source** — badge com o nome da origem (`CivArchive`, etc.)
   - **External ID** — ID do modelo na origem externa
   - **Note** — aviso explicativo quando aplicável (ex.: CivArchive é backup espelhado)
   - **Download Mirrors** — lista de mirrors com URL clicável e status **Active** (borda verde) ou **Deleted** (borda vermelha/opacidade reduzida)
3. **Layout de três colunas:** o container `info-permissions-container` agora distribui `Version Information | Browser Source | Permissions` lado a lado em telas grandes; em telas menores (≤1500px) empilha verticalmente.

**Arquivos alterados:** `scripts/civitai_api.py`, `style.css`.
**Decisões:** O bloco `Browser Source` só é renderizado quando `browserSource != 'civitai'`, então modelos do CivitAI continuam com o layout atual de duas colunas. O link de download principal (`model_url`) continua apontando para o melhor mirror ativo via adapter. A lista de mirrors é omitida quando não há dados de espelhamento. O CSS do novo bloco segue a paleta roxa do CivArchive para diferenciar visualmente do bloco verde de Permissions.
**Pontos sensíveis:** Apenas o arquivo primário/selecionado é consultado para mirrors; modelos com múltiplos arquivos mostrarão os mirrors do arquivo principal. O status `deleted` é inferido da presença de `deletedAt` no mirror.

---

### 2026-07-08 — LoraDex: botões de ação em lote agora indicam "página atual"

**O que mudou (pt-BR):** Os botões de ação em lote do LoraDex tiveram os labels alterados para deixar claro que afetam **apenas a página atual**:
- `✅ Apply all pending` → `✅ Apply page changes`
- `↺ Reset all pending` → `↺ Reset page changes`

Os textos de status também foram ajustados para "Applied X change(s) on this page" e "Reset pending changes on this page".

**Motivação:** O comportamento técnico já era esse — o LoraDex só renderiza a página atual no DOM, então `loradexApplyAll()` só encontra linhas pendentes da página visível. Porém, o label antigo podia sugerir que a operação afetaria toda a coleção. A mudança remove essa ambiguidade sem alterar a lógica.

**Arquivos alterados:** `scripts/civitai_gui.py`, `scripts/civitai_file_manage.py`.

---

### 2026-07-08 — Pesquisa de integração com plataformas de modelos gratuitas

**O que mudou (pt-BR):** Levantamento e validação técnica de fontes alternativas de modelos/LoRAs com API/token gratuita para download real de arquivos. Quatro plataformas foram investigadas; duas já têm endpoints confirmados e duas precisam de mais mapeamento.

**Plataformas validadas:**

| Plataforma | API de metadados | Download de arquivo | Autenticação | Observações |
|---|---|---|---|---|
| **CivitAI** | `https://civitai.com/api/v1/...` | Redirect assinado via `downloadUrl` | Token gratuito `?token=` ou `Authorization: Bearer` | Já integrado; rate limits agressivos (HTTP 429). |
| **CivArchive** | `GET https://civarchive.com/api/models/{id}`<br>`GET https://civarchive.com/api/sha256/{sha256}` | `GET https://civarchive.com/api/download/models/{version_id}?type=Model&format=SafeTensor` | Não identificada para leitura | Fallback para modelos deletados do CivitAI. |
| **Hugging Face** | `GET https://huggingface.co/api/models?search=...` | `https://huggingface.co/{repo_id}/resolve/main/{filename}` | Leitura pública sem token; repos gated precisam de aceite + token | Mais estável; ideal como mirror primário. |
| **arcenciel.io** | `GET https://arcenciel.io/api/models/classes`<br>`GET https://arcenciel.io/api/models/search?...`<br>`GET https://arcenciel.io/api/models/{id}`<br>`GET https://arcenciel.io/api/models/{id}/versions/{version_id}` | Via `externalDownloadUrl` (geralmente HuggingFace) ou possivelmente `https://arcenciel.io/models/{filePath}` | Metadados públicos; download/fila precisa de **Link Key** (`lk_...`) ou API key legada no header `x-link-key` / `x-api-key` | Comunidade ativa de anime/NoobAI; extensão ComfyUI oficial. Base do Link: `https://link.arcenciel.io/api/link`. |
| **ModelScope** | `GET https://www.modelscope.cn/openapi/v1/models?search=...`<br>`GET https://www.modelscope.cn/openapi/v1/models/{owner}/{name}`<br>`GET https://www.modelscope.cn/api/v1/models/{owner}/{name}/repo/files?Revision=...` | `https://www.modelscope.cn/models/{owner}/{name}/resolve/{revision}/{file_path}` | Leitura pública sem token; token para repos privados/gated | Chinês, mas CORS aberto; bom para modelos Qwen/Wan/FLUX. |

**Plataformas descartadas:**
- **Liblib.art**: API só no plano Pro (pagamento chinês).
- **Tensor.Art, SeaArt, PixAI**: plataformas de geração online, não repositórios de download de arquivo.

**Decisões:** A próxima fase de integração deve priorizar **Hugging Face** (mais simples e estável) e **CivArchive** (fallback deletados) como primeiros conectores. **arcenciel.io** e **ModelScope** vêm depois, pois exigem UI de configuração de token/Link Key e mapeamento de tipos de modelo. Nenhum código de integração foi escrito nesta etapa — apenas levantamento e requisições de validação.

**Arquivos alterados:** `docs/PROJECT_LOG.md`.
**Pontos sensíveis:** Os endpoints foram testados em 2026-07-08; APIs de terceiros podem mudar. O download do arcenciel.io sem Link Key ainda não foi confirmado; a URL `externalDownloadUrl` aponta para HuggingFace, o que pode ser usado como fallback. ModelScope retorna 404 no endpoint legacy `/api/v1/models/{id}/repo?FilePath=...` sem autenticação, mas o endpoint `/resolve/` funciona publicamente.

---

### 2026-07-08 — Organization modular: base model + categoria de LoRA

**O que mudou (pt-BR):** A aba **Organization** ganhou dois toggles independentes acima dos botões de organização:
- **Organize by base model** (default: valor da setting `civitai_neo_auto_organize`)
- **Organize LoRAs by category** (default: valor da setting `civitai_neo_lora_category_sort`)

O usuário pode agora escolher organizar apenas por base, apenas por categoria, ou ambos. A hierarquia é sempre **Base > Category**. Exemplos para a pasta `Lora/`:
- Só base: `Lora/Anima/`
- Só categoria: `Lora/Character/`
- Ambos: `Lora/Anima/Character/`

A função `analyze_organization_plan()` foi reescrita para computar o `target_suffix` a partir dos flags selecionados, detectando também cenários de reorganização (ex.: mover de `Lora/Character/` para `Lora/Anima/Character/` quando o usuário muda de "só categoria" para "base + categoria"). `validate_organization()` e `fix_misplaced_files()` também passaram a receber os mesmos flags. A categoria é calculada com a heurística completa (tags + descrição + nome do arquivo/nome CivitAI), respeitando categoria manual salva no sidecar.

**Arquivos alterados:** `scripts/civitai_gui.py`, `scripts/civitai_file_manage.py`.
**Decisões:** Os toggles da UI refletem as settings de download automático, mas são inputs independentes da operação manual — o usuário pode organizar manualmente de forma diferente do download automático sem alterar as settings. Non-LoRAs ignoram a categoria. Se ambos os toggles estiverem OFF, a operação mostra um aviso e não move nada.
**Pontos sensíveis:** Reorganizações em larga escala (ex.: de `Lora/<categoria>/` para `Lora/<base>/<categoria>/`) podem mover muitos arquivos; o backup/rollback continua funcionando normalmente. Modelos sem base model detectado e com base ON caem em `Other`; com base OFF e categoria ON, vão diretamente para `Lora/<categoria>/`.
**Commit:** `4b76906` — branch `revamp`.

### 2026-07-08 — LoraDex: nome/versão CivitAI, CSS corrigido, auto-sugestão e categoria Slider

**O que mudou (pt-BR):** Quatro melhorias na aba **LoraDex**:
1. **CSS corrigido:** o HTML da lista agora é envolvido com `_wrap_html_with_css()`, então o grid/table do LoraDex é renderizado corretamente (mini-thumbnail, linhas separadas, colunas alinhadas) em vez de imagens gigantes empilhadas.
2. **Nome e versão corretos:** em vez de exibir o nome do arquivo no disco, o LoraDex agora mostra o nome do modelo da CivitAI (`model.name` do `.api_info.json`) e o nome da versão instalada (`name` do `.api_info.json`). Fallback para nome do arquivo apenas quando o sidecar não existe.
3. **Auto-sugestão de categoria:** a heurística de categorização agora também usa a **descrição** do modelo como fallback quando as tags não batem. No LoraDex, se não houver categoria manual salva (`Auto`) e a heurística encontrar uma categoria, o dropdown já abre pré-selecionado com a sugestão e a linha é sinalizada com borda azul e badge 🤖. O usuário pode aplicar, alterar ou ignorar cada sugestão.
4. **Nova categoria Slider:** adicionada categoria `Slider` para LoRAs que aumentam/diminuem uma característica. A heurística detecta keywords como `slider`, `increase`, `decrease`, `boost`, `reduce`, `more`, `less`, etc. e também padrões semânticos fortes como `"X slider"`, `"slider for X"`, `"increase X"`, `"more X"`, `"X adjuster"`. A semântica Slider tem prioridade sobre o matching genérico de keywords, então um "breast slider" vira Slider em vez de Clothing.
5. **Coluna Filename + colunas base/version reduzidas:** a tabela do LoraDex ganhou uma coluna **Filename** (o nome exibido nos cards do Extra Networks) logo após o thumbnail; as colunas Base model e Version foram estreitadas para economizar espaço.

**Arquivos alterados:** `scripts/civitai_file_manage.py`, `style_html.css`, `style.css`.
**Decisões:** `categorize_lora_by_tags()` ganhou parâmetros `description` e `name_hints`, além de uma pré-verificação de semântica Slider. A sugestão só aparece quando `saved_category == 'Auto'`; categorias manuais nunca são sobrescritas. As sugestões entram no estado "pending" (amarelo) junto com alterações manuais, mas têm classe/CSS distinta `loradex-suggested` para indicar origem automática.
**Pontos sensíveis:** Match por descrição/nome é substring case-insensitive, então pode haver raros falsos positivos; tags ainda têm prioridade (exceto pela semântica Slider, que é pré-verificada). Modelos sem `.api_info.json` continuam com nome de arquivo e versão vazia, mas ainda podem ser categorizados manualmente.
**Commits:** `ca8cd73` (CSS), `b012ea9` (nome/versão), `2161cd6` (auto-sugestão), `cfda816` (Slider), `9f627b5` (filename/model-name hints), `6b04c85` (coluna filename + colunas reduzidas) — branch `revamp`.

### 2026-07-08 — Fallback de `modelTags` no `.json` sidecar

**O que mudou (pt-BR):** O sidecar `.api_info.json` retornado pelo endpoint `/model-versions/by-hash` da CivitAI **não contém tags do nível do modelo**. Para não depender só dele, `find_and_save()` passou a persistir as `modelTags` (tags do nível do modelo) também no `.json` sidecar durante o download e durante **"Update model info & tags"** (tanto com overwrite ON quanto OFF — no OFF só adiciona se a chave ainda não existir). Com isso, três fluxos passam a usar `modelTags` do `.json` como fallback quando não há tags no `.api_info.json`/API:
1. **Organização em lote** (`get_model_info_for_organization` → `analyze_organization_plan`).
2. **LoraDex** (`_lora_dex_tags`).
3. **Download/update de LoRAs** (`selected_to_queue` lê `modelTags` do sidecar do arquivo instalado existente quando `version.tags` vem vazio).

**Arquivos alterados:** `scripts/civitai_file_manage.py`, `scripts/civitai_download.py`.
**Decisões:** Nova helper `_read_model_tags_from_sidecar(file_path)` centraliza a leitura. Tags manuais/categoria manual continuam tendo prioridade sobre a heurística. Se a API/resposta perder tags no futuro, o sidecar preserva o último valor conhecido.
**Pontos sensíveis:** Apenas o `.json` sidecar passa a crescer ligeiramente (uma lista de strings). A heurística de categoria de LoRA continua a mesma; o fallback só aumenta a chance de acerto para modelos já instalados ou atualizados.
**Commit:** `310d720` — `feat(python): fallback modelTags from .json sidecar for LoraDex, org and update` (branch `revamp`).

### 2026-07-07 — LoraDex: gerenciador manual de categorias de LoRA

**O que mudou (pt-BR):** Adicionada a sub-aba **LoraDex** dentro de **Local Models** (ao lado do *Local Models Browser*). É uma lista vertical paginada que permite ao usuário revisar e ajustar manualmente a categoria de cada LoRA instalada. Cada linha exibe mini-thumbnail (com zoom no hover), nome, base model, versão e um dropdown de categoria; alterações ficam pendentes (destaque amarelo) até serem aplicadas individualmente ou em lote. As categorias manuais são persistidas no `.json` sidecar (`loraCategory`) e têm prioridade sobre a heurística de tags tanto no download quanto na organização em lote.
**Arquivos alterados:** `scripts/civitai_global.py`, `scripts/civitai_gui.py`, `scripts/civitai_file_manage.py`, `scripts/civitai_download.py`, `javascript/civitai-html.js`, `style_html.css`.
**Decisões:** A aba *Local Models* foi convertida em `gr.Tabs` com duas sub-abas (`Local Models Browser` e `LoraDex`). O backend escaneia apenas a pasta `Lora`, lê metadados dos sidecars `.api_info.json`/`.json` e renderiza HTML customizado com paginação própria. `categorize_lora_by_tags()` agora aceita `manual_category`; `get_model_info_for_organization()` retorna a categoria manual; `analyze_organization_plan()` e `selected_to_queue()` a usam para decidir a subpasta. Categorias suportadas no dropdown: `Auto`, `Character`, `Style`, `Clothing`, `Concept`, `Pose`, `Background`, `Utility`, `None`. `Auto` remove a chave do sidecar; `None` grava `null`; demais gravam a string.
**Pontos sensíveis:** LoRAs sem `.api_info.json` exibem base model/versão como `Unknown`/vazio, mas ainda podem ser categorizados manualmente. O preview usa `file://` via URL relativa `file/<path>` do Gradio. Aplicação em lote re-renderiza a página atual mantendo filtros.

### 2026-07-07 — Fix `download_finish` crash on empty Update-selected queue

**O que mudou (pt-BR):** Corrigido `TypeError` em `scripts/civitai_download.py:752` quando `gl.last_version` era `None` no callback `download_finish`. O erro ocorria ao usar **Update selected** no painel Local Models sem nenhum card marcado (ou quando o trigger disparava antes de a fila ser populada), enquanto **Update to latest** não apresentava o problema porque sempre carregava `gl.update_items`.
**Arquivos alterados:** `scripts/civitai_download.py`.
**Decisões:** Substituída a concatenação direta `gl.last_version + " [Installed]"` por uma guarda que só marca a versão como instalada quando `last_version` existe. Se for `None`, o fluxo segue normalmente sem marcar o botão Delete.
**Pontos sensíveis:** O fix é puramente defensivo; o comportamento correto do botão **Update selected** continua exigindo que o usuário marque os checkboxes dos cards desatualizados.
**Commit:** `0de650b fix(python): guard last_version None in download_finish` (branch `revamp`).

### 2026-07-07 — Preview JPEG format + Aria2 HTTP 429 retry/backoff

**O que mudou (pt-BR):** Adicionadas duas melhorias de resiliência/economia inspiradas no `SiliconeShojo/models-info`:
1. **Preview JPEG:** novas settings `preview_format` (PNG/JPEG, default PNG) e `preview_jpeg_quality` (50–100, default 90). Quando JPEG está ativo, previews principais (`<model>.preview.jpg`) e imagens da galeria (`<model>_N.jpg`) são salvas em JPEG com qualidade configurável, reduzindo espaço em disco. PNG permanece o default para preservar comportamento atual e transparência.
2. **Retry/backoff no Aria2 para HTTP 429:** `download_file` agora detecta quando o Aria2 reporta `errorCode=29` com mensagem contendo `429`/`Too Many Requests`. Nesse caso, remove o download atual, espera um backoff exponencial (máx 60s) e re-adiciona com um link de download fresco obtido via `get_download_link`. Máximo de 5 retries; outros erros mantêm falha imediata.
**Arquivos alterados:** `scripts/civitai_gui.py`, `scripts/civitai_file_manage.py`, `scripts/civitai_download.py`.
**Decisões:** `_resize_image_bytes` passou a aceitar `fmt` e `quality`, e `target_size=None` para re-encode sem redimensionar. `save_preview` e `save_images` passaram a usar a extensão correta e a converter RGB para JPEG. Ao salvar no novo formato, o preview/galeria antigo na extensão contrária é removido (`send2trash` com fallback `os.remove`) para evitar duplicatas quando a setting é alterada e o usuário roda "Update model info & tags" com overwrite. O delete/move de arquivos associados já procurava pelo stem `.preview`, então `.preview.jpg` continua sendo tratado corretamente.
**Pontos sensíveis:** O formato PNG continua sendo o padrão; usuários precisam alterar explicitamente a setting para JPEG. O retry de 429 depende de `get_download_link` conseguir renovar o link assinado — se a CivitAI mantiver o rate limit no endpoint de redirecionamento, o retry pode falhar.

### 2026-07-07 — LoRA category subfolders by tags

**O que mudou (pt-BR):** Adicionada organização automática de LoRAs em subpastas por categoria de uso baseada nas tags do modelo. Nova setting `civitai_neo_lora_category_sort` (default OFF) nas settings de Model Organization. Quando ativada junto com `civitai_neo_auto_organize`, LoRAs são organizadas em `Lora/<base>/<categoria>/` (ex.: `Lora/SDXL/Style/`, `Lora/Pony/Character/`). Categorias suportadas: Character, Style, Clothing, Concept, Pose, Background, Utility. Funciona tanto no download de novos modelos quanto na operação em lote **Update Models → Organize/Validate**.
**Arquivos alterados:** `scripts/civitai_gui.py`, `scripts/civitai_file_manage.py`, `scripts/civitai_download.py`.
**Decisões:** `get_model_info_for_organization()` passou a retornar também as tags do `.api_info.json`. A heurística de match é por substring case-insensitive nas tags, com a primeira categoria que der match vencendo. Apenas LoRAs são afetados; Checkpoints e outros tipos mantêm o comportamento atual. A validação de organização reutiliza `analyze_organization_plan`, então já reconhece paths `base/category` como corretos.
**Pontos sensíveis:** Modelos sem tags ou sem `.api_info.json` ficam diretamente em `Lora/<base>/`. A precisão depende das tags declaradas no CivitAI, que nem sempre são consistentes.

### 2026-04-17 — Prefer Latest Installed Card Status

**O que mudou (pt-BR):** Ajustada a lógica de borda dos cards para priorizar a versão mais nova já instalada do mesmo modelo, evitando que modelos permaneçam laranja quando a versão atual também está presente localmente.
**Arquivos alterados:** `scripts/civitai_api.py`.
**Decisões:** O status de card agora considera a presença de uma versão instalada atual como dominante; versões antigas no mesmo modelo não forçam mais o card para outdated quando a versão mais nova também está instalada.
**Pontos sensíveis:** A regra continua distinguindo modelos realmente desatualizados, mas não penaliza coleções que mantêm múltiplas versões instaladas do mesmo modelo.

### 2026-04-17 — Restore realtime Browser card updates

**O que mudou (pt-BR):** Corrigido o fluxo de atualização visual em tempo real dos cards no Browser após download/delete, com identificação estável por model_id e reaplicação automática do filtro de esconder instalados.
**Arquivos alterados:** `scripts/civitai_api.py`, `javascript/civitai-html.js`.
**Decisões:** Removido o acoplamento frágil ao texto do `onclick` para localizar cards; o estado do card agora é atualizado preservando outras classes visuais e reaplicando o hide-installed sem exigir novo refresh da busca.
**Pontos sensíveis:** Cards já renderizados antes da mudança continuam com fallback por `onclick`, mas novos renders usam `data-model-id` como fonte principal.

### 2026-03-13 — Trigger Words Group Preservation on Update Models

**O que mudou (pt-BR):** Ajustado o fluxo de "Update model info & tags" para preservar grupos de trigger words no mesmo formato do CivitAI. O sidecar agora salva `activation text groups` (lista por grupo) além do campo legado `activation text` consolidado.
**Arquivos alterados:** `scripts/civitai_api.py`, `scripts/civitai_file_manage.py`.
**Decisões:** O lookup local no painel passou a priorizar apenas o campo agrupado para evitar achatamento por split em vírgulas; fallback legado permanece opcional para cenários de compatibilidade.
**Pontos sensíveis:** Sidecars antigos sem `activation text groups` continuam dependentes da API para renderização em grupos até serem atualizados via "Update model info & tags".

### 2026-03-12 — Trigger Word Consolidation

**O que mudou (pt-BR):** Implementada consolidação de trigger words a partir de três fontes: metadata embutida em `.safetensors`, campo local `'activation text'` do `.json` sidecar e `trainedWords` da API. A exibição no painel usa lista unificada e sem duplicatas, mantendo fallback para API quando não existe cache local.
**Arquivos alterados:** `scripts/civitai_file_manage.py`, `scripts/civitai_api.py`.
**Decisões:** Parsing de metadata `.safetensors` feito via leitura do header (sem carregar tensores em memória); deduplicação case-insensitive preservando ordem de primeira ocorrência; lookup local do `.json` com fallback recursivo para suportar subpastas de organização (ex.: `Wan/I2V`).
**Pontos sensíveis:** Busca recursiva de `.json` pode crescer em custo em coleções muito grandes; cache local pode ficar desatualizado em relação à API até novo save/scan.

### 2026-03-10 — v0.7.4: Wan I2V/T2V Differentiation

**Contexto:** A API do CivitAI já retorna valores distintos de `baseModel` para subtypes Wan (`Wan Video 14B i2v 480p`, `Wan Video 2.2 T2V-A14B`, etc.). Aproveitamos isso para diferenciar visualmente nos cards e opcionalmente nas pastas.

#### Mudanças
- **`scripts/civitai_api.py`:** `BASE_MODEL_SHORT` mapeado para `'T2V'`, `'I2V'`, `'TI2V'` em vez de `'Wan'` genérico. Adicionados também `Flux.2 Klein` e `Flux.2 D` → `'F2'` (antes caía no fallback `'flux'` → `'F1'`, incorreto).
- **`scripts/civitai_file_manage.py`:** `normalize_base_model()` agora suporta opt-in de subpastas Wan por tipo. Check de "já organizado" corrigido para funcionar com caminhos multi-nível (`Wan/I2V`).
- **`scripts/civitai_gui.py`:** Nova setting `civitai_neo_wan_subfolder_by_type` (OFF por padrão) — quando ativa, organiza Wan em `Wan/I2V/`, `Wan/T2V/`, `Wan/TI2V/`.

#### Basemodels Wan confirmados na API
- `Wan Video 1.3B t2v` → T2V
- `Wan Video 14B t2v` → T2V
- `Wan Video 14B i2v 480p` → I2V
- `Wan Video 14B i2v 720p` → I2V
- `Wan Video 2.2 T2V-A14B` → T2V
- `Wan Video 2.2 I2V-A14B` → I2V
- `Wan Video 2.2 TI2V-5B` → TI2V

#### Commits
- `45e1200` feat: differentiate Wan I2V/T2V in base model short badges
- `01c07b9` feat: optional Wan I2V/T2V/TI2V subfolder organization
- `313775f` feat: add Flux.2 Klein / Flux.2 D base model short badges [NEO-ONLY]

**Contexto:** Criação dos arquivos de contexto para orientar agentes AI e humanos no desenvolvimento do projeto.

#### Arquivos Principais Mapeados
- **Backend Python:**
  - `scripts/civitai_gui.py` (2074 linhas) — Interface Gradio, callbacks, settings
  - `scripts/civitai_api.py` (2059 linhas) — Client CivitAI API, geração HTML, validação
  - `scripts/civitai_download.py` (1279 linhas) — Aria2 RPC, queue manager, hash check
  - `scripts/civitai_file_manage.py` (4058 linhas) — File ops, organização, dashboard, creator mgmt
  - `scripts/civitai_global.py` (70 linhas) — Estado global compartilhado (anti-pattern legacy)
  - `scripts/download_log.py` (173 linhas) — Persistência JSONL da queue

- **Frontend:**
  - `javascript/civitai-html.js` (1806 linhas) — Card interaction, tile sizing, UI dynamics
  - `style_html.css` + `style.css` — Estilos customizados

- **Infra:**
  - `install.py` — Hook do Forge para instalar dependencies
  - `aria2/` — Binários Win/Linux do Aria2

#### Features Confirmadas (README ↔ Código)
- ✅ Browse & Search com filtros avançados (base model, content type, period, sort)
- ✅ Download queue com Aria2 (multi-connection, cancel, progress)
- ✅ Queue persistence via `download_log.py` → `neo_download_queue.jsonl`
- ✅ SHA256 hash validation pós-download
- ✅ Auto-organization com backup (últimos 5 em `civitai_organization_backups.json`)
- ✅ Update detection (orange borders) com batch update
- ✅ Dashboard com breakdown por categoria/arquitetura, top 10 files/categories, orphan scan
- ✅ Creator management (favorite/ban) com persistência em `favoriteCreators.txt` / `bannedCreators.txt`
- ✅ Model info overlay com "Send to txt2img", LoRA syntax insertion
- ✅ Forge Neo folder compatibility (embeddings auto-detect, upscaler fallback)
- ✅ Smart version selection (respeita filtro de base model ativo)

#### Decisões Arquiteturais
1. **Estado Global (`gl.init()`):** Variáveis globais compartilhadas entre módulos (legacy design, não thread-safe)
   - `download_queue`, `json_data`, `json_info`, `recent_model`, etc.
   - Threading: `_not_downloading` event para sincronização de downloads
   - **Não refatorar sem planejamento:** usado em toda a codebase

2. **Aria2 RPC Lifecycle:** Start automático no import de `civitai_download.py`
   - Port 24000, secret `R7T5P2Q9K6`
   - Auto-reconnect se crashar durante sessão
   - Tracking file: `aria2/running`

3. **Filesystem Safety:**
   - Delete via `send2trash()` (recycle bin)
   - Sanitização de filename (illegal chars, max length)
   - Associated files (`.json`, `.png`, `.txt`) movem junto com model

4. **Queue Persistence (v0.6.2+):**
   - JSONL format em `config_states/neo_download_queue.jsonl`
   - Estados: `queued → downloading → completed/cancelled/failed/dismissed`
   - Restore banner aparece se houver entradas `queued` órfãs após disconnect

5. **Gradio 4+ Breaking Changes:**
   - APIs diferentes do Gradio 3 (usadas em sd-civitai-browser-ex)
   - Settings persistence via `elem_id` matching no `ui_config_file`
   - `gr.update()` syntax específica do Gradio 4

6. **Forge Neo vs. Classic Folder Differences:**
   - Embeddings: `models/embeddings/` (Neo) vs. `embeddings/` (Classic)
   - Upscalers: `models/ESRGAN/` (Neo unifica tudo) vs. subfolders separados (Classic)
   - Auto-detection implementada em `civitai_file_manage.py`

#### Pontos Sensíveis
- **Update detection sensível:** Comentário em `civitai_api.py:472` — "Sensitive check for updates by `name_match`... It is possible that an outdated version of the model will not be marked as outdated"
  - Comparação por nome pode falhar em edge cases
  - Considerar melhorar lógica de matching no futuro

- **NSFW check impreciso:** Comentário em `civitai_api.py:113` — "This nsfwlevel system is not accurate..."
  - Depende da metadata da CivitAI (não 100% confiável)
  - Fallback: check primeira imagem do model

- **Folder resolver None:** Debug print em `civitai_api.py:254` — "Warning: Folder resolver returned None for content_type"
  - Pode acontecer com content types desconhecidos
  - Fallback: pasta "Other" ou erro

- **Threading não totalmente thread-safe:**
  - `gl.download_queue` modificado por callbacks Gradio sem lock explícito
  - `_not_downloading` event protege apenas cancelamento/cleanup
  - Não observado bugs críticos, mas não ideal para concorrência pesada

---

### 2026-03-05 — Bugfix + Feature: Melhorias de Download de Wildcards

#### Bug Corrigido: IndentationError em `civitai_file_manage.py`
- **Root cause:** `if sha in installed_hashes:` não tinha corpo — `installed_versions.append()` estava no mesmo nível de indentação do `if`, e havia um `continue` solto abaixo
- **Fix:** Corrigida indentação com 4 espaços + substituído `continue` por `break`
- **Commit:** `680de02` — afetava apenas NEO (EX usa `installed_map`/`installed_all`, implementação diferente)

#### Feature: Melhorias no Download de Wildcards (`cfe322b` NEO / `b28f9bd` EX)
Três mudanças implementadas nos dois repositórios:

1. **Skip de imagens para Wildcards** — `save_preview` e `save_images` ignorados quando o `content_type` do item é `'Wildcards'`. Wildcards não têm localização útil para previews.

2. **Pasta própria por wildcard** (padrão: ON) — Cada wildcard é salvo em um subdiretório com o nome do modelo (ex: `wildcards/emotion-pack/emotion-pack.txt`). Compatível com o `__subfolder/name__` syntax do sd-dynamic-prompts.
   - Novo setting: `civitai_neo_wildcard_own_folder` (default=True)

3. **Organização por base model opcional** (padrão: OFF) — A separação por base model (`auto_organize`) que se aplicava a todos os tipos agora é opt-in para wildcards, porque wildcards são geralmente agnósticos à arquitetura.
   - Novo setting: `civitai_neo_wildcard_organize_by_base` (default=False)

#### Arquivos Alterados
- `scripts/civitai_download.py` (NEO + EX): `selected_to_queue()` + bloco pós-download
- `scripts/civitai_gui.py` (NEO + EX): 2 novos settings na seção Model Organization

---

## Backlog

### 🐛 Bugs Conhecidos
- [ ] **Update detection:** Lógica de `name_match` pode não marcar alguns outdated models (ver `civitai_api.py:472`)
- [ ] **NSFW check:** Sistema de `nsfwLevel` não é 100% preciso (depende da metadata inconsistente da CivitAI)

### 🔧 Technical Debt
- [ ] **Estado global:** Refatorar `gl.init()` para classe/contexto thread-safe (breaking change, planejar cuidadosamente)
- [ ] **Threading:** Adicionar locks explícitos em `download_queue` mutations
- [ ] **Error handling:** Padronizar tratamento de exceções (atualmente mix de try/except com prints)
- [ ] **Type hints:** Adicionar type annotations (código legacy sem tipos)

### ✨ Features Planejadas (Roadmap)

#### v0.8.0 — Advanced Curation *(próxima)*
- [ ] Saved search presets (salvar combinações de filtros)
- [ ] Favorites in creator/user search
- [ ] Additional browser QoL improvements

#### v1.0.0 — First Stable Release
- [ ] Resolver todos os bugs conhecidos
- [ ] Full Forge Neo compatibility guarantee
- [ ] Performance optimization (lazy loading de cards?)
- [ ] Automated tests (atualmente zero cobertura)

### 📝 Melhorias Futuras (Não Priorizadas)
- [ ] **Dashboard:** Gráficos interativos (Plotly/Chart.js?)
- [ ] **Search:** Autocomplete nos filtros
- [ ] **Download:** Torrent support como alternativa ao Aria2
- [ ] **Organization por Tag** *(design validado, 2026-03-06)*
  - **Fase 1:** Salvar `tags` e `user_tags` no `.json` sidecar durante `find_and_save` (requer segundo request a `/models/{id}`); tornar tags no painel editáveis para atribuição manual
  - **Fase 2:** Aba Manage: usuário escolhe tags "âncora" → modelos com aquela tag vão para `<tipo>/tag_nome/`; convive com organização por base model
  - Bloqueio: `/model-versions/by-hash` não retorna tags; precisa de request extra ao `modelId`
- [ ] **Organization:** Outras regras customizáveis (além de base model e tag)
- [ ] **API:** Rate limit handling mais sofisticado
- [ ] **UI:** Dark mode toggle (atualmente depende do WebUI theme)
- [ ] **I18n:** Suporte a idiomas (atualmente inglês/português misturados)

### 🧪 Investigações
- [ ] **Performance:** Profile `civitai_api.py` HTML generation (2k+ linhas, pode ser lento?)
- [ ] **Memory:** `gl.json_data` cresce indefinidamente? (leak potencial em sessões longas)
- [ ] **Aria2:** Testar limites de queue size (atualmente sem limite)

---

## Notas de Manutenção

### Ao Adicionar Features
1. Verificar se é compatível com Gradio 4+ (se não, marcar como Neo-only)
2. Se tocar filesystem: adicionar backup/rollback
3. Se tocar download: atualizar `download_log.py` states se necessário
4. Atualizar README.md (Changelog + Features)
5. Adicionar entrada neste PROJECT_LOG.md
6. Se mudar arquitetura/invariantes: atualizar AGENTS.local.md

### Ao Fazer Bugfix
1. Documentar root cause
2. Adicionar entrada datada neste log
3. Se crítico: mencionar no README Changelog
4. Considerar adicionar test case (quando/se framework de testes for implementado)

### Twin Project Sync (NEO ↔ EX)
- **Regra geral:** NEO é upstream, EX recebe features quando compatíveis
- **Projeto EX:** `C:\Users\Eduardo\OneDrive\Documentos\GitHub\sd-civitai-browser-ex`
  - Target: A1111, Forge Classic (Gradio 3.15+)
  - Versão atual: v0.2.0-ex (baseada no Neo v0.7.0)
  - Repo: https://github.com/eduardoabreu81/sd-civitai-browser-ex
- **Gradio 4+ features:** NÃO portar para EX
- **Forge Neo folder logic:** NÃO portar para EX (tem próprio fallback)
- **Bugfixes genéricos:** PORTAR para EX (API logic, file ops, etc.)
- **Comunicação:** Marcar PRs/commits com `[NEO-ONLY]` ou `[SYNC-TO-EX]`
- **Comunicação:** Marcar PRs/commits com `[NEO-ONLY]` ou `[SYNC-TO-EX]`

### Regras de Documentação

> **What's New (apenas a família da minor atual):** A seção "What's New" mantém as entradas da família da minor atual vX.Y.* inteira (ex: se estamos em v0.6.1, ficam v0.6.1 e v0.6.0 no What's New; se estamos em v0.4.0-ex, fica apenas v0.4.0-ex). Versões de famílias anteriores (ex: v0.5.x) pertencem exclusivamente ao Changelog.

---

**Última atualização:** 2026-05-09 (v0.9.0 major update consolidated)

---

### 2026-04-20 a 2026-05-09 — v0.9.0 Major Update: CivitAI Domain Support, Update Mode Isolation & Download Resilience

**O que mudou (pt-BR):** Major update consolidando múltiplas melhorias críticas desenvolvidas entre Abril e Maio de 2026. Como não houve release intermediário no CivitAI, toda a família de mudanças foi unificada em v0.9.0.

**1. CivitAI Domain Support**
- Suporte a domínios `civitai.com` (SFW) e `civitai.red` (completo).
- Setting `civitai_sfw_only` para restringir a `civitai.com`.
- Todas as URLs dinâmicas (API, links HTML, Referer) passaram a usar `get_civitai_domain()`.
- Parser de direct-link atualizado para aceitar ambos os domínios.
- Links smart em previews apontando para domínio correto.

**2. Update Mode Isolation & SHA256 Safety**
- Isolamento de estado do Update Mode — filtros do Browser não interferem mais quando Update Mode está ativo.
- `gl.update_mode` e `gl.update_items` inicializados em `gl.init()` para prevenir `AttributeError`.
- Detecção de SHA256 ambíguo — consulta ambos os domínios (`.com` e `.red`) quando a API retorna múltiplos modelos para um hash.
- Recheck de SHA256 em caso de mismatch — re-consulta a API via `version_id` para detectar silent-updates do autor.
- Busca por SHA256 defensiva: trata respostas em lista, campos ausentes, valida formato do hash.

**3. Exact Search Fix**
- Exact search restrito a "Model name" — CivitAI API não suporta quoted search para Tag ou User name.

**4. Batch Download Resilience**
- Loop interno (`while gl.download_queue:`) eliminando gaps entre itens na fila batch.
- Timeout 30s + retry automático (até 3×) para falhas de rede/timeout.
- Buffer SHA256 aumentado de 1MB para 8MB.
- Banner de restore inclui itens `failed` além de `queued`/`downloading`.

**5. Update List Sort & Re-trigger Fix**
- Lista de outdated ordenada por mtime (mais recente primeiro).
- Guarda contra re-trigger duplo no `queue_trigger`.

**6. Documentação Interna**
- Regras de sincronização Neo↔EX documentadas em `AGENTS.md` e `.github/copilot-instructions.md`.
- AGENTS.md protegido em todos os 7 repos (adicionado ao `.gitignore`).

**Arquivos alterados:** `scripts/civitai_api.py`, `scripts/civitai_download.py`, `scripts/civitai_file_manage.py`, `scripts/civitai_gui.py`, `scripts/civitai_global.py`, `scripts/download_log.py`, `javascript/civitai-html.js`, `README.md`, `.gitignore`

**Decisões:**
- Todas as mudanças da família 0.9.x foram unificadas em v0.9.0 pois não houve release pública intermediária.
- A regra de versionamento interno (bump Z para bugfix) foi usada durante o desenvolvimento, mas para fins de release pública consideramos tudo como v0.9.0.

**Pontos sensíveis:**
- Lógica de ambiguidade consulta ambos os domínios, dobrando requisições em casos raros.
- Silent-update detection depende do `version_id` estar presente no item da fila.
- Mudança de domínio em tempo real requer reload da UI para atualizar todos os links cached.

**Próximos passos / Next steps:**
- Responder e fechar issue #2 no GitHub (EX).
- Verificar se há outras issues abertas no EX para triagem.
- Planejar próxima feature para Neo (possivelmente melhorias no Dashboard ou Organizer).

### 2026-03-13 — API Request Resilience

**O que mudou (pt-BR):** Implementado *exponential backoff* (retentativas com espera progressiva) para erros de servidor do CivitAI (HTTP 500, 502, 503, 504) na função `request_civit_api`.
**Arquivos alterados:** `scripts/civitai_api.py`
**Decisões:** O update/scan não deve falhar no primeiro erro transitório; agora realiza até 3 tentativas com espera progressiva.
**Pontos sensíveis:** Em indisponibilidade prolongada da API, o fluxo ainda pode pular itens após o limite de tentativas.

### 2026-05-09 — Local Model Review (Phase B)

**O que mudou (pt-BR):** Implementado sistema de marcação local "Mark for review" para modelos instalados, permitindo ao usuário sinalizar modelos que precisam de revisão manual sem depender de API ou sidecar writes.

**Arquivos alterados:**
- `scripts/civitai_local_review.py` (novo) — Storage versionado (`config_states/local_review_status.json`), resolver de metadados local puro, interface `mark_file_for_review()`.
- `scripts/civitai_api.py` — `_resolve_local_model_meta()` lê `.json` sidecar e `.api_info.json` sem gerar SHA256 ou chamar API.
- `scripts/civitai_gui.py` — Botão "Mark for review" no Model Detail Panel, visível apenas quando o modelo está instalado localmente; feedback via `review_status_text`.

**Decisões:**
- Integração no **Model Detail Panel** escolhida por ser a superfície per-modelo nativa do app; Local Models é bulk-only e Browser Cards exigiriam JS+hidden-input complexo.
- Não foi modificado o tuple de 13 retornado por `update_model_info`; o estado do botão é controlado via `.then()` nos eventos `list_versions.select` e `model_select.change`.
- `mark_file_for_review` usa lazy import para evitar circularidade e valida existência do arquivo antes de persistir.
- Schema de storage é versionado (v1) com migração automática de formato flat legado.

**Pontos sensíveis:**
- Modelos sem sidecars `.json` ainda podem ser marcados, mas terão metadados mínimos (apenas `fileName`, `filePath`, `contentType` inferido).
- O botão aparece/desaparece dinamicamente com base em `os.path.isfile()`; não é confiável se o arquivo for movido entre a seleção do modelo e o clique no botão (protegido por re-validação no callback).

**Testes:** 34 testes unitários em `tests/test_civitai_local_review.py` — todos passando.

### 2026-03-17 — Checkpoint SHA256 Cache Sync

**O que mudou (pt-BR):** Adicionado sync de SHA256 de checkpoints para o cache oficial do WebUI em dois momentos: (1) automaticamente ao concluir download de checkpoint e (2) manualmente por botão na aba Update Models para reconciliar sidecars locais com o cache existente.
**Arquivos alterados:** `scripts/civitai_file_manage.py`, `scripts/civitai_download.py`, `scripts/civitai_gui.py`, `README.md`
**Decisões:** Sync usa SHA256 já presente no sidecar local (sem recálculo pesado no botão), adiciona apenas entradas faltantes no cache e mantém um registro local em `lib/models/checkpoint_hashes.json` para rastreamento e limpeza de órfãos.
**Pontos sensíveis:** Checkpoints sem `sha256` no sidecar são reportados como não sincronizados até receberem metadata válida; remoções manuais de arquivo são limpas na próxima execução do botão.



---

## Backlog / TODO

### Portabilidade para browser-ex
- [ ] **Validar mudanças recentes no EX** — Verificar se as alterações de 2026-05-08 (sort update list por mtime + fix re-trigger loop no download) fazem sentido na versão sd-civitai-browser-ex (Gradio 3 / A1111 / Forge Classic). Se aplicável, marcar commit com [SYNC-TO-EX].

---

## Linha do Tempo — Branch `revamp` (Beta-Revamp v0.1.0)

> Trabalho em desenvolvimento no branch `revamp` (divergiu de `main` em `a02e944`). UI marcada com o badge **Beta-Revamp v0.1.0** (`civitai_gui.py:322`). Tema central: aba **Local Models** self-contained, com a antiga aba **Update Models** fundida dentro dela. Ainda **não released** no CivitAI. Inclui novos módulos `civitai_html_builder.py` e `civitai_local_review.py` (ambos com testes) e docs de planejamento (`docs/REVAMP_AUDIT.md`, `docs/REVAMP_LAYOUT_PROPOSAL.md`, `docs/HTML_COMPONENT_ANALYSIS.md`, `docs/FUNCTION_MAP.md`).

### 2026-05-13 — HTML builder extraction + revamp layout planning

**O que mudou (pt-BR):** Extraídos os construtores de HTML de `update_model_info` para um módulo dedicado `civitai_html_builder.py`, com cobertura de testes. Adicionada remoção automática do card de modelo atualizado na aba Update Models e corrigida a ordem de binding dos `.then()` (deferido até `refresh_inputs`/`page_outputs` existirem). Criados docs internos de planejamento do revamp.
**Arquivos alterados:** `scripts/civitai_html_builder.py` (novo), `scripts/civitai_gui.py`, `scripts/civitai_api.py`, `tests/test_civitai_html_builder.py` (novo), `docs/REVAMP_LAYOUT_PROPOSAL.md` (novo), `docs/HTML_COMPONENT_ANALYSIS.md` (novo), `docs/FUNCTION_MAP.md`.
**Decisões:** Separar a geração de HTML da lógica de callback para viabilizar o novo layout de overlay sem inchar `update_model_info`.
**Pontos sensíveis:** HTMLs antigos exigem localizar o fechamento do description-block por contagem de profundidade (fallback chain).

### 2026-05-25 — Browser filter defaults em JSON local

**O que mudou (pt-BR):** Defaults dos filtros do Browser passaram a persistir em JSON local da extension (em vez de depender só do settings do Forge). Removido parâmetro morto `olf` do `settings_map`/`saveSettings`.
**Arquivos alterados:** `scripts/civitai_gui.py`, `javascript/civitai-html.js`.
**Decisões:** Persistência local evita perda de filtros entre reloads e desacopla do ciclo de settings do WebUI.
**Pontos sensíveis:** Inputs do `saveSettings` e parâmetros devem ficar alinhados para não reintroduzir args mortos.

### 2026-05-29 — Ocultar progress bars nativas do Gradio 4

**O que mudou (pt-BR):** Barras de progresso nativas do Gradio 4 ocultadas nos callbacks de download/update; reaplicação dos filtros hideInstalled/banned quando o DOM da lista é regenerado.
**Arquivos alterados:** `javascript/civitai-html.js`.
**Pontos sensíveis:** Depende de seletores do DOM gerado pelo Gradio 4.

### 2026-06-01 — Update mode: versões selecionáveis + retention via send2trash

**O que mudou (pt-BR):** No Update Mode o usuário pode escolher a versão alvo; resolução de versão passou a ser híbrida (family/baseModel). Política de retention ('replace' e 'move to _Trash') passou a usar `send2trash` em vez de `os.remove`.
**Arquivos alterados:** `scripts/civitai_download.py`, `scripts/civitai_file_manage.py`, `scripts/civitai_gui.py`.
**Decisões:** Alinhar retention com o invariante de filesystem safety (nunca delete direto).
**Pontos sensíveis:** Resolução híbrida pode escolher versão inesperada se family e baseModel divergirem.

### 2026-06-06 a 2026-06-07 — Aba Local Models self-contained (merge da aba Update Models)

**O que mudou (pt-BR):** A aba **Update Models** foi fundida dentro de **Local Models**, que virou um browser autossuficiente (rename / delete / update) com grid próprio e filtro de base model independente. Adicionados: multi-select update, spinner de loading, refresh do detail panel ao trocar de versão, trained tags + "Add to prompt" no detail panel (B3), marcação de card como instalado pós-download e remoção da versão antiga conforme retention. Removidos os handoffs "load to browser". Badge **Beta-Revamp v0.1.0** adicionado à UI.
**Arquivos alterados:** `scripts/civitai_gui.py`, `scripts/civitai_file_manage.py`, `javascript/civitai-html.js`, `style.css`.
**Decisões:** Consolidar a gestão de modelos locais num só lugar; Local Models deixa de depender do Browser para operar.
**Pontos sensíveis:** Restaurado o refresh pós-download do Browser e adicionada guarda contra worker null; houve reverts de tentativas de dedup do worker de progresso que quebravam a barra.

### 2026-06-08 — Reorg de Maintenance & Updates + filtro "only updates"

**O que mudou (pt-BR):** UI de Maintenance & Updates de-cluttered (controle único de content-type), accordion movido para acima do grid e depois para a aba **Organization**. Filtro "only updates" virou view puramente client-side; "Update to latest" passou a funcionar sem scan prévio e a mostrar progresso; adicionado modo replace/keep no update. Guarda contra `sidecar sha256: null` no version_match/sha lookup. Corrigido flash do "Add to prompt" ao clicar no card.
**Arquivos alterados:** `scripts/civitai_gui.py`, `scripts/civitai_file_manage.py`, `javascript/civitai-html.js`.
**Pontos sensíveis:** `sha256: null` em sidecars antigos precisa de guarda explícita para não poluir o match.

### 2026-06-10 — Resiliência de fetch do Local + isolamento Browser/Local

**O que mudou (pt-BR):** Corrigido HTTP 500 no load do Local browser. Fetch passou a ser híbrido: uma chamada batched-first com fallback per-id; query single-id `?ids=` (corrige 500 da civitai.red); tentativa em civitai.com primeiro com fallback para .red; chunked fetch + recovery via version-endpoint para coleções grandes. Estado das abas Browser e Local isolado, com barras de download independentes por aba, origem de download registrada por item de fila e botões Clear próprios. Corrigidos: guarda de update parcial de card, "scan poisoning" e full clear.
**Arquivos alterados:** `scripts/civitai_api.py`, `scripts/civitai_download.py`, `scripts/civitai_file_manage.py`, `scripts/civitai_gui.py`, `javascript/civitai-html.js`.
**Decisões:** Batched-first minimiza requisições (1 chamada) mas faz fallback per-id quando a API retorna 500; consultar civitai.com antes de .red reduz exposição a NSFW quando possível.
**Pontos sensíveis:** Fallback per-id multiplica requisições em coleções grandes; recovery via version-endpoint depende de `version_id` presente.

### 2026-06-12 — Botão "Download selected version" no detail panel do Local

**O que mudou (pt-BR):** Adicionado botão "Download selected version" no Model Detail Panel da aba Local, permitindo baixar a versão selecionada diretamente do painel.
**Arquivos alterados:** `scripts/civitai_gui.py`, `javascript/civitai-html.js`.
**Pontos sensíveis:** Depende de a versão escolhida no dropdown estar sincronizada com o estado do painel.

### 2026-06-16 — Fix de delete (3 caminhos) + invalidação de `gl.update_items` no fluxo Local

**O que mudou (pt-BR):** Corrigidas falhas intermitentes ao apagar modelos nos 3 caminhos (botão do card, seleção única no detail, multisseleção) via cadeia de fallback SHA256 → modelId → filename, respeitando `civitai_neo_delete_to_trash`; `delete_model` nunca mais retorna `None` (busca em todas as pastas). Auditoria de segregação Browser↔Local: único vazamento real era `gl.update_items` — agora `download_single_update` o ignora e `reset_update_items()` dispara no Load/search do Local. Front-end: `deleteInstalledModel` troca `setTimeout(100)` por duplo `requestAnimationFrame` (evita race do SHA256 vazio).
**Arquivos alterados:** `scripts/civitai_file_manage.py`, `scripts/civitai_gui.py`, `scripts/civitai_download.py`, `javascript/civitai-html.js`.
**Pontos sensíveis:** `reset_update_items()` deliberadamente NÃO roda dentro de `render_local_browser` (senão apagaria os itens recém-coletados por um scan). Validação: estática (`py_compile`/`node -c`); runtime pendente.

### 2026-06-17 — Detecção de status de versão robusta (baseModel+índice) + ordenação na aba Local

**O que mudou (pt-BR):** (1) Reescrito o `installstatus` do `get_model_card` (Browser) para usar o campo `baseModel` + ordem do array (índice 0 = mais novo) em vez de parsear o nome da versão — comparação semântica de nome só como desempate quando ambos têm número limpo. Corrige molduras erradas com nomes livres (ex.: "Rose Quartz"/"Pearl" → outdated correto; "Ani-il_v9.0"/"Last" última versão → verde). Cross-family (azul) refinado: só dispara quando outro baseModel tem versão **mais recente** que a instalada (ignora linhagens antigas). Unifica a lógica do Browser com a do `version_match` (aba Local). (2) Nova ordenação na aba Local Models: dropdown "Sort by:" (Name A-Z/Z-A, Recently/Oldest downloaded) com re-sort leve sem rescan (`resort_local_browser` sobre o cache `gl.local_json_data`, carimbando `_local_mtime`). (3) `model_list_html` ignora `gl.sortNewest` quando `target='local'` — fecha mais um vazamento cross-tab (toggle de data do Browser não afeta o Local).
**Arquivos alterados:** `scripts/civitai_api.py`, `scripts/civitai_file_manage.py`, `scripts/civitai_gui.py`.
**Pontos sensíveis:** Cross-family agora depende da ordem por data do array da API (índice 0 = mais recente globalmente). Ordenação por data usa mtime do arquivo no disco. Validação: estática (`py_compile`) + verificação isolada da lógica de molduras contra 3 modelos reais (3/3 PASS); validado na WebUI ✅ (sort + molduras + isolamento OK).

### 2026-06-17 — Safeguard: "Update to latest" preserva a família (baseModel)

**O que mudou (pt-BR):** O botão "Update to latest" do Local podia pular de família (ex.: baixar Pony quando a instalada é Illustrious) no fallback `versions_list[0]` (mais nova global), que dispara quando a versão instalada não é identificada (sidecar sem `sha256`). Fix **A** (`trigger_local_update`): em vez de `model_id||[]`, ancora no SHA256 do arquivo instalado → acha o `baseModel` dele → força a versão mais nova **do mesmo baseModel** (`model_id||[id]`), ignorando a auto-resolução. Fix **B** (`_resolve_versions_to_download`): detecção do instalado agora casa por `sha256` **ou** `modelVersionId` cacheado (alinha com `version_match`), tornando o fallback global-newest inalcançável nos fluxos de update.
**Arquivos alterados:** `scripts/civitai_gui.py`, `scripts/civitai_download.py`.
**Pontos sensíveis:** Fix B mantém o `versions_list[0]` para download fresco (correto). Validação: `py_compile` OK + verificação sintética da resolução de família (4/4 PASS); runtime na WebUI pendente.
**Pendência relacionada:** features de conta via MCP (favoritar/seguir/notificações) planejadas — ver memória `mcp-account-features-plan`.

### 2026-06-17 — Local detail-panel instantâneo + galeria no update do Local + badge de conta (MCP passos 1-2)

**O que mudou (pt-BR):** (1) **Clique de card na aba Local sem rede:** `update_model_info(..., prefer_cached_images=True)` usa as imagens já cacheadas em `gl.local_json_data` (o `/models` já traz `modelVersions[].images`); o `meta` por-imagem é deliberadamente pulado (só importa no card do botão CivitAI do txt2img). Antes ia na civitai.red + 3× backoff (~6s por clique). (2) **Galeria no update pela aba Local:** o fetch lazy de `preview_html` em `download_create_thread` passou a resolver contra o `item['model_json']` próprio (origin-independent) em vez do `gl.json_data` do Browser — sem isso, `preview_html` vinha vazio e `save_images` abortava em silêncio (só o `preview.png` saía). (3) **Features de conta via MCP (passos 1-2):** novo `scripts/civitai_mcp.py` — cliente JSON-RPC do `mcp.civitai.com` (stateless, JSON puro, UA obrigatório, `whoami` cacheado) + badge passivo "Connected as <user>" no topo do Dashboard, auto-conectado em background; switch `account_features_mcp` default ON (opt-out silencioso). Sem botão de teste (decisão do usuário: conexão automática quando há API key).
**Arquivos alterados:** `scripts/civitai_api.py`, `scripts/civitai_gui.py`, `scripts/civitai_download.py`, `scripts/civitai_mcp.py` (novo).
**Decisões:** Local detail = das imagens em memória (exato/instantâneo, sem meta); arquitetura MCP = cliente próprio (favoritar/seguir/notificações não existem na REST v1, só via MCP/tRPC).
**Pontos sensíveis:** Badge precisa de API key no pod para validar (whoami autenticado). Validação: `py_compile` OK; runtime na WebUI pendente.
**Commits:** `8747105`, `039342e`, `8ce5c77`.

### 2026-06-18 — Performance de scan (card Local + bulk download), filtro de base no bulk, e suíte "Send to txt2img"

**O que mudou (pt-BR):**
**Performance — fim dos tree-walks repetidos:**
- *Clique de card Local:* `update_model_versions` ganhou `installed_file_paths` — detecta a versão instalada lendo só os 1-3 arquivos conhecidos (carimbados como `_local_paths` por `render_local_browser`) em vez de `os.walk`+`json.load` na árvore inteira do tipo a cada clique. Fallback ao walk quando o item não tem o carimbo (exige re-rodar "Load local models").
- *Bulk download (Browser):* `selected_to_queue` monta um índice **uma vez** por batch (`build_installed_index()` → `{hashes, ver_ids, by_model_id}`); `_resolve_versions_to_download` e `find_installed_file_by_model_id` reusam — de **2×N walks** para **1**. Era a "etapa BEM demorada de validação/roteamento".

**Filtro de base respeitado no bulk download:** o `base_filter` da busca agora chega ao `selected_to_queue`; em download novo, `_pick_filtered_or_first` escolhe a versão mais nova **cujo baseModel está no filtro** (não a global mais nova) — corrige modelos vindo como Anima/Chroma quando o filtro era Illustrious/NoobAI.

**"Send to txt2img" (card do botão CivitAI):**
- *Defer do `#paste`* (dois `requestAnimationFrame`) — corrige o campo sendo limpo (race: `#paste` lia o prompt antes do Gradio comprometer o valor).
- *`sendToTxt2img`* monta o infotext a partir do **meta já renderizado no card** (linhas `data-key`) em vez de re-baixar a imagem e ler o PNG embutido — exato e instantâneo. Fallback ao embutido (`sendImgUrl`) só quando a imagem não tem meta no card.
- *Botão "Try reading params from image file"* no empty state (imagens) — torna o fallback embutido alcançável quando a API não traz meta.
- *Conversão SwarmUI→A1111:* `fetch_and_process_image` detecta JSON `sui_image_params` (embutido de imagens geradas no SwarmUI) e converte pra infotext A1111 (prompt/negative/steps/sampler/cfg/seed/size/model + LoRAs inline `<lora:nome:peso>`) — era o "texto gigantesco" que o `#paste` não conseguia parsear.

**Outros:** `BeautifulSoup(html)` em `convert_local_images` agora especifica `'html.parser'` (silencia `GuessedAtParserWarning`; comportamento consistente entre ambientes).
**Arquivos alterados:** `scripts/civitai_api.py`, `scripts/civitai_download.py`, `scripts/civitai_file_manage.py`, `scripts/civitai_gui.py`, `javascript/civitai-html.js`, `style.css`.
**Decisões:** Índice único por batch (corrige O(N²)→O(N)); filtro = "uma versão por modelo, a mais nova que casa"; "Send to txt2img" prioriza o meta do card (o que o usuário vê), embutido como fallback, e converte SwarmUI.
**Pontos sensíveis:** O ganho de velocidade do card Local exige re-rodar "Load local models" (itens precisam de `_local_paths`). Conversão SwarmUI passa o nome do sampler como está (pode não mapear 1:1 no WebUI). Validação: `py_compile`/`node -c` OK + testes isolados (filtro 4/4, match instalado 3/3, conversão SwarmUI com o JSON real do usuário); runtime na WebUI pendente.
**Commits:** `cb00367`, `47d0eea`, `4af4d21`, `c57089f`, `b066066`, `3c5511c`, `a282646`.
**Status:** `revamp` aproximando-se do **Release Candidate**. Pendente: MCP passo 3 (⭐ favorite / 🔔 follow no detail panel), depois passo 4 (feed de notificações no Dashboard) — ver memória `mcp-account-features-plan`.

### 2026-06-18 — Features de conta via MCP: favorite/notify no detail panel + feed de notificações (passos 3-4)

**O que mudou (pt-BR):**
**Passo 3 — toggles no detail panel do Browser:** botões **⭐ Favorite** (`set_model_favorite`, `setTo` explícito → seguro/idempotente) e **🔔 Notify new versions** (`toggle_notify_model`, toggle server-side) no painel de detalhe, gated por `account_features_mcp` + API key (`_account_ready`). Estado por toggle em `gr.State` (`fav_state`/`notify_state`); `seed_account_buttons` roda via `.then` no `model_select.change` (lê o `model_id` já atualizado) e mostra/esconde os botões conforme account ready.
**Seed do Favorite (resolve a limitação):** o MCP `get_model` **não** expõe `isFavorite`/`isNotified` (structuredContent só tem `id`/`name`/`air`). Mas o estado de favorito **existe** via REST `/models?favorites=true` — o mesmo endpoint do filtro "only liked" do Browser. Novo `get_favorited_model_ids()` (cacheado por sessão, paginado) + `set_favorited_cache()` (sync após toggle) em `civitai_api.py`; o detail panel abre já como **⭐ Favorited** quando o modelo está nos favoritos. **Notify continua sem seed** (não há endpoint de leitura de "modelos que sigo", nem REST nem MCP) — começa off e reflete após o 1º clique.
**Passo 4 — feed no Dashboard:** accordion colapsável **"🔔 Following — new versions"** + botão "Check notifications" → `_mcp.list_notifications(limit=50)`, renderizando o **texto humano** do MCP (robusto à estrutura do item). Gated por account ready.
**Arquivos alterados:** `scripts/civitai_gui.py`, `scripts/civitai_api.py`.
**Decisões:** Favorite com `setTo` explícito (sem risco) + seed via REST favorites; Notify como toggle honesto (sem seed possível); feed renderiza texto cru até validarmos o payload real.
**Pontos sensíveis:** Notify pode inverter no 1º clique se já seguido (sem seed). Filtro de categoria do feed e parsing em linhas clicáveis ficam pendentes até ver o retorno real de `list_notifications`. Validação: `py_compile` OK; **runtime na WebUI pendente** (todas as features de conta precisam da API key do usuário no pod). Probe do transporte MCP feito sem auth (stateless, JSON puro, 53 tools).
**Commits:** `a7e9b8d`, `c2f45be`, `efa5f78`.
**Próximos passos / Next steps:**
- Validar passos 1-4 na WebUI (badge, ⭐/🔔, feed) com a API key — **colar o texto do feed** pra filtrar categoria "nova versão" e formatar em linhas.
- MCP fase 2 (opcional): reviews 1-5★ no detail panel (`upsert_resource_review`).
- Fechar o **Release Candidate** do `revamp` após a validação runtime do lote 06-17/06-18.

### 2026-06-23 — Resolução exata de arquivo nos cards + feed "Following" acionável + Send-to-txt2img só-prompt

**O que mudou (pt-BR):**
**[Fix] Match exato de arquivo nos botões de card:** `model_from_sent` (botão CivitAI) e `send_to_browser` resolviam o arquivo com `file.startswith(model_name)` guardando o **último** match → modelos com prefixo comum (ex.: "Char" vs "Char - Outfit" vs "Char v2") abriam o arquivo errado. Agora preferem **match exato de stem** (`os.path.splitext(file)[0] == model_name`); prefixo só como fallback.
**[Feat/Fix] Feed "Following — new versions" (Dashboard/MCP):** accordion passou a abrir expandido; o `list_notifications` retorna texto minimal (`#id tipo data`, sem nome/link) e ruidoso, então o feed agora **filtra só `new-model-version`** e monta **linhas com link** a partir do structuredContent (`details.modelId`/`modelVersionId`/nome → link pro modelo+versão), com fallback pras linhas filtradas e um diagnóstico no terminal (`[Following feed] sample notification: …`).
**[Fix] "Send to txt2img" com card só-prompt:** `sendToTxt2img` só emitia a linha `Negative prompt:` quando havia negativo; um card só com prompt positivo virava uma linha solta que o `#paste` ignorava. Agora **sempre** emite `Negative prompt:` (vazia quando ausente), igual ao `metaToTxt2Img`.
**Arquivos alterados:** `scripts/civitai_file_manage.py`, `scripts/civitai_gui.py`, `javascript/civitai-html.js`.
**Pontos sensíveis:** O mapeamento das chaves do structuredContent do `list_notifications` ainda não foi confirmado em runtime (codado defensivo + diagnóstico); decisão pendente da ação do clique no feed (link CivitAI / abrir no Browser / download).
**Commits:** `38fcaa3`, `aadf560`, `fa1ea5d`, `eeb39c1`.
**Próximos passos / Next steps:**
- Validar o feed com a key e colar o `sample notification` do terminal pra finalizar o mapeamento + decidir a ação do clique.

### 2026-06-24 — Borda verde por modelVersionId + paginação da aba Local Models

**O que mudou (pt-BR):**
**[Fix] Card instalado sem borda verde:** na detecção de instalado do `get_model_card`, `collect_existing_files` só casava por `sha256` do sidecar ou nome de arquivo. Se o `.json` não tivesse `sha256` (ou o arquivo fosse renomeado), o `installstatus` ficava vazio (sem borda) mesmo o modelo estando instalado. Agora `collect_existing_files` também coleta o **`modelVersionId`** cacheado e o `get_model_card` casa as versões por ele (alinhado com `version_match`). Ex.: Animosity (model 2596298, versão 2916492, Illustrious V1.1 = idx 0) volta a ficar verde.
**[Feat] Paginação da aba Local Models:** o grid renderizava **todos** os cards de uma vez, sobrecarregando o DOM em bibliotecas grandes. Agora `_render_local_slice` **fatia em memória** a lista já ordenada de `gl.local_json_data` e renderiza só uma página (padrão 50), com dropdown **"Per page" (25/50/100)** ao lado do Sort e uma **barra Prev/"Page X/Y"/Next** embutida no HTML do grid (`localGoToPage` → `#local_page_trigger` → `render_local_page`). A ordenação é aplicada na lista **inteira antes** de fatiar, então a ordem se mantém entre páginas; Load/Sort/Per-page voltam pra página 1.
**Arquivos alterados:** `scripts/civitai_api.py`, `scripts/civitai_file_manage.py`, `scripts/civitai_gui.py`, `javascript/civitai-html.js`, `style.css`.
**Decisões:** Paginação por **slice server-side** (não client-side) porque o gargalo real é o DOM com milhares de cards; barra embutida no HTML do grid pra não tocar os 7 call sites de `render_local_browser`.
**Pontos sensíveis:** Cada troca de página re-roda `collect_existing_files` (1 `os.walk` por render) pra detecção de borda — cachear se ficar lento em bibliotecas enormes. `render_local_page` recebe `page.<rand>` (sufixo aleatório força o change event) → pega o inteiro antes do ponto.
**Commits:** `93bbb51`, `3082dc6`.
**Próximos passos / Next steps:**
- Validar runtime: paginação (Per page/Prev/Next/sort entre páginas) e borda verde do Animosity.
- Considerar cache do `collect_existing_files` se a troca de página ficar lenta.
- Fechar o **Release Candidate** do `revamp` após validar o acumulado 06-17→06-24.

### 2026-07-11 — Fase E: Browser source adapter para ModelScope

**O que mudou (pt-BR):**
**[Feat] Adapter ModelScope no multi-browser:** novo source `ModelScope` registrado no dropdown do Browser, permitindo buscar modelos diretamente em `www.modelscope.cn`.
**API utilizada:** busca por `PUT /api/v1/dolphin/models` com payload JSON (`Name`, `PageSize`, `PageNumber`); detalhe por `GET /api/v1/models/{owner}/{repo}`; downloads via endpoint HF-compatible `https://www.modelscope.cn/models/{owner}/{repo}/resolve/master/{path}`.
**Normalização:** modelos são convertidos para o formato canônico da extensão. Content type e base model são inferidos de `MuseInfo.model.modelType`/`stableDiffusionVersion` quando disponível; caso contrário usa heurística por tags, libraries e nome do repo (mesma família de hints do HF). Arquivos reais vêm de `MuseInfo.versions[].stats.fileList` na busca ou de `ModelInfos.safetensor.files` no detalhe, com fallback para card renderizável quando ainda não há file list.
**URL paste:** URLs de modelos do ModelScope (`modelscope.cn/models/{owner}/{repo}`) são parseadas e redirecionadas para o novo adapter, populando o model panel para download.
**Arquivos alterados:** `scripts/browser_sources/modelscope.py` (novo), `scripts/browser_sources/__init__.py`, `scripts/browser_sources/url_parser.py`, `tests/test_browser_sources.py`.
**Decisões:** ModelScope aparece no dropdown (ao contrário do HF, que ficou URL-only). GGUF e catálogo curado Hugging Face foram postergados por complexidade; a entrega imediata é navegação/download direto no ModelScope.
**Pontos sensíveis:** `MuseInfo` só está presente para modelos de geração de imagem cadastrados no Muse; repos sem MuseInfo retornam arquivo sintético no search, mas o detalhe (`get_model`) carrega a file list real. Tamanhos de `MuseInfo.stats.fileSizes` usam heurística bytes/KB; `ModelInfos.safetensor.files[].size` é tratado como bytes.
**Testes:** `pytest tests/test_browser_sources.py` passando (58/58), incluindo busca Muse, detalhe com ModelInfos, filtros de content type/base model, build de download URL e parsing de URL.
**Próximos passos / Next steps:**
- Validar runtime no Forge Neo: dropdown ModelScope, busca, paginação, clique em card e download de arquivo.
- Após validação, atualizar README.md (What's New) e fechar/release da branch `revamp`.

---

## Backlog / Próxima Sessão

### 2026-07-08 — Proposta: Dynamic Base Model Filtering no Extra Networks

**Inspiração:** recurso do `SiliconeShojo/models-info` — dropdown de filtro por arquitetura injetado diretamente no header toolbar do Extra Networks do WebUI, filtrando os cards nativos sem reload e agrupando não reconhecidos em **Unknown**.

**Objetivo no Browser Neo:** oferecer o mesmo filtro dinâmico para os cards do **Extra Networks nativo do Forge Neo**, permitindo ao usuário ver apenas modelos de uma arquitetura (SD 1.5, SDXL, Flux, Pony, SD 3.5, Wan, etc.) e limpar a biblioteca via categoria Unknown.

**Desafios técnicos identificados:**
1. O Browser Neo hoje só injeta um botão nos cards nativos (`javascript/civitai-html.js:596-643`); não controla o toolbar/header do Extra Networks.
2. Os cards nativos do Forge Neo **não expõem base model** no DOM (nenhum `data-base-model` ou atributo equivalente).
3. É preciso mapear cada card nativo para o base model correspondente. As fontes possíveis são:
   - **Sidecars `.json`/`.api_info.json` já salvos pelo Browser Neo** (mais confiável, mas só cobre modelos que passaram pelo extension).
   - **Metadados que o Forge Neo já carrega internamente** (se houver API/DOM acessível — a investigar).
   - **Re-escanear os arquivos no disco** para construir um índice `nome/stem → base_model` (lento em coleções grandes; precisa de cache).
4. Lazy loading/paginação do Extra Networks exige re-aplicação contínua do filtro (MutationObserver ou hooks nos eventos de refresh/aba).
5. Seletores do DOM podem variar entre versões do Forge Neo; precisaremos de fallback defensivo.

**Caminhos possíveis (a decidir na próxima sessão):**
- **Opção A — Documentar/planejar:** escrever especificação completa, seletores, funções e sequência de implementação sem codar ainda.
- **Opção B — MVP com sidecars:** dropdown injetado no toolbar; filtro baseado apenas nos modelos que já têm sidecar `.json`/`.api_info.json` salvo pelo Browser Neo; Unknown para o resto.
- **Opção C — Investigar DOM primeiro:** abrir o Forge Neo (local ou via Playwright) para confirmar seletores exatos do toolbar e dos cards nativos antes de planejar.

**Arquivos prováveis de envolvimento:** `javascript/civitai-html.js`, `scripts/civitai_file_manage.py` (índice/lookup), `style.css`, possivelmente `scripts/civitai_api.py`.
**Status:** proposta registrada; aguardando decisão do usuário para iniciar.

---

## Resumo para README (próximo release)

### What's New — Revamp v0.1.0

- **LoraDex — curadoria visual de LoRAs**  
  Nova sub-aba dentro de *Local Models* para revisar e ajustar a categoria de cada LoRA instalada. Lista compacta com mini-thumbnail (zoom no hover), nome do modelo CivitAI, base model, versão instalada e dropdown de categoria. Alterações pendentes são destacadas em amarelo e podem ser aplicadas individualmente ou em lote.

- **Auto-sugestão de categoria de LoRA**  
  O LoraDex sugere automaticamente uma categoria (`Character`, `Style`, `Clothing`, `Concept`, `Pose`, `Background`, `Utility`) com base nas tags do modelo; se as tags não forem suficientes, usa a descrição como fallback. Sugestões aparecem pré-selecionadas no dropdown e são sinalizadas com borda azul + badge 🤖. Categorias manuais salvas pelo usuário têm sempre prioridade.

- **Subpastas de LoRA por categoria**  
  Quando `civitai_neo_lora_category_sort` está ativa junto com `civitai_neo_auto_organize`, LoRAs são organizadas em `Lora/<base>/<categoria>/` tanto no download quanto em organização em lote.

- **Preview em JPEG**  
  Nova opção para salvar previews e imagens da galeria em JPEG com qualidade configurável, reduzindo espaço em disco.

- **Retry Aria2 em HTTP 429**  
  Downloads que levam rate limit da CivitAI são automaticamente re-tentados com backoff e link fresco.

- **Melhorias no Local Models**  
  Paginação, detecção de versão instalada por `modelVersionId`, isolamento Browser↔Local e filtros de base model respeitados em updates em lote.

- **Estabilidade**  
  Fix de crash em `download_finish` com fila vazia, resolução exata de arquivo por stem e fallback de `modelTags` no sidecar para organização/LoraDex/download.
