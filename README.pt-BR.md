# EasySlice Print

[![CI](https://github.com/rafaelomodei/easySlicePrint/actions/workflows/ci.yml/badge.svg)](https://github.com/rafaelomodei/easySlicePrint/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/rafaelomodei/easySlicePrint?include_prereleases)](https://github.com/rafaelomodei/easySlicePrint/releases)
![Blender 4.2 – 5.2](https://img.shields.io/badge/Blender-4.2%20%E2%80%93%205.2-orange)
![License: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/license-PolyForm%20NC%201.0.0-blue)

**Slice. Join. Print.** — add-on gratuito e open source para Blender que divide modelos 3D em
peças imprimíveis, cria **pinos e encaixes** correspondentes e exporta as peças para impressão em
resina ou FDM.

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

1. Baixe `easy_slice_print-<versão>.zip` (releases) ou gere com `scripts/build.sh`.
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

Veja [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) e [docs/FEATURES.md](docs/FEATURES.md).
Contribuições são bem-vindas — leia [CONTRIBUTING.md](CONTRIBUTING.md) e o [Código de Conduta](CODE_OF_CONDUCT.md).

## Licença

**PolyForm Noncommercial License 1.0.0** — livre para usar, estudar, modificar e compartilhar,
inclusive contribuir, **mas não para fins comerciais** (não pode vender, embutir em produto pago nem
prestar serviço comercial com ele). Veja [LICENSE](LICENSE).

> Observação: a plataforma oficial de extensões do Blender só aceita licenças compatíveis com a GPL;
> por isso o add-on é distribuído aqui (releases / Install from Disk) e não em extensions.blender.org.

O EasySlice Print é um projeto independente. Não é afiliado, endossado nem derivado de nenhum add-on
comercial; nenhum código ou asset de terceiros está incluído.
