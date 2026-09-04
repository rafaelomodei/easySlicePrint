/** Spanish copy. See `en.ts` for the translation rules. */
import type { Dict } from "./en";

const es: Dict = {
  meta: {
    tagline: "Corta. Encaja. Imprime.",
    description:
      "División no destructiva de modelos y conectores personalizados para impresión 3D — un add-on de Blender gratuito y de código abierto.",
  },

  language: {
    label: "Idioma",
    names: { en: "English", pt: "Português", es: "Español" },
  },

  nav: {
    workflow: "Flujo de trabajo",
    planMode: "Plan Mode",
    connectors: "Conectores",
    features: "Funciones",
    install: "Instalación",
    faq: "FAQ",
  },

  header: {
    home: "Inicio de {name}",
    sections: "Secciones",
    download: "Descargar",
  },

  hero: {
    pillFree: "Gratis y de código abierto",
    pillBlender: "Blender {blenderMin} – {blenderMax}",
    pillPlatforms: "Windows · macOS · Linux",
    titleLead: "Corta. Encaja.",
    titleAccent: "Imprime.",
    lead: "Divide cualquier modelo en piezas imprimibles con cortes de plano, curva o a mano alzada, añade conectores de pin y hembra que encajan de verdad, y exporta un archivo por pieza — sin tocar nunca la malla original.",
    download: "Descargar v{version}",
    free: "· gratis",
    github: "Ver en GitHub",
    fine: "{license} · Add-on de Blender · Exporta STL / OBJ / FBX en milímetros",
  },

  status: {
    pill: "Alfa",
    note:
      "<strong>Versión alfa.</strong> {name} sigue en desarrollo activo: espera fallos y aristas. Un corte puede fallar o salir mal en algunas mallas, y un plan guardado con una versión puede no reconstruirse igual en la siguiente. Guarda una copia de tu <code>.blend</code>, revisa cada pieza antes de imprimirla y avisa en GitHub de lo que salga mal.",
  },

  workflow: {
    eyebrow: "Flujo de trabajo",
    title: "Tres pasos de un modelo a piezas imprimibles",
    intro:
      "Toda la herramienta cabe en una pestaña de la barra lateral. Dibuja por dónde va el corte, deja que el add-on coloque los conectores, exporta.",
    steps: {
      cut: {
        title: "Dibuja el corte",
        body: "Arrastra una línea para un corte recto, traza una curva o dibuja un lazo alrededor de un cuello o una muñeca directamente sobre la superficie. Los cortes siguen la vista: lo que dibujas es lo que obtienes.",
      },
      connectors: {
        title: "Genera los conectores",
        body: "Un pin de un lado, la hembra correspondiente del otro. Elige la forma y el tamaño, ajusta la holgura de tu impresora, invierte los lados o mueve el conector a mano.",
      },
      export: {
        title: "Exporta piezas imprimibles",
        body: "Un clic escribe un STL, OBJ o FBX por pieza en una carpeta, ya en milímetros. Comprueba el ajuste en Exploded View antes de imprimir.",
      },
    },
  },

  planMode: {
    eyebrow: "Plan Mode",
    title: "Planifica cada corte. Construye cuando estés listo.",
    intro:
      "Plan Mode es no destructivo: los cortes son registros ligeros con vista previa en vivo. Edítalos, muévelos, desactívalos o elimínalos, y luego haz Build de todos a la vez. Vuelve al plan tantas veces como quieras — el modelo original nunca se modifica.",
    plane: {
      title: "Plane Cut",
      body: "Arrastra una línea sobre el modelo y se coloca un corte recto que lo atraviesa. Selecciona el corte en la lista y usa <strong>Edit Cut Surface</strong> para mover, girar o escalar el plano con <kbd>G</kbd> <kbd>R</kbd> <kbd>S</kbd> — el conector lo sigue.",
      checks: [
        "<strong>Two Contacts / Base Split</strong> — corta los dos apoyos de una base de una sola vez, cada uno con su propio conector",
        "<strong>Chain Cuts</strong> — empieza el siguiente corte automáticamente",
        "Posición, rotación y escala del conector editables por corte",
      ],
    },
    curve: {
      title: "Curve Cut",
      body: "Dibuja una línea curva sobre el modelo y el corte la sigue de lado a lado. Después arrastra los puntos de control, añádelos o quítalos, o desplaza la curva entera; el suavizado y el número de puntos los eliges tú.",
      checks: [
        "Superficie de corte extruida en la dirección de la vista",
        "Editor de puntos: arrastra, <kbd>Ctrl</kbd>+clic para añadir, <kbd>X</kbd> para borrar, <kbd>Ctrl</kbd>+<kbd>Z</kbd> para deshacer",
      ],
    },
    freehand: {
      title: "Freehand Cut",
      body: "Para todo lo que un plano no alcanza: dibuja un lazo cerrado <em>alrededor</em> de la superficie — un cuello, una muñeca, una cola — orbitando entre trazos. El lazo se rellena y se usa como superficie de corte.",
      checks: [
        "Orbita con <kbd>MMB</kbd> mientras dibujas, cierra el lazo en el punto inicial o con <kbd>Enter</kbd>",
        "Conserva cada punto que dibujas: un detalle trazado llega a la cara de corte impresa",
      ],
    },
    build: {
      title: "Build, revisa, aprueba",
      body: "<strong>Build</strong> ejecuta los booleanos y deja las piezas en una colección <code>ESP_Built_&lt;name&gt;</code>. ¿No te convence? <strong>Back to Plan</strong> restaura el borrador con todos los cortes intactos. <strong>Approve</strong> finaliza y, con <em>Keep Original</em>, guarda el modelo de origen en una colección de respaldo oculta.",
      checks: [
        "Desmarca <em>Ready</em> para dejar un corte fuera del build, ocultar su vista previa o eliminarlo",
        "<strong>Skip Failed Cuts</strong> sigue construyendo aunque falle un booleano",
        "<strong>Remesh</strong> por vóxeles opcional de las piezas construidas",
      ],
    },
  },

  quickCut: {
    eyebrow: "Quick Cut",
    title: "O córtalo ya mismo",
    intro:
      "Quick Cut es el modo inmediato: dibuja una vez y obtén las piezas finales con el conector ya colocado. Sin plan, sin historial — las mismas herramientas, el camino más rápido.",
    checks: [
      "<strong>Plane, Curve y Freehand</strong> funcionan todos en Quick Cut",
      "Conector automático con la forma, el tamaño y la holgura actuales",
      "Piezas nombradas por lado: <code>_UPPER/_LOWER</code>, <code>_LEFT/_RIGHT</code>, <code>_FRONT/_BACK</code>",
      "Cambia a Plan Mode cuando quieras con un solo interruptor",
    ],
  },

  connectors: {
    eyebrow: "Conectores",
    title: "Pins y hembras que encajan con tu impresora",
    intro:
      "Cada corte recibe un pin de un lado y la hembra correspondiente del otro. Ajusta el encaje una vez en las preferencias y olvídate.",
    shapes: ["Cilindro", "Cónico", "Hexágono", "Caja"],
    shapesCustom: "+ tus propias mallas",
    checks: [
      "<strong>Tamaños predefinidos</strong> o ancho y alto explícitos en milímetros",
      "<strong>Holgura</strong> entre el pin y la hembra, según tu impresora",
      "<strong>Punta asimétrica</strong> — hembra más profunda que el pin, más longitud extra de punta",
      "<strong>Lado del pin</strong> A o B, se invierte con un clic",
      "<strong>Ajuste manual</strong> — selecciona el conector y muévelo, gíralo o escálalo con total libertad, reinícialo cuando quieras",
      "<strong>Cut gap (kerf)</strong> — material retirado a lo largo del corte para que las piezas no se toquen",
      "<strong>Biblioteca propia</strong> — cualquier malla rígida de la colección <code>ESP_Connectors</code> aparece en el menú Shape",
    ],
  },

  features: {
    eyebrow: "Todo incluido",
    title: "Lista de funciones",
    items: {
      plane: { title: "Plane Cut", body: "Arrastra una línea en el viewport → corte recto que atraviesa el modelo." },
      curve: { title: "Curve Cut", body: "Dibuja una línea curva sobre el modelo → el corte la sigue de lado a lado." },
      freehand: {
        title: "Freehand Cut",
        body: "Lazo cerrado alrededor de la superficie, orbita mientras dibujas → superficie de corte rellenada.",
      },
      baseSplit: {
        title: "Two Contacts / Base Split",
        body: "Dos contactos cortados en una sola operación, cada uno con su propio conector.",
      },
      quickCut: { title: "Quick Cut mode", body: "Piezas finales al instante, sin historial." },
      planMode: {
        title: "Plan Mode",
        body: "Registros no destructivos, superficies y conectores editables, Build / Back to Plan / Approve.",
      },
      connectors: {
        title: "Conectores",
        body: "Cilindro, Cónico, Hexágono, Caja o mallas propias; tamaños predefinidos o medidas explícitas; holgura; punta asimétrica; lado del pin; transformación manual.",
      },
      kerf: { title: "Cut Gap (kerf)", body: "Material retirado a lo largo del corte para que las piezas no se toquen." },
      remesh: { title: "Remesh", body: "Remesh por vóxeles opcional de las piezas construidas." },
      exploded: {
        title: "Exploded View",
        body: "Separa las piezas para inspeccionar los conectores y vuelve a juntarlas.",
      },
      export: { title: "Export", body: "Un archivo por pieza — STL, OBJ, FBX — en una carpeta, en milímetros." },
      checkMesh: { title: "Check Mesh", body: "Comprobación manifold con aviso antes de cortar." },
    },
  },

  who: {
    eyebrow: "Pensado para",
    title: "¿Para quién es?",
    cards: {
      minis: {
        title: "Creadores de miniaturas y figuras",
        body: "Divide bustos y figuras por el cuello, las muñecas y la base para que cada pieza se imprima en vertical y con soportes mínimos.",
      },
      cosplay: {
        title: "Cosplay y props",
        body: "Cascos, armaduras y armas más grandes que la cama de impresión: córtalos en piezas que vuelven a unirse con pins.",
      },
      product: {
        title: "Producto y prototipado mecánico",
        body: "Medidas explícitas en milímetros, holgura y kerf: piezas que encajan como dice el CAD.",
      },
      farms: {
        title: "Granjas de impresión y aficionados",
        body: "Planifica un modelo entero una vez, recompón tras cada ajuste y exporta todas las piezas con un clic.",
      },
    },
  },

  compat: {
    eyebrow: "Requisitos",
    title: "Compatibilidad, rendimiento y límites",
    compatibility: {
      title: "Compatibilidad",
      checks: [
        "Blender <strong>{blenderMin} – {blenderMax}</strong>, probado headless en ambos extremos LTS en CI",
        "Windows, macOS y Linux",
        "Mallas cerradas y <strong>manifold</strong> con escala y rotación aplicadas",
        "Escena en milímetros (unit scale 0.001) o la preferencia <em>1 unit = 1 mm</em>",
      ],
    },
    performance: {
      title: "Rendimiento",
      checks: [
        "Planificar es instantáneo: la geometría solo se calcula al hacer <strong>Build</strong>",
        "El tiempo de build depende del número de polígonos y del solver booleano",
        "El solver <em>Manifold</em> (Blender 4.5+) se usa automáticamente, <em>Exact</em> como alternativa",
      ],
    },
    limits: {
      title: "Limitaciones conocidas",
      items: [
        "Las mallas abiertas, auto-intersectadas o rotas dan booleanos incorrectos — ejecuta <em>Check Mesh</em> antes.",
        "No es un analizador de imprimibilidad: el grosor de pared, la orientación, los soportes y las tolerancias corren de tu cuenta.",
        "Los conectores son rígidos por diseño; no hay articulaciones ni uniones móviles.",
        "Las sugerencias automáticas de corte según el tamaño de la cama están en la hoja de ruta, todavía no disponibles.",
      ],
    },
  },

  install: {
    eyebrow: "Instalación",
    title: "Instálalo en menos de un minuto",
    steps: [
      "<strong>Descarga</strong> <code>easy_slice_print-{version}.zip</code> aquí abajo.",
      "En Blender abre <strong>Edit → Preferences → Add-ons</strong>, haz clic en el menú <strong>⌄</strong> de la esquina superior derecha, elige <strong>Install from Disk…</strong> y selecciona el zip.",
      "Activa <strong>{name}</strong>.",
      "Pulsa <kbd>N</kbd> en el 3D Viewport: el panel está en la pestaña <strong>EasySlice</strong> de la barra lateral.",
    ],
    quickstart: {
      title: "Inicio rápido",
      steps: [
        "Usa una escena en milímetros o marca <em>Preferences → EasySlice → Units → 1 unit = 1 mm</em>.",
        "Selecciona una malla cerrada y aplica escala y rotación (<kbd>Ctrl</kbd>+<kbd>A</kbd>). Si tienes dudas, ejecuta <em>Check Mesh</em>.",
        "Elige <strong>Quick Cut</strong> o <strong>Plan Mode</strong>, haz clic en <strong>Plane</strong>, <strong>Curve</strong> o <strong>Freehand</strong> y dibuja.",
        "Define la forma del conector, el tamaño, el lado del pin, el cut gap y la holgura.",
        "<strong>Build</strong>, comprueba el ajuste en <strong>Exploded View</strong>, <strong>Export</strong>.",
      ],
      note: "La holgura depende de cada impresora (0,15–0,4 mm es lo habitual). Imprime primero una pieza pequeña de prueba.",
    },
  },

  download: {
    eyebrow: "Descargar",
    body: "Gratis, sin cuenta, sin clave de licencia. El zip se instala directamente en Blender. El código fuente, las incidencias y las versiones anteriores están en GitHub.",
    releases: "Todas las versiones",
    changelog: "Changelog",
    extension: "Blender Extensions",
    note: "También en la <a href=\"{extensionUrl}\" target=\"_blank\" rel=\"noopener\">plataforma Blender Extensions</a>: en cuanto pase la revisión podrás instalarlo y actualizarlo desde <em>Preferences → Get Extensions</em>.",
    meta: {
      version: "Versión",
      blender: "Blender",
      platforms: "Plataformas",
      platformsValue: "Windows · macOS · Linux",
      license: "Licencia",
      price: "Precio",
      priceValue: "Gratis",
    },
  },

  faq: {
    eyebrow: "FAQ",
    title: "Preguntas y respuestas",
    items: [
      {
        q: "¿De verdad es gratis?",
        a: "Sí. {name} es software libre bajo la GNU GPL v3.0 o posterior: úsalo, estúdialo, modifícalo y compártelo, también con fines comerciales, siempre que las obras derivadas conserven la misma licencia.",
      },
      {
        q: "¿Qué versiones de Blender son compatibles?",
        a: "De Blender {blenderMin} a {blenderMax}. La batería de pruebas se ejecuta headless en ambos extremos LTS en cada commit. Windows, macOS y Linux.",
      },
      {
        q: "¿Modifica mi modelo original?",
        a: "En Plan Mode no. Los cortes se guardan como registros y solo se ejecutan al pulsar <strong>Build</strong>; el objeto de origen se conserva en una colección oculta <code>ESP_Backup</code> cuando <em>Keep Original</em> está activo. <strong>Back to Plan</strong> restaura el borrador en cualquier momento.",
      },
      {
        q: "¿Qué holgura debo usar en los conectores?",
        a: "Depende de tu impresora, del material y del slicer. De 0,15 a 0,4 mm cubre la mayoría de equipos FDM; las impresoras de resina admiten menos. Imprime primero un par de prueba pequeño — un pin cónico es la forma más tolerante.",
      },
      {
        q: "¿Puedo usar mis propias formas de conector?",
        a: "Sí. Abre la biblioteca de conectores (el icono junto a <em>Shape</em>), añade cualquier malla rígida a la colección <code>ESP_Connectors</code> siguiendo la convención de la caja unitaria y aparecerá en el menú Shape.",
      },
      {
        q: "¿Y las articulaciones o las rótulas?",
        a: "Quedan fuera del alcance por diseño: los conectores son pins y hembras rígidos para pegar o encajar a presión las piezas.",
      },
      {
        q: "Mi corte falla o da un resultado extraño.",
        a: "Las operaciones booleanas necesitan una malla cerrada, manifold y con la escala aplicada. Ejecuta <em>Check Mesh</em> antes. Las mallas muy densas tardan más; el solver <em>Manifold</em> (Blender 4.5+) se elige automáticamente cuando está disponible. Activa <em>Skip Failed Cuts</em> para seguir construyendo el resto.",
      },
    ],
  },

  support: {
    eyebrow: "Soporte y hoja de ruta",
    title: "En desarrollo activo y a la vista de todos",
    cards: {
      bug: {
        title: "¿Encontraste un error?",
        body: "Abre una incidencia con tu versión de Blender y, si puedes, el archivo .blend. Los cierres inesperados y los cortes incorrectos tienen prioridad.",
        link: "Reportar en GitHub →",
      },
      feature: {
        title: "¿Quieres una función?",
        body: "Las sugerencias de corte según el tamaño de la cama son lo siguiente en la lista. Vota, comenta o propón la tuya en el tracker.",
        link: "Pedir una función →",
      },
      contribute: {
        title: "¿Quieres contribuir?",
        body: "Núcleo de pura geometría, pruebas headless en dos versiones de Blender, Python formateado con ruff. Los pull requests son bienvenidos.",
        link: "Leer la guía →",
      },
    },
  },

  footer: {
    legal:
      "Software libre bajo la GNU GPL v3.0 o posterior. {name} es un proyecto independiente: no está afiliado a ningún add-on comercial, ni respaldado ni derivado de él, y no incluye código ni recursos de terceros.",
    project: {
      title: "Proyecto",
      source: "Código fuente",
      releases: "Versiones",
      extension: "Blender Extensions",
      changelog: "Changelog",
      license: "Licencia",
    },
    docs: {
      title: "Documentación",
      architecture: "Arquitectura",
      features: "Mapa de funciones",
      contributing: "Cómo contribuir",
      readme: "README (inglés)",
    },
    help: {
      title: "Ayuda",
      bug: "Reportar un error",
      feature: "Pedir una función",
      discussions: "Discusiones",
      security: "Política de seguridad",
    },
    copyright:
      "© {year} {author} y los colaboradores de {name} · Blender es una marca registrada de la Blender Foundation.",
  },

  notFound: {
    title: "Página no encontrada — {name}",
    code: "404",
    heading: "Esa página quedó cortada.",
    body: "Aquí no hay nada, pero los conectores siguen encajando.",
    cta: "Volver al inicio",
  },

  media: {
    badgeVideo: "Vídeo de demostración muy pronto",
    badgeImage: "Captura de pantalla muy pronto",
    hero: {
      alt: "Demostración de {name}: cortes de plano en las patas de un caballo de carrusel y un corte en curva en la cabeza, construidos en piezas y separados",
      expects: "Grabación de pantalla de 20–40 s: dibujar un corte Freehand → Build → Exploded View → Export",
    },
    stepCut: {
      alt: "Viewport mientras se dibuja una línea de corte sobre el modelo",
      expects: "Viewport a media línea, con la superposición del corte visible",
    },
    stepConnectors: {
      alt: "Piezas construidas en vista explosionada mostrando el pin y la hembra",
      expects: "Piezas construidas en Exploded View, con el pin y la hembra a la vista",
    },
    stepExport: {
      alt: "Panel de exportación con las piezas escritas como archivos STL",
      expects: "Panel de exportación con la carpeta y el formato, y las piezas exportadas en el slicer",
    },
    planeCut: {
      alt: "Plane cut: arrastrando una línea sobre un modelo en Plan Mode",
      expects: "Plan Mode: arrastrar un corte Plane y luego Edit Cut Surface y mover el plano con G/R",
    },
    curveCut: {
      alt: "Curve cut: una línea curva dibujada en la cola de un caballo de carrusel, que sale como pieza aparte",
      expects: "Plan Mode: dibujar un corte Curve cruzando la silueta y arrastrar algunos puntos de control",
    },
    freehandCut: {
      alt: "Freehand cut: dibujando un lazo cerrado alrededor de un cuello mientras se orbita",
      expects: "Plan Mode: lazo Freehand alrededor de un cuello o muñeca, orbitando con MMB entre trazos",
    },
    buildExport: {
      alt: "Build, Back to Plan, Approve y Export",
      expects: "Build → aparecen las piezas → Back to Plan → ajustar → Approve → Export STL",
    },
    quickCut: {
      alt: "Quick Cut: un corte de plano con conector automático, sin historial",
      expects: "Modo Quick Cut: un arrastre y las piezas y el conector aparecen al instante",
    },
    connectors: {
      alt: "Formas de conector: cilindro, cónico, hexágono, caja y una malla propia",
      expects: "Primer plano de las cinco formas de conector una al lado de la otra, con pins y hembras",
    },
  },
};

export default es;
