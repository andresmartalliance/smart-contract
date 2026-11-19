# Smart Contract + MAIRA

**V6.3 — Gestión Contractual + Mi Contratación · piloto de doble portal · Development**

Smart Contract es una plataforma SaaS multiempresa con motor declarativo de workflows de contratación, campos, políticas y modalidades configurables. La primera aplicación es contratación de red prestadora de salud, sin codificar PGP, cápita ni evento como flujos obligatorios. El workflow institucional de Famisanar aún no ha sido recibido y no forma parte de esta versión.

## V6.3 — Piloto funcional entre contratante y contratista

El mismo frontend ofrece **Gestión Contractual** (institución que contrata) y **Mi Contratación** (persona natural, proveedor o IPS invitada). No hay dos apps ni otro entorno. Ambos utilizan Google Sign-In, mismo backend FastAPI y PostgreSQL, con autorizaciones distintas en cada solicitud.

Recorrido para la primera prueba con **información ficticia**:

1. Ingresar a Smart Contract con el correo habilitado para administrar el piloto (`andres@wearesmart.co`). El primer acceso permite crear el espacio ficticio desde **Gestión Contractual** si la cuenta todavía no tiene institución.
2. Abrir **Flujos → Ejemplo de doble portal**. El ejemplo incluye Inicio → Datos del contratista (formulario dinámico) → Revisión interna (aprobación simulada de trámite) → Fin. El configurador puede cambiar responsables y la parte que ejecuta cada etapa.
3. Seleccionar **Publicar plantilla de prueba**. Esta versión se persiste en PostgreSQL y no es una aprobación jurídica.
4. En **Gestión Contractual**, crear un expediente con nombre, correo invitado y tipo de persona (natural o jurídica). La aplicación concede acceso al correo designado; **no envía email**. Copiar y compartir manualmente el enlace.
5. Abrir una sesión separada del navegador con la cuenta Google invitada (debe ser usuaria de prueba en Google Auth Platform → Audience si el OAuth sigue en Testing). En **Mi Contratación**, llenar la actividad asignada.
6. Volver a la cuenta del contratante; revisar, devolver para corregir o completar la siguiente actividad. El historial técnico queda en `audit_events` de PostgreSQL. El expediente llega al estado `COMPLETED` cuando las etapas del piloto terminan.

**Aislamiento:** la API valida el ID token Google, correo, membresía activa en la institución para acciones internas y acceso al expediente por invitación exacta para externos. Una contraparte solo recibe sus propias actividades, sin ver las respuestas internas. La interfaz oculta las secciones de configuración institucional a usuarios que solo fueron invitados. La separación se prueba desde backend con datos ficticios y no debe confundirse con RLS de PostgreSQL, que aún está pendiente.

**Limitaciones explícitas:** piloto habilitado solo en Railway Development mediante `SMART_PORTAL_DEMO_ENABLED=true` y correo administrador autorizado. El flujo de trabajo ejecutable está restringido a etapas manuales sin condiciones; se rechazan firmas, integraciones, cálculos y generación documental como si fueran operaciones realizadas. Los documentos, notificaciones de invitación y firma electrónica productiva no están implementados. Tampoco hay selección de varias instituciones para un mismo administrador, permisos institucionales completos, RLS ni pruebas con dos cuentas Google reales verificadas en navegador. No cargar datos de pacientes, contratos o clientes.

**Verificación:** GitHub Actions V6.3 aprobó 37 pruebas backend y la compilación Vue. Railway confirmó API/Web/PostgreSQL en línea con último despliegue del código V6.3 y migración Alembic 0002 configurada en preDeploy. La prueba interactiva de dos sesiones queda pendiente. Gemini aún no tiene clave configurada, por lo que MAIRA no ha interpretado documentos.

## Smart Contract V6.2 — Pantalla de acceso corporativo

- Página de acceso Google con el mismo lenguaje visual de Smart Service Desk: fondo gris claro, tarjeta blanca centrada, logotipo Smart de la referencia, título Smart Contract, texto directo y un botón auténtico Google Identity Services.
- Marca Smart con su wordmark multicolor y texto extraído y depurado de la imagen facilitada por el usuario. El logo aparece en el login y en la navegación. Se conserva el favicon azul sólido ya aprobado para el navegador.
- La interfaz no muestra el espacio de trabajo sin identidad verificada. El servidor valida el ID token de Google, la audiencia y la lista de usuarios permitidos en GET /api/v1/maira/session; la sesión del piloto se mantiene únicamente en memoria (se pierde al recargar).
- La carga con MAIRA reutiliza la sesión Google del login, sin segundo botón ni doble inicio de sesión.
- **Límite:** este login es una puerta controlada para Development y la prueba MAIRA; NO confiere roles, pertenencia a tenant, RLS ni derechos de publicación institucional. Los endpoints multiempresa existentes siguen requiriendo sus propias credenciales. Sin Gemini aún no habrá interpretación documental.

## MAIRA V6.1 — Validaciones de procedencia y borradores

- MAIRA registra el número de paso, cita original, página y confianza dentro de la configuración de cada nodo propuesto. Se muestran en **Propiedades** al seleccionar una etapa.
- La API rechaza pasos de origen duplicados, nodos con mapeos contradictorios y referencias de origen incompatibles; conserva la validación del grafo acíclico.
- **Aplicar propuesta** requiere una confirmación adicional para evitar sustituir el borrador que existe en el navegador. Si falla la validación local, restablece el estado anterior.
- El inicio de sesión Google puede prepararse cuando el cliente OAuth esté configurado aunque Gemini siga pendiente.
- GitHub Actions V6.1: 26 pruebas Python correctas y compilación Vue correcta; servicios Railway Web/API en SUCCESS. No se ha realizado la prueba de un documento real contra Gemini.

**Estado de credenciales en Railway:** la lista de prueba `SMART_MAIRA_ALLOWED_EMAILS` está configurada para `andres@wearesmart.co`. Siguen ausentes `SMART_GOOGLE_CLIENT_ID` y `SMART_GEMINI_API_KEY`. No subir claves a repositorio, Drive ni al chat. Sin esas dos configuraciones el análisis queda correctamente bloqueado.

## MAIRA V6.0 — Primera prueba de interpretación (piloto limitado)

Desde **Flujos → Crear con MAIRA** el Configurador puede seleccionar un archivo PDF, PNG, JPG o TXT (máximo 6 MB), autenticarse con una cuenta Google explícitamente permitida y solicitar que Gemini analice el documento. MAIRA propone un workflow declarativo con nodos y dependencias, una tabla de pasos originales con citas cortas, páginas, nivel de confianza y dudas para validación humana. El borrador debe revisarse antes de aplicarse al editor.

**Estado actual:** UI y API desplegadas, GitHub Actions completa (22 pruebas) y Railway API/Web SUCCESS. El cliente OAuth Google y la clave Gemini **NO** están configurados en este proyecto: el botón muestra una indicación de configuración pendiente y **no puede analizar ningún documento aún**. Esto es deliberado para no crear una carga pública de documentos. Variables requeridas en API: `SMART_GOOGLE_CLIENT_ID` (cliente OAuth Web del dominio Development), `SMART_MAIRA_ALLOWED_EMAILS` (lista de correos autorizados) y `SMART_GEMINI_API_KEY` (clave de Google AI Studio); opcional `SMART_GEMINI_MODEL` con valor predeterminado `gemini-2.5-flash`. No subir credenciales a GitHub ni a Drive.

El análisis devuelve un borrador **sin persistencia en el servidor**; el archivo se envía a Gemini con el consentimiento del usuario autenticado, la carga se limita a tipos reconocidos, validación de cabeceras y tamaño, y la propuesta se valida con el motor existente. Al aceptar, se guarda únicamente en localStorage del navegador. Solo pruebas con documentos sintéticos/autorizados; faltan RLS, gobierno del tenant, retención institucional y revisión de seguridad.

## Ajuste de identidad V5.6

- Resumen: el emblema **MAIRA / AI AGENT** reemplaza la figura cuadrada SMART; ahora es circular, centrada dentro de los anillos y sin la sensación de objeto superpuesto.
- Se conserva **exactamente** el degradado original del Resumen `#10223f → #153968 → #164578` y se aplica la misma familia cromática a la identidad de MAIRA, sustituyendo el azul verdoso previo.
- Chips externos reubicados para no tapar el emblema y ajuste responsive. Sin cambios en API, BD, flujos ni integración Gemini.

## Identidad MAIRA V5.5

Nombre de marca: **MAIRA — Multi-tenant AI for Intelligent Review & Agreements**.
Sentido operativo: inteligencia artificial multiempresa para revisión inteligente y acuerdos contractuales. Descriptor: **Contract Intelligence Agent** (agente de inteligencia contractual).

La pantalla MAIRA muestra una tarjeta de identidad azul profundo con círculos cian, la sigla visible, su significado en inglés y su traducción contextual al español, conforme a la referencia visual de NORA. El panel persistente de MAIRA y la tarjeta del Resumen también muestran el significado. No se cambia la arquitectura multiempresa ni se afirma que Gemini esté conectado.

## Qué cambia en V5.4

- Un botón MAIRA flotante visible en todas las pantallas, persistente al navegar; abre y cierra un panel lateral contextual sin bloquear el diseñador.
- El panel reconoce el módulo actual; en Flujos también reconoce el nombre y estado del borrador y la etapa seleccionada.
- Atajos reales y locales: verificar estructura, simular, agregar una aprobación y exportar JSON, además de navegación a Workflow Studio y vista MAIRA.
- El panel distingue claramente asistencia contextual local de inteligencia generativa: **Gemini aún NO está conectado**. No muestra respuestas falsas ni envía información del cliente.
- Diseño responsive, control accesible de apertura/cierre y advertencias claras sobre la ausencia de datos institucionales autenticados.
- Configuración Railway por watch paths: API /api/** y Web /web/**, para reducir compilaciones por commits exclusivamente documentales. No cambia la infraestructura.
- Las experiencias Configurador y Operador institucionales, RLS, publicación y MAIRA con Gemini siguen pendientes.

## Qué cambia en V5.3

- Sistema visual renovado, claro y futurista, sin efectos decorativos excesivos: tipografía, navegación vectorial, superficies, gradientes limitados, tarjetas y componentes unificados.
- Resumen convertido en centro de control: métricas estrictamente derivadas del borrador del navegador, acceso a Workflow Studio y estado real de MAIRA. No inventa contratos, proveedores, porcentajes ni tendencias.
- Workflow Studio con nueva jerarquía visual, biblioteca de categorías, canvas limpio, nodos identificados visualmente por su función, propiedades y conexiones más legibles.
- MAIRA tiene una pantalla de presentación propia, con cuatro capacidades planificadas, pero conserva la indicación clara de que Gemini aún NO está conectado.
- Pantallas aún no operativas mantienen estados vacíos honestos, sin datos de demostración presentados como reales.
- Diseño adaptable a pantallas medianas y móviles; foco visible y soporte de movimiento reducido.
- La navegación inicia en Resumen y abre el mismo Workflow Studio funcional de V5.2, preservando su persistencia local y JSON.
- No hay nuevas dependencias, cuentas ni servicios. No se alteraron esquemas de base de datos, API ni permisos.

## Qué funciona en V5.4

**Diseñador visual Vue 3 / Vue Flow:**

- Crear un flujo en blanco o partir de un ejemplo genérico de red prestadora.
- Insertar 14 bloques funcionales, arrastrar etapas, añadir conexiones y quitar conexiones o etapas no protegidas.
- Configurar nombres, roles abiertos, requisitos legales/institucionales/condicionales/opcionales, activación y reglas de igualdad, desigualdad, comparación, pertenencia o existencia.
- Configurar por etapa campos de formulario reutilizables (nombre, identificador, tipo y obligatoriedad), instrucciones y modo de ejecución (manual, IA asistida, API o RPA — los últimos requieren integraciones futuras).
- Validación estructural del grafo: entrada/salida, ciclos, rutas sin finalización, tareas protegidas, responsables y claves de campos.
- Simulación local con hechos JSON y lista de actividades completadas. Simulación conservadora: un dato desconocido bloquea la rama; no representa una aprobación real ni cumplimiento jurídico.
- Exportación e importación JSON compatible con el esquema FastAPI, preservando posiciones y condiciones de ruta.
- Recuperación automática del borrador en **este navegador**, usando localStorage. Es almacenamiento local, no compartido ni multiempresa. No ingresar expedientes ni datos reales de clientes.

**API FastAPI:** rutas con JWT y pertenencia al tenant, CRUD básico de borradores, validación del motor y simulación estructural. Los controles de servidor se extienden para rechazar enlaces hacia inicio/después de finalización, ramas huérfanas, aprobadores ausentes, campos duplicados y condiciones obligatorias sin regla. **La interfaz aún NO está conectada a estas rutas porque la autenticación corporativa falta.**

**Railway:** se usa el mismo proyecto `smart-contract`, ambiente `development`, con servicios `api`, `web` y `Postgres` conectados a GitHub `andresmartalliance/smart-contract` / `main`. La migración inicial Alembic se ejecuta como predeploy de API. No instalar otro ambiente de prueba.

## Qué no está operativo

- Google Sign-In y sesiones corporativas con roles Configurador/Operador.
- Persistencia institucional compartida, versionado de publicación, ejecución real de contratos y aprobaciones.
- PostgreSQL RLS, almacenamiento documental protegido por institución y auditoría productiva.
- MAIRA + Gemini; sigue en estado NO CONFIGURADO. No se simulan respuestas de IA.
- Integraciones REPS, SIIFA, ERP, firma, API y RPA.

**Restricción:** el acceso público a Development es solo para diseño con datos ficticios o plantillas genéricas. No cargar información real de IPS, documentos, contratos ni tarifas institucionales hasta implementar controles de identidad y privacidad.

## Arquitectura de código

- `api/` — FastAPI, modelos de tenants, JWT/membresía, versiones de workflows, reglas DSL, simulador, Alembic y pruebas pytest.
- `web/` — Vue 3 + Vue Flow. Visual Editor, panel de propiedades, condiciones, formularios, validación y simulación local.
- `docs/ARCHITECTURE.md` — arquitectura integral y límites de este paquete.
- `RELEASE_MANIFEST.json` — estado de verificación; la fuente de continuidad de negocio es el documento maestro de Google Drive.

## Verificación del paquete

- Backend: desde `api/`, `python -m pytest -q` — **14 pruebas** de backend superadas previamente; la capa visual conserva el mismo motor. El frontend V5.3 compila en Railway.
- Frontend: desde `web/`, `npm install && npm run build` — debe verificarse en Railway; el entorno local no pudo instalar las dependencias de npm por conectividad.
- Despliegue: GitHub hace despliegue automático de ambos servicios. Un solo commit consolidado por entrega para contener costos.
- Una release solo se cierra tras verificar despliegues, resultado de build, APIs, riesgos, actualización integral de Drive y SHA final.

## Continuidad

Repositorio privado: `andresmartalliance/smart-contract`. Proyecto Railway: `smart-contract` / `development`. Google Drive: carpeta `Smart Contract - Desarrollo y Continuidad`, documento `00 - SMART CONTRACT - CONTEXTO MAESTRO INTEGRAL - V5.4` (se actualiza al verificar el release).

El usuario autorizó trabajar únicamente en este repositorio, proyecto Railway y carpeta Drive; esa limitación es una **política de ejecución** porque los conectores tienen alcance técnico más amplio. No modificar otros productos.

Próxima versión integral: autenticación real y control multiempresa de configuración, guardado seguro de flujos, publicación con permisos, MAIRA conectada y procesamiento del workflow real cuando se reciba.

## Favicon y marca visual · V6.1.1

Smart Contract utiliza el icono aprobado del usuario: geometría abstracta de nube y tres barras ascendentes en azul sólido `#0040DB`, fondo transparente, sin degradado ni 3D. Está disponible como `web/public/favicon.svg` y `web/public/favicon-64.png`. `web/index.html` referencia SVG con respaldo PNG, y la marca de la barra lateral utiliza el mismo emblema en lugar de la S provisional. No afecta la identidad separada de MAIRA ni el backend.

Entrega funcional: commit `d15d44dae6dfaf2ca3f03810a3b0ac916549f74b`; GitHub Actions PASS y Railway Web SUCCESS, API y Postgres sin cambios. La integración Gemini continúa pendiente de credenciales propias de Smart Contract. La marca de Google Auth Platform deberá llamarse `Smart Contract` y utilizar un OAuth Web Client con origen `https://web-development-80ecf771.up.railway.app`, sin redirección, dado que la app usa Google Identity Services por callback de JavaScript.
