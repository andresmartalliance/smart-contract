# Smart Contract V5.2 — Arquitectura integral y estado real

## Objetivo de producto
Plataforma SaaS multiempresa de workflows contractuales dinámicos, con bibliotecas de campos, bloques, políticas, reglas, cálculos y plantillas. Contratación de la red prestadora es el primer caso: no es una limitación de diseño. Las modalidades se registran como datos, nunca como condicionales de implementación codificados para evento, cápita, PGP u otra modalidad.

## Usuarios y separación de responsabilidades
- **Configurador:** diseña y modifica flujos, define políticas y reglas, compara versiones y solicita publicación.
- **Operador:** tramita expedientes y tareas con permisos granulares para Jurídica, Red, Financiera, Técnica, Actuarial y aprobadores.
El frontend V5.2 es un editor local público y todavía NO aplica permisos de usuario; el backend sí exige JWT + membresía de tenant. No conectar el editor a operaciones reales sin identidad segura.

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

## Estado de entrega V5.2
**Incluye:** editor visual funcional con bloqueos locales, formularios configurables, responsables, conexiones condicionadas, validación, simulación, importación/exportación y recuperación local; backend validado con 14 pruebas de motor y aislamiento.
**No incluye:** Google OAuth; escritura institucional desde navegador; publicación; RLS; integración Gemini; ejecución real de contratos; SIIFA/REPS; matriz de procesos de Famisanar; verificación jurídica de plantillas específicas.
**Antes de prometer MVP:** construir sesión, controles backend/RLS, biblioteca persistente y versionada, publicación formal, expediente operativo y MAIRA; luego probar rutas institucionales reales.
