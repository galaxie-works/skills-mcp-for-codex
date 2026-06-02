param(
  [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

$skillsIndexPath = Join-Path $Root "docs\installed-skills.md"
$sourceMapPath = Join-Path $Root "docs\skill-source-map.json"
$manifestPath = Join-Path $Root "manifest.json"
$schemaPath = Join-Path $Root "manifest.schema.json"
$categoriesDocPath = Join-Path $Root "docs\skill-categories.md"
$guidePath = Join-Path $Root "docs\installer-manifest-guide.md"

if (-not (Test-Path -LiteralPath $skillsIndexPath)) {
  throw "Missing docs\installed-skills.md. Refresh the installed skills inventory first."
}

$generatedAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")

$categoryDefinitions = [ordered]@{
  "frontend-ui" = [ordered]@{
    name = "Frontend, UI e Design System"
    description = "Skills para criar interfaces, componentes, layouts, Tailwind, React, shadcn, animações e experiências visuais bonitas."
    color = "#ec4899"
    tags = @("frontend", "ui", "design-system", "tailwind", "react", "shadcn")
  }
  "wordpress-web" = [ordered]@{
    name = "WordPress, Sites e CMS"
    description = "Skills para WordPress, Elementor, GenerateBlocks, auditoria de sites, páginas institucionais e publicação web."
    color = "#2563eb"
    tags = @("wordpress", "elementor", "cms", "website", "site")
  }
  "marketing-growth" = [ordered]@{
    name = "Marketing, Growth e SEO"
    description = "Skills para SEO, conteúdo, anúncios, analytics, social media, funis, posicionamento e crescimento comercial."
    color = "#f97316"
    tags = @("marketing", "seo", "ads", "growth", "analytics", "social")
  }
  "product-ops" = [ordered]@{
    name = "Produto, Operação e PO"
    description = "Skills para priorização, backlog, PRD, discovery, gestão de produto, rotinas executivas e automação do dia a dia."
    color = "#14b8a6"
    tags = @("produto", "po", "backlog", "prd", "ops", "startup")
  }
  "automation-agents" = [ordered]@{
    name = "Automação, Agentes e MCP"
    description = "Skills para browser automation, agentes, MCPs, workflows, integrações e execução assistida por ferramentas."
    color = "#8b5cf6"
    tags = @("automation", "agents", "mcp", "browser", "workflow")
  }
  "backend-architecture" = [ordered]@{
    name = "Backend, APIs e Arquitetura"
    description = "Skills para APIs, Laravel, bancos, autenticação, arquitetura, padrões backend e integrações complexas."
    color = "#0ea5e9"
    tags = @("backend", "api", "architecture", "database", "laravel")
  }
  "devops-cloud" = [ordered]@{
    name = "DevOps, Cloud e Deploy"
    description = "Skills para Vercel, Azure, CI/CD, GitHub Actions, deploy, infraestrutura, ambientes e observabilidade."
    color = "#22c55e"
    tags = @("devops", "cloud", "deploy", "vercel", "ci-cd", "github")
  }
  "quality-security" = [ordered]@{
    name = "Qualidade, Testes e Segurança"
    description = "Skills para QA, auditoria, acessibilidade, testes, lint, revisão, segurança e hardening."
    color = "#ef4444"
    tags = @("qa", "testing", "security", "audit", "accessibility")
  }
  "content-media" = [ordered]@{
    name = "Conteúdo, Áudio, Vídeo e Mídia"
    description = "Skills para escrita, documentação, storytelling, áudio, vídeo, imagens, apresentações e conteúdo multimídia."
    color = "#f59e0b"
    tags = @("content", "writing", "audio", "video", "media", "slides")
  }
  "data-ai" = [ordered]@{
    name = "Dados, IA e Pesquisa"
    description = "Skills para dados, IA, modelos, pesquisa, análise, ciência, bancos vetoriais e experimentação."
    color = "#6366f1"
    tags = @("data", "ai", "research", "ml", "analysis")
  }
  "business-strategy" = [ordered]@{
    name = "Negócios, Finanças e Estratégia"
    description = "Skills para estratégia, CFO/CMO/COO, pricing, vendas, customer research, planejamento e tomada de decisão."
    color = "#64748b"
    tags = @("business", "strategy", "finance", "sales", "pricing")
  }
  "system-runtime" = [ordered]@{
    name = "Sistema, Runtime e Utilitários"
    description = "Skills internos, utilitários técnicos e capacidades de suporte que mantêm o ambiente Codex funcionando."
    color = "#475569"
    tags = @("system", "runtime", "utility", "codex")
  }
}

function Convert-ToSlug {
  param([string]$Value)
  $slug = $Value.ToLowerInvariant()
  $slug = $slug -replace "[^a-z0-9]+", "-"
  $slug = $slug.Trim("-")
  if ([string]::IsNullOrWhiteSpace($slug)) { return "skill" }
  return $slug
}

function Get-DisplayName {
  param([string]$Skill)
  $clean = $Skill -replace "--.*$", ""
  $parts = ($clean -replace "[-_]+", " ").Trim().Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries)
  ($parts | ForEach-Object {
    if ($_.Length -le 3 -and $_ -eq $_.ToUpperInvariant()) { $_ }
    elseif ($_.Length -le 2) { $_.ToUpperInvariant() }
    else { $_.Substring(0,1).ToUpperInvariant() + $_.Substring(1) }
  }) -join " "
}

function Get-Tags {
  param(
    [string]$Skill,
    [string]$Description,
    [string]$Why
  )

  $text = "$Skill $Description $Why".ToLowerInvariant()
  $tags = New-Object System.Collections.Generic.List[string]

  $rules = [ordered]@{
    "react" = "\breact\b|\bjsx\b|\btsx\b"
    "tailwind" = "\btailwind\b|\bcss\b"
    "wordpress" = "\bwordpress\b|\belementor\b|\bgenerateblocks\b|\bcms\b"
    "seo" = "\bseo\b|\bsearch\b|\bschema\b|\bbacklink\b|\bkeyword\b|\bserp\b|\bgeo\b|\bllmo\b"
    "marketing" = "\bmarketing\b|\bads\b|\bcampaign\b|\bcopy\b|\bgrowth\b|\bfunnel\b|\bsocial\b|\blinkedin\b|\binstagram\b|\btiktok\b"
    "analytics" = "\banalytics\b|\btracking\b|\bga4\b|\bgoogle analytics\b|\bgsc\b|\bmetrics\b"
    "product" = "\bproduct\b|\bprd\b|\bbacklog\b|\broadmap\b|\bpriorit"
    "automation" = "\bautomation\b|\bbrowser\b|\bagent\b|\bworkflow\b|\bmcp\b|\bscrap|\bcrawl"
    "backend" = "\bbackend\b|\bapi\b|\bdatabase\b|\bmysql\b|\bsqlite\b|\bprisma\b|\blaravel\b|\bauth\b"
    "devops" = "\bdeploy\b|\bvercel\b|\bazure\b|\bcloud\b|\bci\b|\bcd\b|\bgithub actions\b|\bdocker\b"
    "security" = "\bsecurity\b|\bpentest\b|\bvulnerab|\bxss\b|\bsql injection\b|\bauthenticat"
    "testing" = "\btest\b|\bqa\b|\bjest\b|\bvitest\b|\blint\b|\baudit\b"
    "content" = "\bcontent\b|\bwriting\b|\barticle\b|\bdocumentation\b|\bblog\b|\bcopywriting\b"
    "media" = "\baudio\b|\bvideo\b|\bimage\b|\bslide\b|\bpresentation\b|\bfigma\b|\bdesign\b"
    "ai" = "\bai\b|\bllm\b|\bmodel\b|\bagent\b|\brag\b|\bopenai\b|\bgemini\b|\bclaude\b"
    "business" = "\bfinance\b|\bcfo\b|\bcmo\b|\bcoo\b|\bsales\b|\bpricing\b|\bstrategy\b|\bcustomer\b"
  }

  foreach ($key in $rules.Keys) {
    if ($text -match $rules[$key]) { $tags.Add($key) }
  }

  if ($tags.Count -eq 0) { $tags.Add("general") }
  return @($tags | Select-Object -Unique)
}

function Get-CategoryId {
  param(
    [string]$Skill,
    [string]$Description,
    [string]$Why,
    [string[]]$Tags
  )

  $text = "$Skill $Description".ToLowerInvariant()

  if ($Skill -like ".system/*" -or $Why -match "System/runtime") { return "system-runtime" }
  if ($text -match "__security__|__development__cc-skill-coding-standards|code review|coding standards|best practices|quality|checklist") { return "quality-security" }
  if ($text -match "__ai-research__|__scientific__|\bmachine learning\b|\bdeep learning\b|\btraining\b|\bfine-tuning\b|\bbenchmark\b") { return "data-ai" }
  if ($text -match "__document-processing__|__creative-design__.*(image|video|audio|slide|presentation|deck|writing|article|content|media)") { return "content-media" }
  if ($text -match "__creative-design__|design system|\bui\b|\bux\b|\blayout\b|\bcomponent\b|\bfigma\b|\btailwind\b|\breact\b|\bcss\b|\bshadcn\b") { return "frontend-ui" }
  if ($text -match "__business-marketing__.*(pricing|strategy|sales|finance|cfo|cmo|coo|customer)") { return "business-strategy" }
  if ($text -match "__business-marketing__.*(product|owner|prd|backlog|roadmap|startup)") { return "product-ops" }
  if ($text -match "__business-marketing__") { return "marketing-growth" }
  if ($text -match "__enterprise-communication__") { return "product-ops" }
  if ($text -match "__pocketbase__") { return "backend-architecture" }
  if ($text -match "\bsecurity\b|\bpentest\b|\bvulnerab|\bxss\b|\bsql injection\b|\btest\b|\bqa\b|\bjest\b|\bvitest\b|\blint\b|\baudit\b|\baccessibility\b|\bhardening\b") { return "quality-security" }
  if ($text -match "\bwordpress\b|\belementor\b|\bgenerateblocks\b|\bcms\b|website audit|audit websites") { return "wordpress-web" }
  if ($text -match "\bseo\b|\bmarketing\b|\bads\b|\bcampaign\b|\bgrowth\b|\banalytics\b|\bsocial\b|\blinkedin\b|\binstagram\b|\btiktok\b|\bcopywriting\b|\bemail sequence\b|\bconversion\b|\bfunnel\b|\bbacklink\b|\bschema\b") { return "marketing-growth" }
  if ($text -match "\baudio\b|\bvideo\b|\bimage\b|\bslide\b|\bpresentation\b|\bwriting\b|\barticle\b|\bdocumentation\b|\bblog\b|\bstory\b|\bmedia\b|\bcontent\b") { return "content-media" }
  if ($text -match "\breact\b|\btailwind\b|\bshadcn\b|\bfrontend\b|\bui\b|design system|\bcomponent\b|\banimation\b|\bfigma\b|\blayout\b|\bcss\b|view transition") { return "frontend-ui" }
  if ($text -match "\bproduct\b|\bprd\b|\bbacklog\b|\broadmap\b|\bpriorit|\bsprint\b|\bstakeholder\b|project manager|\boperation\b|\bstartup\b") { return "product-ops" }
  if ($text -match "browser automation|\bagent\b|\bmcp\b|\bworkflow\b|\bscrap|\bcrawl\b|\bteams\b|\bslack\b|\bautomation\b") { return "automation-agents" }
  if ($text -match "\bdeploy\b|\bvercel\b|\bazure\b|\bcloud\b|\bci\b|\bcd\b|github actions|\bdocker\b|\binfrastructure\b|\bobservability\b|\blogs\b") { return "devops-cloud" }
  if ($text -match "\bbackend\b|\bapi\b|\barchitecture\b|\bdatabase\b|\bmysql\b|\bsqlite\b|\bprisma\b|\blaravel\b|\bauth\b|\bserver\b|\bintegration\b") { return "backend-architecture" }
  if ($text -match "\bdata\b|\bai\b|\bllm\b|\bmodel\b|\bresearch\b|\bscience\b|\banalysis\b|\bml\b|\brag\b|\bvector\b|\bopenai\b|\bgemini\b|\bclaude\b") { return "data-ai" }
  if ($text -match "\bfinance\b|\bcfo\b|\bcmo\b|\bcoo\b|\bsales\b|\bpricing\b|\bstrategy\b|\bcustomer\b|\bbusiness\b") { return "business-strategy" }
  return "system-runtime"
}

function Get-PtDescription {
  param(
    [string]$Name,
    [string]$CategoryId,
    [string[]]$Tags
  )

  $tagText = ($Tags | Select-Object -First 4) -join ", "
  switch ($CategoryId) {
    "frontend-ui" { return "Ajuda a criar, revisar ou melhorar interfaces com foco em experiência visual, componentes, responsividade e consistência. Útil quando o trabalho envolve $Name, UI, design system ou padrões frontend. Tags: $tagText." }
    "wordpress-web" { return "Ajuda a trabalhar com sites, WordPress, CMS, Elementor ou publicação web. Útil para estruturar páginas, revisar implementações e orientar manutenção relacionada a $Name. Tags: $tagText." }
    "marketing-growth" { return "Ajuda em marketing, SEO, conteúdo, anúncios, mensuração ou crescimento. Útil para planejar, produzir, auditar ou otimizar iniciativas relacionadas a $Name. Tags: $tagText." }
    "product-ops" { return "Ajuda em produto, operação, backlog, priorização, planejamento e rotinas de PO. Útil para transformar demandas relacionadas a $Name em decisões, planos e entregáveis mais claros. Tags: $tagText." }
    "automation-agents" { return "Ajuda a automatizar tarefas, coordenar agentes, operar browser/MCP ou criar fluxos assistidos. Útil quando $Name precisa reduzir trabalho manual ou conectar ferramentas. Tags: $tagText." }
    "backend-architecture" { return "Ajuda em backend, APIs, arquitetura, bancos, autenticação ou integrações. Útil para projetar, implementar e revisar soluções técnicas relacionadas a $Name. Tags: $tagText." }
    "devops-cloud" { return "Ajuda em deploy, cloud, CI/CD, ambientes, GitHub, Vercel, Azure ou operação técnica. Útil para instalar, configurar, publicar ou diagnosticar fluxos relacionados a $Name. Tags: $tagText." }
    "quality-security" { return "Ajuda a revisar qualidade, testes, acessibilidade, segurança, lint, auditoria ou riscos técnicos. Útil para encontrar problemas e orientar correções relacionadas a $Name. Tags: $tagText." }
    "content-media" { return "Ajuda a produzir, revisar ou estruturar conteúdo, documentação, áudio, vídeo, imagens, apresentações ou storytelling. Útil para materiais relacionados a $Name. Tags: $tagText." }
    "data-ai" { return "Ajuda em dados, IA, análise, pesquisa, modelos, automações inteligentes ou experimentação. Útil para explorar, construir ou validar trabalhos relacionados a $Name. Tags: $tagText." }
    "business-strategy" { return "Ajuda em estratégia, vendas, finanças, pricing, pesquisa de clientes ou tomada de decisão. Útil para orientar escolhas de negócio relacionadas a $Name. Tags: $tagText." }
    default { return "Ajuda como capacidade de sistema, runtime ou utilitário técnico do Codex. Útil para suporte operacional relacionado a $Name. Tags: $tagText." }
  }
}

function Parse-SkillsIndex {
  $rows = New-Object System.Collections.Generic.List[object]
  $lines = Get-Content -LiteralPath $skillsIndexPath

  foreach ($line in $lines) {
    if ($line -notmatch '^\| `([^`]+)` \| `([^`]+)` \| (.*) \| (.*) \|$') { continue }
    $skill = $Matches[1]
    $path = $Matches[2]
    $why = $Matches[3].Trim()
    $description = $Matches[4].Trim()

    $rows.Add([pscustomobject]@{
      skill = $skill
      path = $path
      why = $why
      description = $description
    })
  }

  return $rows.ToArray()
}

$sourceMap = @{}
if (Test-Path -LiteralPath $sourceMapPath) {
  foreach ($entry in (Get-Content -LiteralPath $sourceMapPath -Raw | ConvertFrom-Json)) {
    if ($entry.skill_name -and $entry.url -and -not $sourceMap.ContainsKey($entry.skill_name)) {
      $sourceMap[$entry.skill_name] = $entry.url
    }
  }
}

$rows = Parse-SkillsIndex
$skillsByCategory = @{}
foreach ($categoryId in $categoryDefinitions.Keys) {
  $skillsByCategory[$categoryId] = New-Object System.Collections.Generic.List[object]
}

foreach ($row in $rows) {
  $skillId = ($row.path -replace "^skills[\\/]", "") -replace "\\", "/"
  $isSystem = $skillId.StartsWith(".system/")
  $installPath = $row.path -replace "\\", "/"
  $diskPath = Join-Path $Root ($row.path -replace "/", "\")
  $hasSkillFile = Test-Path -LiteralPath (Join-Path $diskPath "SKILL.md")
  $tags = Get-Tags -Skill $row.skill -Description $row.description -Why $row.why
  $categoryId = Get-CategoryId -Skill $skillId -Description $row.description -Why $row.why -Tags $tags
  $displayName = Get-DisplayName -Skill $row.skill
  $descriptionPt = Get-PtDescription -Name $displayName -CategoryId $categoryId -Tags $tags
  $sourceUrl = $null
  if ($sourceMap.ContainsKey($row.skill)) { $sourceUrl = $sourceMap[$row.skill] }

  $skillsByCategory[$categoryId].Add([ordered]@{
    id = $skillId
    slug = (Convert-ToSlug $skillId)
    name = $displayName
    originalName = $row.skill
    categoryId = $categoryId
    descriptionPtBr = $descriptionPt
    descriptionOriginal = $row.description
    whyWeHaveIt = $row.why
    tags = $tags
    path = $installPath
    target = "codex"
    defaultInstallRoot = "~/.codex/skills"
    alternateInstallRoots = @("~/.agents/skills")
    hasSkillFile = [bool]$hasSkillFile
    installable = [bool](-not $isSystem -and $hasSkillFile)
    system = [bool]$isSystem
    sourceUrl = $sourceUrl
  })
}

$categories = New-Object System.Collections.Generic.List[object]
foreach ($categoryId in $categoryDefinitions.Keys) {
  $definition = $categoryDefinitions[$categoryId]
  $skills = @($skillsByCategory[$categoryId] | Sort-Object { $_.name }, { $_.id })
  if ($skills.Count -eq 0) { continue }
  $categories.Add([ordered]@{
    id = $categoryId
    name = $definition.name
    descriptionPtBr = $definition.description
    color = $definition.color
    tags = $definition.tags
    count = $skills.Count
    installableCount = @($skills | Where-Object { $_.installable }).Count
    skills = $skills
  })
}

$manifest = [ordered]@{
  schemaVersion = "1.0.0"
  generatedAt = $generatedAt
  language = "pt-BR"
  repository = [ordered]@{
    name = "skills-mcp-for-codex"
    owner = "galaxie-works"
    url = "https://github.com/galaxie-works/skills-mcp-for-codex"
    branch = "main"
  }
  installer = [ordered]@{
    recommendedStack = "Tauri + React + TypeScript"
    defaultTarget = "codex"
    supportedTargets = @("codex", "agents")
    safeInstallFlow = @(
      "download-manifest",
      "select-skills",
      "download-repository-version",
      "validate-skill-md",
      "backup-existing-folder",
      "copy-to-install-root",
      "show-result"
    )
  }
  installRoots = [ordered]@{
    codex = "~/.codex/skills"
    agents = "~/.agents/skills"
  }
  counts = [ordered]@{
    categories = $categories.Count
    skills = $rows.Count
    installableSkills = @($categories.skills | Where-Object { $_.installable }).Count
    systemSkills = @($categories.skills | Where-Object { $_.system }).Count
  }
  categories = $categories
}

$schema = [ordered]@{
  '$schema' = "https://json-schema.org/draft/2020-12/schema"
  '$id' = "https://github.com/galaxie-works/skills-mcp-for-codex/blob/main/manifest.schema.json"
  title = "Galaxie Codex Skills Installer Manifest"
  type = "object"
  required = @("schemaVersion", "generatedAt", "language", "repository", "installer", "installRoots", "counts", "categories")
  properties = [ordered]@{
    schemaVersion = @{ type = "string" }
    generatedAt = @{ type = "string" }
    language = @{ type = "string"; const = "pt-BR" }
    repository = @{
      type = "object"
      required = @("name", "owner", "url", "branch")
    }
    installer = @{
      type = "object"
      required = @("recommendedStack", "defaultTarget", "supportedTargets", "safeInstallFlow")
    }
    installRoots = @{
      type = "object"
      required = @("codex", "agents")
    }
    counts = @{
      type = "object"
      required = @("categories", "skills", "installableSkills", "systemSkills")
    }
    categories = @{
      type = "array"
      items = @{
        type = "object"
        required = @("id", "name", "descriptionPtBr", "color", "tags", "count", "installableCount", "skills")
      }
    }
  }
}

$manifest | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
$schema | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $schemaPath -Encoding UTF8

$categoryRows = foreach ($category in $categories) {
  "| <span style=`"color:$($category.color)`">&#9679;</span> **$($category.name)** | ``$($category.id)`` | $($category.count) | $($category.installableCount) | $($category.descriptionPtBr) |"
}

$topSkillsRows = foreach ($category in $categories) {
  $sample = @($category.skills | Where-Object { $_.installable } | Select-Object -First 8)
  $skillList = if ($sample.Count -gt 0) { ($sample | ForEach-Object { '``{0}``' -f $_.name }) -join ", " } else { "Somente suporte/runtime" }
  "| **$($category.name)** | $skillList |"
}

$categoriesMarkdown = @"
# Categorias dos Skills

![Manifest](https://img.shields.io/badge/manifest-ready-22c55e?style=for-the-badge)
![Idioma](https://img.shields.io/badge/descricoes-pt--BR-14b8a6?style=for-the-badge)
![Installer](https://img.shields.io/badge/Tauri_Installer-ready-8b5cf6?style=for-the-badge)

> Mapa visual para navegar o acervo de skills por intenção de uso. Este arquivo foi gerado a partir de ``docs/installed-skills.md`` e alimenta o ``manifest.json`` usado pelo app instalador.

## Resumo

| Métrica | Valor |
| --- | ---: |
| Categorias | $($manifest.counts.categories) |
| Skills no manifesto | $($manifest.counts.skills) |
| Skills instaláveis | $($manifest.counts.installableSkills) |
| Skills de sistema/runtime | $($manifest.counts.systemSkills) |

## Categorias

| Categoria | ID | Skills | Instaláveis | Descrição |
| --- | --- | ---: | ---: | --- |
$($categoryRows -join "`n")

## Amostras por Categoria

| Categoria | Exemplos de skills |
| --- | --- |
$($topSkillsRows -join "`n")

## Como usar no app

O app deve usar ``manifest.json`` como fonte de verdade para:

- montar a sidebar de categorias;
- permitir checkbox por categoria ou por skill;
- pesquisar por ``name``, ``descriptionPtBr``, ``descriptionOriginal`` e ``tags``;
- mostrar status ``Installed``, ``Update available`` ou ``Not installed``;
- validar ``hasSkillFile`` antes de habilitar instalação;
- copiar apenas itens com ``installable = true``;
- tratar skills com ``system = true`` como leitura/runtime, não como instalação comum.

## Paleta sugerida

As cores no manifesto foram pensadas para uma UI com cards, filtros e badges:

- ``frontend-ui``: rosa energia para UI/design.
- ``wordpress-web``: azul web/CMS.
- ``marketing-growth``: laranja performance.
- ``product-ops``: teal operação.
- ``automation-agents``: violeta automação.
- ``backend-architecture``: azul técnico.
- ``devops-cloud``: verde deploy.
- ``quality-security``: vermelho atenção.
- ``content-media``: âmbar criação.
- ``data-ai``: índigo IA/dados.
- ``business-strategy``: slate executivo.
- ``system-runtime``: cinza utilitário.
"@

Set-Content -LiteralPath $categoriesDocPath -Value $categoriesMarkdown -Encoding UTF8

$guideMarkdown = @"
# Guia do Manifesto para o Skills Installer

![Stack](https://img.shields.io/badge/stack-Tauri_%2B_React_%2B_TS-0ea5e9?style=for-the-badge)
![Segurança](https://img.shields.io/badge/install-safe_actions-22c55e?style=for-the-badge)
![Cross Platform](https://img.shields.io/badge/OS-Windows_macOS_Linux-f97316?style=for-the-badge)

Este guia descreve como o app instalador deve consumir o ``manifest.json`` deste repositório.

## Objetivo

Permitir que uma pessoa escolha categorias ou skills individuais e instale tudo com segurança em:

| Target | Pasta |
| --- | --- |
| ``codex`` | ``~/.codex/skills`` |
| ``agents`` | ``~/.agents/skills`` |

## Fluxo recomendado

~~~text
GitHub repo
  ↓
manifest.json
  ↓
Skills Installer
  ↓
seleção por categoria/skill
  ↓
download da versão escolhida
  ↓
validação de SKILL.md
  ↓
backup local se já existir
  ↓
cópia segura para o destino
  ↓
resultado por item
~~~

## Campos principais

| Campo | Uso no app |
| --- | --- |
| ``categories[].id`` | Chave da sidebar e filtros. |
| ``categories[].name`` | Nome visual da categoria. |
| ``categories[].color`` | Cor de badge/card. |
| ``categories[].skills[]`` | Lista renderizada no centro da tela. |
| ``skills[].id`` | ID estável do skill dentro do repo. |
| ``skills[].name`` | Nome amigável para UI. |
| ``skills[].descriptionPtBr`` | Descrição principal em português. |
| ``skills[].descriptionOriginal`` | Descrição original do SKILL.md, útil para busca avançada. |
| ``skills[].path`` | Caminho dentro do repo para copiar. |
| ``skills[].installable`` | Se pode ser instalado pelo app. |
| ``skills[].system`` | Se é skill de runtime/sistema. |
| ``skills[].sourceUrl`` | Link de origem quando conhecido. |

## Estados de instalação

| Estado | Como calcular |
| --- | --- |
| ``Not installed`` | Pasta de destino não existe. |
| ``Installed`` | Pasta existe e contém ``SKILL.md``. |
| ``Update available`` | Pasta existe, mas hash/versão local difere do item baixado. |
| ``Invalid local install`` | Pasta existe, mas falta ``SKILL.md``. |
| ``Not installable`` | ``installable = false``, normalmente skill de sistema/runtime. |

## Instalação segura

O app não deve executar comandos arbitrários. A instalação pode ser feita com operações de arquivo:

1. baixar o zip/tarball do GitHub na versão selecionada;
2. localizar cada ``skills[].path``;
3. validar ``SKILL.md``;
4. criar backup com timestamp se o destino já existir;
5. copiar arquivos para ``~/.codex/skills/<id>`` ou ``~/.agents/skills/<id>``;
6. registrar logs simples por item.

## UI sugerida

- Sidebar com categorias, contagem e checkbox "selecionar tudo".
- Área central com cards de skills.
- Busca por nome, descrição e tags.
- Filtros por status: instalado, atualização disponível, não instalado.
- Drawer/modal de detalhes com descrição em pt-BR, descrição original, origem e caminho.
- Tela de progresso com log por skill.
- Botão "Abrir pasta instalada".

## Regenerar manifesto

~~~powershell
.\tools\generate-installer-manifest.ps1
~~~

Sempre rode depois de atualizar ``docs/installed-skills.md`` ou mexer no acervo de ``skills/``.
"@

Set-Content -LiteralPath $guidePath -Value $guideMarkdown -Encoding UTF8

Write-Output "Generated manifest: $manifestPath"
Write-Output "Generated schema: $schemaPath"
Write-Output "Generated categories doc: $categoriesDocPath"
Write-Output "Generated installer guide: $guidePath"
