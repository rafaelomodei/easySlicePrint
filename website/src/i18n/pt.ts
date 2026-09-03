/** Brazilian Portuguese copy. See `en.ts` for the translation rules. */
import type { Dict } from "./en";

const pt: Dict = {
  meta: {
    tagline: "Corte. Encaixe. Imprima.",
    description:
      "Divisão não destrutiva de modelos e conectores personalizados para impressão 3D — add-on gratuito e de código aberto para Blender.",
  },

  language: {
    label: "Idioma",
    names: { en: "English", pt: "Português", es: "Español" },
  },

  nav: {
    workflow: "Fluxo",
    planMode: "Plan Mode",
    connectors: "Conectores",
    features: "Recursos",
    install: "Instalação",
    faq: "Perguntas",
  },

  header: {
    home: "Início do {name}",
    sections: "Seções",
    download: "Baixar",
  },

  hero: {
    pillFree: "Gratuito &amp; código aberto",
    pillBlender: "Blender {blenderMin} – {blenderMax}",
    pillPlatforms: "Windows · macOS · Linux",
    titleLead: "Corte. Encaixe.",
    titleAccent: "Imprima.",
    lead: "Divida qualquer modelo em peças imprimíveis com cortes por plano, curva ou laço livre, gere conectores de pino e encaixe que realmente encaixam e exporte um arquivo por peça — sem nunca tocar na malha original.",
    download: "Baixar v{version}",
    free: "· grátis",
    github: "Ver no GitHub",
    fine: "{license} · add-on para Blender · Exporta STL / OBJ / FBX em milímetros",
  },

  status: {
    pill: "Alfa",
    note:
      "<strong>Versão alfa.</strong> O {name} ainda está em desenvolvimento ativo: espere bugs e arestas. Um corte pode falhar ou sair errado em algumas malhas, e um plano salvo em uma versão pode não ser reconstruído da mesma forma na seguinte. Mantenha um backup do seu <code>.blend</code>, confira cada peça antes de imprimir e relate no GitHub o que der errado.",
  },

  workflow: {
    eyebrow: "Fluxo de trabalho",
    title: "Três passos do modelo às peças imprimíveis",
    intro:
      "A ferramenta inteira cabe em uma aba da sidebar. Desenhe onde o corte deve passar, deixe o add-on posicionar os conectores, exporte.",
    steps: {
      cut: {
        title: "Desenhe o corte",
        body: "Arraste uma linha para um corte reto, desenhe uma curva ou trace um laço em volta de um pescoço ou pulso direto na superfície. Os cortes seguem a vista: o que você desenha é o que sai.",
      },
      connectors: {
        title: "Gere os conectores",
        body: "Um pino de um lado, o encaixe correspondente do outro. Escolha a forma e o tamanho, defina a folga da sua impressora, troque o lado ou mova o conector na mão.",
      },
      export: {
        title: "Exporte as peças",
        body: "Um clique grava um STL, OBJ ou FBX por peça em uma pasta, já em milímetros. Confira o encaixe na Exploded View antes de imprimir.",
      },
    },
  },

  planMode: {
    eyebrow: "Plan Mode",
    title: "Planeje cada corte. Construa quando quiser.",
    intro:
      "O Plan Mode é não destrutivo: cortes são registros leves com preview ao vivo. Edite, mova, desative ou apague e depois faça o Build de uma vez. Volte ao plano quantas vezes precisar — o modelo original nunca é alterado.",
    plane: {
      title: "Plane Cut",
      body: "Arraste uma linha atravessando o modelo e um corte plano é criado nela. Selecione o corte na lista e use <strong>Edit Cut Surface</strong> para mover, girar ou escalar o plano com <kbd>G</kbd> <kbd>R</kbd> <kbd>S</kbd> — o conector acompanha.",
      checks: [
        "<strong>Two Contacts / Base Split</strong> — corte os dois pés de uma base numa só operação, cada um com o seu conector",
        "<strong>Chain Cuts</strong> — já começa o próximo corte automaticamente",
        "Posição, rotação e escala do conector editáveis corte a corte",
      ],
    },
    curve: {
      title: "Curve Cut",
      body: "Desenhe uma linha curva sobre o modelo e o corte segue a linha atravessando tudo. Depois arraste os pontos de controle, adicione ou remova pontos, ou deslize a curva inteira; a suavização e a quantidade de pontos são você quem define.",
      checks: [
        "Superfície de corte extrudada na direção da vista",
        "Editor de pontos: arraste, <kbd>Ctrl</kbd>+clique para adicionar, <kbd>X</kbd> para apagar, <kbd>Ctrl</kbd>+<kbd>Z</kbd> desfaz",
      ],
    },
    freehand: {
      title: "Freehand Cut",
      body: "Para tudo o que um plano não alcança: desenhe um laço fechado <em>em volta</em> da superfície — um pescoço, um pulso, uma cauda — orbitando entre os traços. O laço é preenchido e vira a superfície de corte.",
      checks: [
        "Orbite com o <kbd>botão do meio</kbd> enquanto desenha e feche o laço no ponto inicial ou com <kbd>Enter</kbd>",
        "Suavização e quantidade de pontos de controle ajustáveis antes e depois",
      ],
    },
    build: {
      title: "Build, revise, aprove",
      body: "O <strong>Build</strong> roda os booleanos e coloca as peças na coleção <code>ESP_Built_&lt;name&gt;</code>. Não gostou? O <strong>Back to Plan</strong> devolve o rascunho com todos os cortes intactos. O <strong>Approve</strong> finaliza e, com <em>Keep Original</em>, guarda o modelo de origem numa coleção de backup oculta.",
      checks: [
        "Desmarque <em>Ready</em> para deixar um corte fora do build, esconder o preview ou apagá-lo",
        "<strong>Skip Failed Cuts</strong> continua construindo quando um booleano falha",
        "<strong>Remesh</strong> voxel opcional das peças construídas",
      ],
    },
  },

  quickCut: {
    eyebrow: "Quick Cut",
    title: "Ou corte agora mesmo",
    intro:
      "O Quick Cut é o modo imediato: desenhe uma vez e receba as peças finais com o conector já no lugar. Sem plano, sem histórico — as mesmas ferramentas, pelo caminho mais curto.",
    checks: [
      "<strong>Plane, Curve e Freehand</strong> funcionam todos no Quick Cut",
      "Conector automático usando a forma, o tamanho e a folga atuais",
      "Peças nomeadas por lado: <code>_UPPER/_LOWER</code>, <code>_LEFT/_RIGHT</code>, <code>_FRONT/_BACK</code>",
      "Mude para o Plan Mode quando quiser, com um clique",
    ],
  },

  connectors: {
    eyebrow: "Conectores",
    title: "Pinos e encaixes no ponto da sua impressora",
    intro:
      "Todo corte ganha um pino de um lado e o encaixe correspondente do outro. Ajuste a folga uma vez nas preferências e esqueça o assunto.",
    shapes: ["Cilindro", "Cônico", "Hexagonal", "Caixa"],
    shapesCustom: "+ suas próprias malhas",
    checks: [
      "<strong>Presets de tamanho</strong> ou largura e altura explícitas em milímetros",
      "<strong>Folga</strong> entre pino e encaixe, específica de cada impressora",
      "<strong>Ponta assimétrica</strong> — encaixe mais fundo que o pino, com comprimento extra na ponta",
      "<strong>Lado do pino</strong> A ou B, troca com um clique",
      "<strong>Ajuste manual</strong> — selecione o conector e mova, gire ou escale à vontade, com reset a qualquer momento",
      "<strong>Cut gap (kerf)</strong> — material removido ao longo do corte para as peças não se tocarem",
      "<strong>Biblioteca própria</strong> — qualquer malha rígida na coleção <code>ESP_Connectors</code> aparece no menu Shape",
    ],
  },

  features: {
    eyebrow: "Tudo incluído",
    title: "Lista de recursos",
    items: {
      plane: { title: "Plane Cut", body: "Arraste uma linha no viewport → corte plano atravessando o modelo." },
      curve: { title: "Curve Cut", body: "Desenhe uma linha curva sobre o modelo → o corte segue a linha." },
      freehand: {
        title: "Freehand Cut",
        body: "Laço fechado em volta da superfície, orbitando enquanto desenha → superfície de corte preenchida.",
      },
      baseSplit: {
        title: "Two Contacts / Base Split",
        body: "Dois contatos cortados numa só operação, cada um com o seu conector.",
      },
      quickCut: { title: "Quick Cut mode", body: "Peças finais na hora, sem histórico." },
      planMode: {
        title: "Plan Mode",
        body: "Registros não destrutivos, superfícies e conectores editáveis, Build / Back to Plan / Approve.",
      },
      connectors: {
        title: "Conectores",
        body: "Cilindro, Cônico, Hexagonal, Caixa ou malhas próprias; presets ou tamanho explícito; folga; ponta assimétrica; lado do pino; transformação manual.",
      },
      kerf: { title: "Cut Gap (kerf)", body: "Material removido ao longo do corte para as peças não se tocarem." },
      remesh: { title: "Remesh", body: "Remesh voxel opcional das peças construídas." },
      exploded: {
        title: "Exploded View",
        body: "Afasta as peças para inspecionar os conectores e volta.",
      },
      export: { title: "Export", body: "Um arquivo por peça — STL, OBJ, FBX — numa pasta, em milímetros." },
      checkMesh: { title: "Check Mesh", body: "Verificação manifold com aviso antes de cortar." },
    },
  },

  who: {
    eyebrow: "Feito para",
    title: "Para quem é?",
    cards: {
      minis: {
        title: "Miniaturas &amp; figuras",
        body: "Divida bustos e miniaturas em pescoços, pulsos e bases para cada peça imprimir em pé e com o mínimo de suportes.",
      },
      cosplay: {
        title: "Cosplay &amp; props",
        body: "Capacetes, armaduras e armas maiores que a mesa de impressão — corte em pedaços que se encaixam de volta.",
      },
      product: {
        title: "Produto &amp; prototipagem mecânica",
        body: "Medidas explícitas em milímetros, folga e kerf: peças que encaixam do jeito que o CAD manda.",
      },
      farms: {
        title: "Print farms &amp; hobbistas",
        body: "Planeje o modelo inteiro uma vez, reconstrua depois dos ajustes, exporte todas as peças com um clique.",
      },
    },
  },

  compat: {
    eyebrow: "Requisitos",
    title: "Compatibilidade, desempenho e limites",
    compatibility: {
      title: "Compatibilidade",
      checks: [
        "Blender <strong>{blenderMin} – {blenderMax}</strong>, testado headless nas duas pontas LTS no CI",
        "Windows, macOS e Linux",
        "Malhas fechadas e <strong>manifold</strong>, com escala e rotação aplicadas",
        "Cena em milímetros (unit scale 0.001) ou a preferência <em>1 unit = 1 mm</em>",
      ],
    },
    performance: {
      title: "Desempenho",
      checks: [
        "O planejamento é instantâneo: a geometria só roda no <strong>Build</strong>",
        "O tempo de build depende da quantidade de polígonos e do solver booleano",
        "Solver <em>Manifold</em> (Blender 4.5+) usado automaticamente, <em>Exact</em> como fallback",
      ],
    },
    limits: {
      title: "Limitações conhecidas",
      items: [
        "Malhas abertas, auto-intersectadas ou quebradas geram booleanos errados — rode o <em>Check Mesh</em> antes.",
        "Não é um analisador de imprimibilidade: espessura de parede, orientação, suportes e tolerâncias são por sua conta.",
        "Os conectores são rígidos por definição; nada de juntas articuladas ou móveis.",
        "Sugestões automáticas de corte pelo tamanho da mesa estão no roadmap, ainda não chegaram.",
      ],
    },
  },

  install: {
    eyebrow: "Instalação",
    title: "Instale em menos de um minuto",
    steps: [
      "<strong>Baixe</strong> o <code>easy_slice_print-{version}.zip</code> abaixo.",
      "No Blender abra <strong>Edit → Preferences → Add-ons</strong>, clique no menu <strong>⌄</strong> no canto superior direito, escolha <strong>Install from Disk…</strong> e selecione o zip.",
      "Ative o <strong>{name}</strong>.",
      "Aperte <kbd>N</kbd> no 3D Viewport: o painel fica na aba <strong>EasySlice</strong> da sidebar.",
    ],
    quickstart: {
      title: "Início rápido",
      steps: [
        "Use uma cena em milímetros ou marque <em>Preferences → EasySlice → Units → 1 unit = 1 mm</em>.",
        "Selecione uma malha fechada e aplique escala &amp; rotação (<kbd>Ctrl</kbd>+<kbd>A</kbd>). Na dúvida, rode o <em>Check Mesh</em>.",
        "Escolha <strong>Quick Cut</strong> ou <strong>Plan Mode</strong>, clique em <strong>Plane</strong>, <strong>Curve</strong> ou <strong>Freehand</strong> e desenhe.",
        "Defina a forma do conector, o tamanho, o lado do pino, o cut gap e a folga.",
        "<strong>Build</strong>, confira o encaixe na <strong>Exploded View</strong>, <strong>Export</strong>.",
      ],
      note: "A folga depende da impressora (0,15–0,4 mm é comum). Imprima um teste pequeno antes.",
    },
  },

  download: {
    eyebrow: "Download",
    body: "Grátis, sem conta, sem chave de licença. O zip instala direto no Blender. Código-fonte, issues e versões antigas estão no GitHub.",
    releases: "Todas as releases",
    changelog: "Changelog",
    note: "Em breve também na plataforma Blender Extensions, para instalar direto pelo <em>Preferences → Get Extensions</em>.",
    meta: {
      version: "Versão",
      blender: "Blender",
      platforms: "Plataformas",
      platformsValue: "Windows · macOS · Linux",
      license: "Licença",
      price: "Preço",
      priceValue: "Grátis",
    },
  },

  faq: {
    eyebrow: "Perguntas",
    title: "Perguntas e respostas",
    items: [
      {
        q: "É gratuito mesmo?",
        a: "É. O {name} é software livre sob a GNU GPL v3.0 ou posterior: use, estude, modifique e compartilhe, inclusive comercialmente, desde que os trabalhos derivados permaneçam sob a mesma licença.",
      },
      {
        q: "Quais versões do Blender são suportadas?",
        a: "Do Blender {blenderMin} ao {blenderMax}. A suíte de testes roda headless nas duas pontas LTS a cada commit. Windows, macOS e Linux.",
      },
      {
        q: "O add-on altera o meu modelo original?",
        a: "No Plan Mode, não. Os cortes ficam guardados como registros e só rodam quando você aperta <strong>Build</strong>; o objeto de origem fica numa coleção <code>ESP_Backup</code> oculta quando o <em>Keep Original</em> está ligado. O <strong>Back to Plan</strong> devolve o rascunho a qualquer momento.",
      },
      {
        q: "Que folga eu devo usar nos conectores?",
        a: "Depende da impressora, do material e do fatiador. 0,15–0,4 mm cobre a maioria das FDM; impressoras de resina aceitam valores mais apertados. Imprima um par de teste antes — o pino cônico é a forma mais tolerante.",
      },
      {
        q: "Posso usar as minhas próprias formas de conector?",
        a: "Pode. Abra a biblioteca de conectores (ícone ao lado de <em>Shape</em>), jogue qualquer malha rígida na coleção <code>ESP_Connectors</code> seguindo a convenção da caixa unitária e ela aparece no menu Shape.",
      },
      {
        q: "E juntas articuladas ou rótulas?",
        a: "Estão fora do escopo por decisão de projeto: os conectores são pinos e encaixes rígidos para colar ou encaixar as peças de volta.",
      },
      {
        q: "Meu corte falha ou sai um resultado estranho.",
        a: "Operações booleanas precisam de uma malha fechada e manifold, com escala aplicada. Rode o <em>Check Mesh</em> antes. Malhas muito densas demoram mais; o solver <em>Manifold</em> (Blender 4.5+) é escolhido automaticamente quando existe. Ative o <em>Skip Failed Cuts</em> para continuar construindo o resto.",
      },
    ],
  },

  support: {
    eyebrow: "Suporte e roadmap",
    title: "Desenvolvido ativamente, em aberto",
    cards: {
      bug: {
        title: "Achou um bug?",
        body: "Abra uma issue com a sua versão do Blender e, se puder, o arquivo .blend. Travamentos e cortes errados têm prioridade.",
        link: "Reportar no GitHub →",
      },
      feature: {
        title: "Quer um recurso novo?",
        body: "Sugestões de corte pelo tamanho da mesa são as próximas da fila. Vote, comente ou proponha a sua no tracker.",
        link: "Pedir um recurso →",
      },
      contribute: {
        title: "Quer contribuir?",
        body: "Núcleo de geometria pura, testes headless em duas versões do Blender, Python formatado com ruff. Pull requests são bem-vindos.",
        link: "Ler o guia →",
      },
    },
  },

  footer: {
    legal:
      "Software livre sob a GNU GPL v3.0 ou posterior. O {name} é um projeto independente: não é afiliado, endossado nem derivado de nenhum add-on comercial, e nenhum código ou asset de terceiros está incluído.",
    project: {
      title: "Projeto",
      source: "Código-fonte",
      releases: "Releases",
      changelog: "Changelog",
      license: "Licença",
    },
    docs: {
      title: "Documentação",
      architecture: "Arquitetura",
      features: "Mapa de recursos",
      contributing: "Como contribuir",
      readme: "README em português",
    },
    help: {
      title: "Ajuda",
      bug: "Reportar um bug",
      feature: "Pedir um recurso",
      discussions: "Discussões",
      security: "Política de segurança",
    },
    copyright:
      "© {year} {author} e os contribuidores do {name} · Blender é marca registrada da Blender Foundation.",
  },

  notFound: {
    title: "Página não encontrada — {name}",
    code: "404",
    heading: "Essa página ficou do outro lado do corte.",
    body: "Não tem nada aqui — mas os conectores continuam encaixando.",
    cta: "Voltar ao início",
  },

  media: {
    badgeVideo: "Vídeo de demonstração em breve",
    badgeImage: "Captura de tela em breve",
    hero: {
      alt: "Demonstração do {name}: um Curve cut desenhado na cauda de um cavalo de carrossel, que sai como peça pronta para imprimir",
      expects: "Gravação de tela de 20–40 s: desenhar um Freehand cut → Build → Exploded View → Export",
    },
    stepCut: {
      alt: "Viewport durante o desenho de uma linha de corte sobre o modelo",
      expects: "Viewport no meio do traço, com a linha de corte visível",
    },
    stepConnectors: {
      alt: "Peças construídas em vista explodida mostrando o pino e o encaixe",
      expects: "Peças construídas na Exploded View, pino e encaixe visíveis",
    },
    stepExport: {
      alt: "Painel de exportação com as peças gravadas em arquivos STL",
      expects: "Painel Export com a pasta e o formato, peças exportadas abertas no fatiador",
    },
    planeCut: {
      alt: "Plane cut: arrastando uma linha sobre um modelo no Plan Mode",
      expects: "Plan Mode: arrastar um Plane cut, depois Edit Cut Surface e mover o plano com G/R",
    },
    curveCut: {
      alt: "Curve cut: uma linha curva desenhada na cauda de um cavalo de carrossel, que sai como peça separada",
      expects: "Plan Mode: desenhar um Curve cut atravessando a silhueta e arrastar alguns pontos de controle",
    },
    freehandCut: {
      alt: "Freehand cut: desenhando um laço fechado em volta de um pescoço enquanto orbita",
      expects: "Plan Mode: laço Freehand em volta de um pescoço/pulso, orbitando com o botão do meio entre os traços",
    },
    buildExport: {
      alt: "Build, Back to Plan, Approve e Export",
      expects: "Build → as peças aparecem → Back to Plan → ajustar → Approve → Export STL",
    },
    quickCut: {
      alt: "Quick Cut: um corte plano com conector automático, sem histórico",
      expects: "Modo Quick Cut: um arraste e as peças com o conector aparecem na hora",
    },
    connectors: {
      alt: "Formas de conector: cilindro, cônico, hexagonal, caixa e uma malha própria",
      expects: "Close nas cinco formas de conector lado a lado, com pinos e encaixes",
    },
  },
};

export default pt;
