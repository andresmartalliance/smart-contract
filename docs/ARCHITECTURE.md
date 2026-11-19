# Smart Contract V5.6 — Arquitectura integral y estado real

## Objetivo de producto
Plataforma SaaS multiempresa de workflows contractuales dinámicos, con bibliotecas de campos, bloques, políticas, reglas, cálculos y plantillas. Contratación de la red prestadora es el primer caso: no es una limitación de diseño. Las modalidades se registran como datos, nunca como condicionales de implementación codificados para evento, cápita, PGP u otra modalidad.

## Usuarios y separación de responsabilidades
- **Configurador:** diseña y modifica flujos, define políticas y reglas, compara versiones y solicita publicación.
- **Operador:** tramita expedientes y tareas con permisos granulares para Jurídica, Red, Financiera, Técnica, Actuarial y aprobadores.
El frontend V5.5 es un editor local público y todavía NO aplica permisos de usuario; el backend sí exige JWT + membresía de tenant. No conectar el editor a operaciones reales sin identidad segura.

## Multiempresa
Cada institución se asocia a `tenant_id`, todos los endpoints actuales resuelven la membresía en el backend, y los registros se filtran por tenant. La capa definitiva requiere además RLS PostgreSQL, almacenamiento segregado, logs y jobs tenant-aware, pruebas adversariales de autorización y aislamiento del conocimiento de MAIRA. Los documentos, tarifas y manuales pertenecen al cliente y jamás se convierten automáticamente en biblioteca global.

## Workflow core
- Esquema declarativo: `key`, `name`, `modality_key` libre, `nodes`, `edges`, `metadata`.
- Nodos: tipo, rol, política, habilitado, condición DSL, configuraciones y campos.
- Enlaces: dependencias con condición de ejecución opcional, soportando bifurcación y paralelismo por grafo.
- Restricciones: un inicio, una o más finalizaciones, DAG sin ciclos, todos los nodos alcanzables desde inicio y capaces de alcanzar un final, roles en aprobaciones, requisitos protegidos no apagables.
- Políticas: `LEGAL_LOCKED`, `ORG_REQUIRED`, `CONDITIONAL`, `OPTIONAL`; este editor no puede rebajar directamente la protección de una etapa existente. En producción el bloqueo se deberá cotejar con una biblioteca jurídica institucional firmada, no solo con el JSON del cliente.
- Validación local + backend con control de identidad. Simulación local con datos de ejemplo y reglas conocidas. El simulador no toma decisiones jurídicas ni ejecuta tareas.
- Borrador local: localStorage y JSON. **No** publicación ni persistencia institucional en frontend; un mismo navegador puede recuperar su borrador, pero no hay colaboración ni control de acceso allí.
- Las posiciones del grafo viven en `config.position`. Los campos propios usan `config.fields`, preparados para renderización futura de formularios sin pantallas dedicadas.

## MAIRA
MAIRA será el agente contractual para proponer flujos, recuperar políticas, analizar documentos, diligenciar minutas y orientar cada tarea. Se ejecutará con herramientas backend por tenant, auditoría y permisos. La interfaz actual comunica que Gemini no está conectado: no hay simulación engañosa de agente ni autonomía de publicación.

## Conocimiento y activos reutilizables
Smart puede reutilizar componentes, esquemas y plantillas genéricas de su propiedad. Los manuales institucionales, negociaciones, notas técnicas, tarifas, expedientes y comentarios son privados. MAIRA solo podrá convertir hallazgos en propuestas versionadas; un responsable autorizado decide si aplicarlas.

## Infraestructura y continuidad
GitHub privado `andresmartalliance/smart-contract` rama `main`, Railway `smart-contract` ambiente `development`, `api`, `web`, `Postgres`. El documento maestro de continuidad de Drive se actualiza **integralmente** tras cada paquete. Una release = mismo commit/código/reglas/API/frontend + pruebas + estado verificado. Evitar commits aislados y despliegues automáticos innecesarios. Los conectores de ChatGPT tienen permisos más amplios que estos recursos; operar exclusivamente dentro del proyecto conforme a la política documentada.

## Corrección visual V5.6 — Emblema y paleta MAIRA

Se conserva el gradiente original aprobado del Resumen `linear-gradient(114deg,#10223f,#153968 70%,#164578)`. La forma cuadrada superpuesta y rotulada SMART fue sustituida por emblema circular MAIRA / AI AGENT centrado dentro de los anillos. Los chips exteriores fueron reubicados y el CSS responsive mantiene la forma circular. El panel principal de identidad MAIRA también usa esta familia de azules en lugar del azul verdoso de V5.5.

Sin cambios en flujos, motor de reglas, integraciones, autenticación, backend, SQL ni políticas multiempresa. Se verificará compilación TypeScript/Vite y estado Railway; la prueba visual en navegador sigue pendiente.

## Identidad del agente MAIRA — V5.5

**MAIRA** es un acrónimo de marca: **Multi-tenant AI for Intelligent Review & Agreements**. El descriptor oficial es **Contract Intelligence Agent** y su explicación en español es **Inteligencia artificial multiempresa para revisión inteligente y acuerdos contractuales**.

La identidad visual retoma el lenguaje de NORA como referencia de agente, pero mantiene la paleta propia de Smart Contract: azul profundo y cian. La pantalla principal presenta un emblema MAIRA con círculos concéntricos, el acrónimo completo en inglés y su explicación en español; también se muestran en el panel flotante global y el bloque MAIRA del Resumen. Se conservaron los controles de contexto/acciones locales de V5.4, sin nuevas dependencias ni backend.

El acrónimo no supone que exista una IA activa: Gemini sigue sin conectarse; la interfaz lo indica de forma explícita. No existen inferencias de IA, revisión automatizada de contratos ni conocimiento multiempresa compartido. La separación de conocimiento y los permisos por tenant siguen siendo requisitos pendientes para el uso institucional.

**Verificación:** frontend Vue-tsc + Vite compiló y se desplegó en Railway sobre commit de código `877c27498b25b7110b7822c3ee3758b6dbdf4b3b`; web/API/Postgres figuran online y sin alertas. API omitió despliegue por watch patterns. No hubo pruebas E2E visuales independientes; la captura de referencia NORA es una guía estética, no un recurso externo incrustado.

## MAIRA contextual y persistente V5.4

MAIRA aparece mediante un botón flotante persistente en todo el producto, sin interferir con navegación ni con el Workflow Studio. Un panel a la derecha muestra el módulo actual, el flujo y la etapa seleccionada cuando aplica, métricas locales del borrador y acciones disponibles.

Las acciones expuestas en V5.4 invocan las funciones existentes del editor local (validar, simular, insertar aprobación, exportar JSON y navegar); **no** usan IA generativa ni escriben en el servidor. El panel muestra Gemini no conectado y tampoco ejecuta contratos, aprobaciones institucionales o acceso a documentos.

La futura integración con Gemini utilizará herramientas backend con autorización tenant, auditoría y publicación humana. El panel es el punto de entrada global a ese agente, no un sustituto de la política de permisos.

Los servicios Railway ahora utilizan watch patterns /web/** y /api/** para evitar despliegues automáticos por modificaciones documentales y por cambios del otro servicio. Son ajustes de despliegue, no separación de la base ni infraestructura adicional.

## Diseño visual V5.3 (capa transversal)

Diseño light-premium de Smart: superficies casi blancas, azul profundo, acentos cian/violeta discretos, jerarquía tipográfica, bordes y sombras ligeras. La identidad del producto se mantiene institucional, no videojuego.

- Pantalla Resumen: hero ejecutivo, cuatro métricas provenientes exclusivamente del borrador local (etapas, activas, conexiones y pasos protegidos), proceso actual y estado de MAIRA.
- Workflow Studio: bloques categorizados, nodos diferenciados por tipo en el canvas, panel de propiedades más legible, barra de acciones real (nuevo/importar/exportar), estados visuales y simulación.
- MAIRA: identidad diferenciada y capacidades expresadas en futuro, sin botones que pretendan ejecutar Gemini.
- Navegación: iconos vectoriales internos (sin librerías ni solicitudes externas), estado Development y layout responsive. Foco visible y ajuste de animaciones por preferencia de accesibilidad.
- No se han incorporado funciones contractuales nuevas ni permisos especiales. Todo el guardado sigue siendo local en navegador; no se procesan documentos ni datos reales.

## Estado de entrega V5.5
**Incluye:** editor visual funcional con bloqueos locales, formularios configurables, responsables, conexiones condicionadas, validación, simulación, importación/exportación y recuperación local; backend validado con 14 pruebas de motor y aislamiento.
**No incluye:** Google OAuth; escritura institucional desde navegador; publicación; RLS; integración Gemini; ejecución real de contratos; SIIFA/REPS; matriz de procesos de Famisanar; verificación jurídica de plantillas específicas.
**Antes de prometer MVP:** construir sesión, controles backend/RLS, biblioteca persistente y versionada, publicación formal, expediente operativo y MAIRA; luego probar rutas institucionales reales.
