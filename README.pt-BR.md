<h1 align="center">EasySlice Print</h1>

<p align="center">
  <strong>Corte. Encaixe. Imprima.</strong><br>
  Divisão não destrutiva de modelos e conectores personalizados para impressão 3D — add-on gratuito para Blender.
</p>

<p align="center">
  <a href="https://github.com/rafaelomodei/easySlicePrint/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/rafaelomodei/easySlicePrint/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/rafaelomodei/easySlicePrint/releases"><img alt="Release" src="https://img.shields.io/github/v/release/rafaelomodei/easySlicePrint?include_prereleases"></a>
  <img alt="Blender 4.2 – 5.2" src="https://img.shields.io/badge/Blender-4.2%20%E2%80%93%205.2-orange">
  <a href="LICENSE"><img alt="Licença: GPL-3.0-or-later" src="https://img.shields.io/badge/license-GPL--3.0--or--later-blue"></a>
  <a href="CODE_OF_CONDUCT.md"><img alt="Código de Conduta" src="https://img.shields.io/badge/code%20of%20conduct-Contributor%20Covenant%202.1-purple"></a>
</p>

<p align="center">
  <a href="https://rafaelomodei.github.io/easySlicePrint/"><strong>Site</strong></a> ·
  <a href="https://github.com/rafaelomodei/easySlicePrint/releases/latest"><strong>Download</strong></a> ·
  <em>English: see <a href="README.md">README.md</a></em>
</p>

<!-- TODO(media): grave a demo, coloque os arquivos em docs/media/ e descomente.
     A lista de capturas está em docs/media/README.md.
<p align="center"><img src="docs/media/demo.gif" alt="Demonstração do EasySlice Print" width="720"></p>
-->

|  |  |
|---|---|
| ✂️ **Corte qualquer modelo** | plano, curva ou laço livre — não só planos retos |
| 🔩 **Pinos e encaixes automáticos** | formas prontas ou suas próprias malhas de conector |
| 🧩 **Planeje vários cortes** | não destrutivo: edite, mova, desative, reconstrua — o original nunca é tocado |
| 🖨️ **Exporte peças prontas** | um STL/OBJ/FBX por peça, em milímetros |

```
1. Desenhe o corte  →  2. Gere os conectores  →  3. Exporte as peças
```

<!-- TODO(media): descomente quando docs/media/step-*.png existirem.
<p align="center">
  <img src="docs/media/step-1-cut.png" width="30%">
  <img src="docs/media/step-2-connectors.png" width="30%">
  <img src="docs/media/step-3-export.png" width="30%">
</p>
-->

## Recursos

| | |
|---|---|
| **Plane Cut** (corte reto) | arraste uma linha no viewport → corte plano atravessando o modelo |
| **Curve Cut** (corte curvo) | desenhe uma linha curva sobre o modelo → o corte segue a linha atravessando o modelo |
| **Freehand Cut** (corte livre) | desenhe um laço fechado *em volta* da superfície (orbite enquanto desenha) → o laço é preenchido e vira a superfície de corte (pescoços, pulsos, qualquer lugar que um plano não alcança) |
| **Two Contacts / Base Split** | dois contatos cortados numa só operação (ex.: os dois pés numa base), cada um com o seu conector |
| **Quick Cut** | corte final imediato, sem histórico |
| **Plan Mode** | não destrutivo: planeje vários cortes, edite/desative/remova, mova planos e conectores, **Build** quando estiver pronto, **Back to Plan** para continuar editando, **Approve** para finalizar. O modelo original nunca é alterado |
| **Conectores** | pino + encaixe automáticos: Cilindro, Cônico, Hexagonal, Caixa ou **malhas próprias** da sua biblioteca; presets de tamanho ou largura/altura explícitas; folga (clearance); ponta assimétrica (encaixe mais fundo); escolha de qual lado leva o pino; mova/gire/escale o conector livremente |
| **Cut Gap (kerf)** | material removido ao longo do corte para as peças não se tocarem |
| **Remesh** | remesh voxel opcional das peças |
| **Vista explodida** | afasta as peças para inspecionar os conectores e volta |
| **Exportação** | um arquivo por peça — **STL, OBJ, FBX** — numa pasta, em milímetros |

Testado headless no Blender 4.2.23 LTS e 5.2.1 LTS (o CI roda os dois). Funciona em Windows, macOS e Linux.

## Instalação

1. Baixe `easy_slice_print-<versão>.zip` nas [releases](https://github.com/rafaelomodei/easySlicePrint/releases) ou gere com `scripts/build.sh`.
2. Blender → *Edit → Preferences → Add-ons → ⌄ (canto superior direito) → Install from Disk…* → escolha o zip.
3. Ative **EasySlice Print**. O painel fica na sidebar do 3D Viewport (`N`) → aba **EasySlice**.

## Início rápido

1. Use uma **cena em milímetros** (Scene Properties → Units → Unit Scale `0.001`, Length `Millimeters`)
   ou marque em *Preferences → EasySlice → Units → "1 unit = 1 mm"*.
2. Selecione uma malha **fechada e manifold**. Aplique escala e rotação (`Ctrl+A`). Use *Check Mesh* (ícone ✓) se tiver dúvida.
3. Escolha **Quick Cut** ou **Plan Mode**.
4. Clique em **Plane**, **Curve** ou **Freehand** e desenhe no viewport:
   * Plane: arraste uma linha atravessando o modelo (ou clique, clique). `Esc` cancela.
   * Curve: desenhe uma linha sobre o modelo cruzando toda a silhueta.
   * Freehand: desenhe na superfície em volta do modelo; orbite com o `botão do meio` entre traços;
     volte ao ponto verde inicial (ou `Enter`) para fechar o laço.
5. Painel Connector: forma, tamanho, lado do pino, cut gap, folga.
6. **Plan mode**: selecione um corte na lista para editar — *Edit Cut Surface* (G/R/S nos planos, arraste
   pontos nas curvas), *Select Connector* e G/R/S, *Reset*, *Swap* do lado do pino. Desmarque **Ready** para
   deixar um corte fora do build, o olho esconde o preview, ✕ apaga.
7. **Build** → as peças aparecem em `ESP_Built_<nome>`. **Back to Plan** para mudar algo, **Approve** para finalizar.
8. **Exploded View** para conferir o encaixe, **Export** para gravar os arquivos.

A folga do conector depende da impressora (0,15–0,4 mm é comum). Imprima um teste pequeno antes.

### Conectores personalizados

Clique no ícone de biblioteca ao lado de *Shape*. A coleção `ESP_Connectors` é criada com os modelos
padrão. Qualquer malha adicionada a ela aparece no menu Shape. Convenção: a malha cabe em
`x, y ∈ [-0.5, 0.5]`, `z ∈ [-1, 1]`; `z = 0` é a superfície de corte e `+z` é a ponta que entra no encaixe.
Conectores precisam ser rígidos (sem articulações).

## Requisitos e limitações

* Blender 4.2 – 5.2. Somente malhas fechadas e manifold; malhas abertas, auto-intersectadas ou quebradas geram booleanos errados.
* O tempo depende da quantidade de polígonos e do solver booleano (Preferences). O solver *Manifold*
  (Blender 4.5+) é usado automaticamente quando existe, *Exact* como fallback.
* Não é um analisador de imprimibilidade — espessura de parede, orientação, suportes e tolerâncias são por sua conta.

## Desenvolvimento

```bash
BLENDER=/caminho/para/blender scripts/run_tests.sh   # testes headless
BLENDER=/caminho/para/blender scripts/build.sh       # gera o zip em dist/
```

Veja [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) e [docs/FEATURES.md](docs/FEATURES.md). O site público fica em
[`website/`](website/) (Astro, publicado no GitHub Pages por `.github/workflows/pages.yml`).
Contribuições são bem-vindas — leia [CONTRIBUTING.md](CONTRIBUTING.md) e o [Código de Conduta](CODE_OF_CONDUCT.md).

## Licença

**GNU General Public License v3.0 ou posterior** (`GPL-3.0-or-later`) — livre para usar, estudar,
modificar e compartilhar, inclusive comercialmente, desde que os trabalhos derivados permaneçam sob
a mesma licença. Veja [LICENSE](LICENSE).

O EasySlice Print é um projeto independente. Não é afiliado, endossado nem derivado de nenhum add-on
comercial; nenhum código ou asset de terceiros está incluído.
