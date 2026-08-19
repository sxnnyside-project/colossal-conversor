# Colossal Conversor — Guia do Usuário

<p align="center">
  <em>Tudo o que você precisa para instalar, usar e resolver problemas do Colossal Conversor no dia a dia.</em>
</p>

<p align="center">
  <sub>Idiomas: <a href="../en/README.md">English</a> · <a href="../es/README.md">Español</a> · <a href="../fr/README.md">Français</a> · <a href="../ja/README.md">日本語</a> · <a href="../pt/README.md">Português</a> · <a href="../zh/README.md">中文</a></sub>
</p>

---

## 1. O que é o Colossal Conversor?

O Colossal Conversor é um aplicativo de desktop offline para converter
arquivos de áudio, vídeo, imagem, documentos, planilhas e apresentações.
Tudo roda localmente através de um núcleo de execução nativo em C++20 —
sem upload para a nuvem, sem conta, sem dependência de rede para a
conversão em si. Veja o [README](../../../README.md) principal para a
visão técnica completa.

Este guia cobre o uso real do aplicativo no dia a dia: instalação, sua
primeira conversão, trabalho com lotes e pipelines, e como se recuperar
quando algo dá errado.

## 2. Plataformas Suportadas

O Colossal Conversor tem como alvo **macOS, Linux e Windows**. O
supervisor de processos nativo tem um backend dedicado por plataforma, de
modo que a criação de processos, a captura de saída, o cancelamento e a
limpeza se comportam da mesma forma em todos os lugares.

| Plataforma | Status |
|---|---|
| macOS | Verificada — compilada, testada e usada no desenvolvimento diário |
| Linux | Implementada (compartilha o backend do macOS); ainda não verificada em um runner Linux |
| Windows | Implementada de acordo com as APIs de processo do Windows; ainda não verificada em um runner Windows |

"Implementada mas ainda não verificada" significa que o código existe e
segue os contratos corretos de plataforma, mas ninguém confirmou ainda que
uma conversão real funciona nessa plataforma. Isso será atualizado conforme
a verificação avançar — veja a seção de plataformas suportadas do README
principal para o status atual, e [CONTRIBUTING.md](../../../CONTRIBUTING.md)
se você quiser ajudar a verificar Linux ou Windows.

## 3. Instalação

Instalar o Colossal Conversor em si é diferente de instalar as ferramentas
externas que ele usa para algumas conversões (veja a seção Dependências
Externas abaixo).

### macOS / Linux

```bash
git clone https://github.com/sxnnyside-project/colossal-conservor.git
cd colossal-conservor
just install
just dev
```

### Windows

```powershell
git clone https://github.com/sxnnyside-project/colossal-conservor.git
cd colossal-conservor
just install
just dev
```

`just install` sincroniza as dependências Python e compila a extensão
nativa. `just dev` inicia o aplicativo. Se você não tiver o `just`, veja
suas [instruções de instalação](https://github.com/casey/just#installation)
— ou execute o equivalente `uv sync --all-groups` seguido da compilação
nativa com CMake descrita no README principal.

## 4. Dependências Externas

Algumas categorias de conversão chamam uma ferramenta externa; outras
rodam inteiramente em processo interno e não precisam de nada além disso.

| Ferramenta | Necessária para |
|---|---|
| FFmpeg | Conversões de áudio e vídeo |
| LibreOffice | Conversões de documentos, planilhas e apresentações |
| Poppler (`pdftoppm`) | Renderização de páginas de documento em imagem |
| Pandoc | Conversões markdown ↔ documento |
| ImageMagick | Conversões de imagem além de BMP/PPM/TGA (que rodam nativamente, sem ferramenta) |

Para verificar o que já está disponível:

```bash
just verify-tools
```

Para instalar o que estiver faltando:

- **macOS**: `bash tools/macos_install_deps.sh` (Homebrew)
- **Linux**: `bash tools/linux_install_deps.sh` (apt, dnf ou pacman — detectado automaticamente)
- **Windows**: execute `tools/windows_install_deps.ps1` no PowerShell (winget, ou Chocolatey se já instalado)

Instalar essas ferramentas **não** garante por si só que toda conversão vai
funcionar — isso apenas disponibiliza o mecanismo correspondente. O
aplicativo detecta cada ferramenta em tempo de execução e só oferece
conversões que realmente consegue executar.

## 5. Primeira Conversão

1. Abra o aplicativo (`just dev`).
2. Clique em **Select File(s)** ou arraste um arquivo para a área de entrada.
3. O Colossal Conversor detecta o formato de entrada e mostra apenas os
   formatos de destino que realmente consegue produzir, agrupados por
   categoria.
4. Clique em um formato de destino.
5. Clique em **Save As...** para escolher (ou confirmar) o destino, caso
   queira algo diferente do padrão.
6. Clique em **Convert** (ou pressione <kbd>Enter</kbd>).

Ao terminar, uma caixa de diálogo informa quantos arquivos foram
produzidos, com botões para abrir o resultado ou revelá-lo no gerenciador
de arquivos.

## 6. Múltiplos Arquivos

Clique em **Select File(s)** e escolha mais de um arquivo, ou arraste
vários de uma vez. O Colossal Conversor mostra apenas os formatos de saída
comuns a todas as entradas selecionadas. Escolha uma **pasta** de destino
(não um único arquivo) via **Save As...**, depois **Convert** — cada
entrada produz sua própria saída nessa pasta.

## 7. Conversões com Múltiplas Saídas

Algumas conversões produzem mais de um arquivo a partir de uma única
entrada — por exemplo, renderizar cada página de um PDF como uma imagem
separada. Isso é detectado automaticamente a partir do par de formatos
escolhido; o destino que você escolher se torna uma pasta contendo todas
as páginas produzidas, e a caixa de diálogo de conclusão informa o número
real de arquivos gerados.

## 8. Pipelines

Algumas conversões não podem acontecer em uma única etapa e são
automaticamente divididas em estágios internos — por exemplo, uma
apresentação convertida em imagem passa primeiro por um PDF intermediário.
Você não precisa configurar isso: escolha sua entrada e o formato de
destino normalmente, e a barra de progresso mostra qual estágio está em
execução. Os arquivos intermediários são limpos automaticamente assim que
o pipeline termina (ou falha, ou é cancelado).

## 9. Escolhendo um Formato de Saída

A grade de formatos só mostra destinos que o Colossal Conversor realmente
consegue produzir a partir da sua entrada atual — ela nunca anuncia uma
conversão que não pode executar. Ao selecionar um formato, aparece uma nota
de fidelidade (por exemplo "high", "medium", "layout") descrevendo o
quanto a saída preserva o original — útil ao converter entre formatos com
capacidades diferentes (por exemplo, um documento estilizado para texto
simples).

## 10. Seleção de Destino

**Save As...** permite escolher para onde vai a saída. Para uma conversão
de saída única, escolha um caminho de arquivo; para um lote ou uma
conversão com múltiplas saídas, escolha uma pasta. Se você não escolher
explicitamente, o aplicativo propõe um destino razoável ao lado do arquivo
de entrada.

## 11. Cancelamento

Clique em **Cancel** enquanto uma conversão está em andamento para
interrompê-la. Isso realmente encerra o processo subjacente (não apenas o
estado da interface) — nenhuma saída parcial é reportada como resultado
bem-sucedido, e a barra de status mostra "Conversion cancelled", distinto
tanto de sucesso quanto de falha. Você pode iniciar uma nova conversão
imediatamente depois.

## 12. Erros e Recuperação

Se uma conversão falhar, uma caixa de diálogo explica o que aconteceu em
linguagem simples, com um botão **Show Details...** para a saída técnica
subjacente (exibida apenas se solicitada). O aplicativo não trava nem
congela após uma conversão falhada — feche a caixa de diálogo e tente
novamente, ajustando a entrada, o formato de destino ou o destino conforme
necessário.

## 13. Dependências Ausentes

Se uma conversão precisar de uma ferramenta que não está instalada, a
mensagem de erro informa isso explicitamente e nomeia a ferramenta — não
será confundida com uma falha genérica. Execute `just verify-tools` para
ver o panorama completo, e veja a seção Dependências Externas acima para
saber como instalar o que estiver faltando.

## 14. Formatos Suportados

A grade de formatos dentro do aplicativo é a lista autoritativa e ao vivo
— ela é gerada a partir do mesmo catálogo que o mecanismo de conversão
usa, então nunca pode anunciar algo que a versão atual não consegue
realmente fazer. De forma geral, o Colossal Conversor suporta:

- **Áudio**: formatos comuns como MP3, WAV, FLAC, AAC, OGG e outros.
- **Vídeo**: formatos comuns como MP4, MKV, MOV, AVI, WebM e outros.
- **Imagem**: formatos comuns como PNG, JPEG, WebP, BMP, TIFF, GIF e outros.
- **Documento**: DOC/DOCX, ODT, RTF, TXT, PDF, Markdown, HTML, EPUB.
- **Planilha**: XLS/XLSX, ODS, CSV, TSV.
- **Apresentação**: PPTX/PPT, ODP.

Selecione um arquivo de entrada no aplicativo para ver a lista exata e
atual de destinos para aquele arquivo específico.

## 15. Solução de Problemas

**Uma conversão que eu esperava que funcionasse não é oferecida.** A lista
de formatos de destino é gerada a partir do formato detectado da sua
entrada específica — verifique se a entrada foi detectada corretamente
(mostrado ao lado do nome do arquivo) e se a conversão desejada é
realmente suportada para esse par de formatos.

**Erro de "dependência ausente".** Execute `just verify-tools` e instale a
ferramenta indicada (veja Dependências Externas / Dependências Ausentes
acima).

**A conversão falha imediatamente.** Verifique **Show Details...** na
caixa de diálogo de erro. Causas comuns: um arquivo de entrada corrompido
ou ilegível, ou um formato que a entrada detectada na verdade não
corresponde (por exemplo, um arquivo renomeado com a extensão errada).

**Cancel não parece fazer nada visualmente.** Em conversões muito curtas, a
operação pode terminar antes que o Cancel tenha efeito — isso é esperado,
não é um bug; o resultado será um sucesso ou falha normal, não uma
interface travada.

**O caminho de destino é inválido.** Certifique-se de que a pasta existe e
que você tem permissão de escrita nela; para uma saída de arquivo único,
certifique-se de que a pasta pai existe.

**Ainda com problemas?** Abra uma issue — veja [SUPPORT.md](../../../SUPPORT.md).

---

<p align="center">
  <sub>Parte da documentação do <a href="../../../README.md">Colossal Conversor</a> — A Sxnnyside Project Release</sub>
</p>
