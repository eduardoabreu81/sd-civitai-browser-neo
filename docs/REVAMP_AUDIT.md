# Revamp — Auditoria de UX/UI e Roadmap

> Branch: `revamp` · Objetivo: reformular o app pra ficar coeso e funcional antes de promover pro `main`.
> Data: 2026-06-07

## Mapa atual

**Abas (5):** Browser · Update Models · Download Queue · Local Models · Dashboard
**Settings:** 45 opções, em 3 seções (Browser / Downloads / Model Organization), em lista praticamente plana.

Render de cards é **um só** mecanismo (`model_list_html` → `civmodelcard`) reusado por Browser, Local Models e Update Mode. Isso é uma força (consistência técnica) que a UI ainda não aproveita totalmente.

---

## Achados (por tema)

### A. Arquitetura de informação (o maior ponto)
- **A1. Sobreposição conceitual entre abas.** Browser (remoto), Local Models (local) e Update Models (desatualizados) tratavam todos de "modelos". — **✅ DECIDIDO:** dois papéis claros → **Browser = descobrir/baixar novidades do CivitAI**; **Local Models = gerenciar o que já tenho** (ajustes, updates, organização). A aba **Update Models foi absorvida pelo Local Models** (2026-06-07).
- **A2. Handoff "Load to browser" é truncado.** — *Aberto.* "Load outdated/installed to browser" ainda joga pro Browser; com o grid local já existente, no futuro pode carregar no próprio grid do Local.
- **A3. "Update Models" tem escopo confuso.** — **✅ RESOLVIDO** pela decisão A1: as features de update/manutenção agora vivem no accordion "Maintenance & Updates" do Local Models.

### B. Consistência
- **B1. Update Models ainda é painel de botões**, agora destoando do Local Models (que virou browser). — *Médio.*
- **B2. Controles de "content types" triplicados:** `content_type` (Browser), `selected_tags`/`selected_tags_local` (Update/Local) e agora `local_content_type`. Mesma ideia, 4 controles. — *Médio.*
- **B3. Onde vivem as ações é inconsistente:** delete no ícone do card (hover), rename só no painel do Local, update via Update Mode/painel. Sem um padrão único "card → ações". — *Médio.*

### C. Settings
- **C1. 45 opções em lista plana.** — **❌ NÃO REORGANIZAR** (decisão do usuário): o app é extenso e agrupar pode dificultar a organização para quem usa. Manter a lista plana.

### D. Feedback visual
- **D1. Progresso como blocos de HTML cru** espalhados (cada operação tem seu `*_progress`). Sem padrão visual de loading/sucesso/erro. — *Médio.*
- **D2. Legenda/badges** (instalado, desatualizado, cross-family, early access) são bons, mas a descoberta depende de uma legenda textual. — *Baixo.*

### E. Fragilidade técnica que afeta UX
- **E1. `adjustFilterBoxAndButtons`** faz cálculo manual de breakpoints e move nós no DOM — frágil (foi fonte do null risk em `pageBoxMobile`). Responsividade via CSS seria mais robusta. — *Médio.*
- **E2. Lacunas v1 do Local Models:** paginação, troca de versão no painel, mover-pra-subpasta por card. — *Médio.*
- **E3. Rename/Delete localizam por sidecar `.json`** — modelos local-only sem `.json` não são encontrados. — *Baixo/médio.*

---

## Direção definida (2026-06-07)
- **Browser** = descobrir/baixar novos modelos do CivitAI.
- **Local Models** = hub de gerenciamento do que já está instalado (ajustes, updates, organização). **Absorveu a aba Update Models.**
- **Settings** = mantidos planos (sem agrupar).
- **Queue / Dashboard** = avaliar como agregar/melhorar depois.
- **Regra de ouro:** não quebrar lógica existente — mudanças preservam nomes de componentes e bindings.

## Roadmap priorizado

### Fase 0 — Estabilizar (pré-requisito)
- Validar em runtime o Local Models browser (você) e corrigir bugs que aparecerem.

### Fase 1 — Consolidação de abas
1. **✅ FEITO** Merge da aba Update Models dentro do Local Models (accordion "Maintenance & Updates"), preservando lógica.
2. **✅ FEITO (A2)** Removidos os botões "Load installed/outdated to browser". Browser mantém a detecção de instalados; o controle de atualização vive no Local. Scans (updates/installed/organize) agora **refrescam o grid do Local**; multi-seleção via checkbox dos cards desatualizados + botão "Update selected" (reusa `update_selected_models`); update por modelo no painel.
3. **B3 (em andamento)** Padrão único card → painel de detalhe.
   - ✅ Local ganhou "Trained tags" + "➕ Add to prompt" (espelha o Browser; reusa `sendTagsToPrompt`).
   - ⏳ Falta (precisa de validação visual): alinhar layout/estilo dos botões de ação e a confirmação de delete entre Browser e Local. Browser **não é alterado** sem necessidade — alinhamos o Local ao padrão dele.

### Fase 2 — Coesão do Local Models
4. **E2** Fechar lacunas: ✅ troca de versão no painel (dropdown Version recarrega) · ✅ indicador de loading (spinner sobre o grid em load/rename/delete) · ⏳ paginação no grid · ⏳ mover-pra-subpasta por card.
5. **B2** Avaliar unificar os controles de "content types"/scan options duplicados (Update vs Organização) — **com cuidado pra não quebrar `file_scan_inputs`**.
6. **D1** Padronizar o componente de progresso (loading/ok/erro).

### Fase 3 — Polish
7. **E1** Responsividade via CSS (aposentar cálculo manual de breakpoints).
8. **D2** Refinos visuais (badges, legenda, hover states).

> Settings (C1) e a ideia de "aba Models única" foram descartados a pedido do usuário — a divisão Browser/Local é a escolhida.

---

## Recomendação de início
Validar o Local Models (agora com as features do Update embutidas) e seguir pela **Fase 1** — padronizar as ações por modelo e trazer os "load to browser" pro grid local, fechando o conceito de hub de gerenciamento.
