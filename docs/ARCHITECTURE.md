# Smart Contract V5.1 — Arquitectura congelada para el primer desarrollo

## Producto

SaaS multiempresa de workflows contractuales dinámicos, con biblioteca de campos, bloques, reglas, fórmulas y plantillas. Modalidades de pago como datos y componentes contractuales, nunca como un `if modalidad == ...`. Primer contexto: red prestadora EPS; Famisanar es caso de uso potencial, no cliente confirmado de la aplicación ni tenant real configurado.

## Usuarios

Dos experiencias: Configurador (diseño, validación y propuestas de flujos) y Operador (expedientes y tareas). Permisos granulares para Jurídica, Técnica, Financiera, Red, Actuarial, Aprobaciones; la separación de funciones prevalece sobre las etiquetas de interfaz.

## Multiempresa

Cada entidad posee `tenant_id` y todas las definiciones y expedientes se consultan desde identidad autenticada y membresía real. Baseline en API filtra por tenant; para producción exige complementar con PostgreSQL RLS, pruebas adversariales, consultas de jobs y almacenamiento con namespaces por empresa. Los datos y el conocimiento de una entidad no son biblioteca global por defecto.

## Motor

DSL declarativo validado, grafo DAG, checks de nodos obligatorios, referencias, topología y roles; condiciones desconocidas nunca son aprobadas. La simulación inicial es conservadora y **no ejecuta decisiones jurídicas**. Faltan rutas avanzadas (split/join expresivo, subprocesos, excepciones y migraciones), almacenamiento seguro de borradores y publicaciones aprobadas.

## MAIRA

Agente con herramientas de dominio: consulta expediente, extrae documentos, propone reglas y workflows, analiza cambios y prepara minutas. Cada acción entra por backend, validación de permiso, auditoría y aprobación para mutaciones importantes. Este primer paquete no simula inteligencia artificial: su endpoint declara que aún está desactivada.

## Knowledge asset

Plantillas y reglas reutilizables de Smart pueden estar en biblioteca central. Manuales, contratos, tarifas, notas técnicas, notas de revisión y documentos de clientes son privados por tenant; no exportar ni compartir automáticamente. Futura recomendación a otros tenants solo a partir de conocimiento explícitamente autorizado y anonimizado cuando corresponda.

## Continudad sin parches acumulados

Una release es un estado autocontenido: código integrado, migraciones, pruebas, manifiesto, estado Railway y **un solo documento maestro vigente en Drive**, actualizado en todas sus secciones. Snapshots previos son históricos. Nunca afirmar funcionalidades inexistentes; verificar cada hito con pruebas y readback. Los cambios pequeños pueden realizarse internamente, pero se consolidan y validan en una entrega integral.

## Pendientes prioritarios

1. Habilitar acceso de la integración GitHub al repositorio `andresmartalliance/smart-contract`.
2. Subir base y confirmar CI, dependencias, licencias y seguridad.
3. Conectar Railway Development y servicios; verificar migraciones y health checks.
4. Implementar OAuth Google real, RLS PostgreSQL, gestor de tenants, expedientes y auditoría avanzada.
5. Editor Vue Flow persistente conectado a API; versionado, aprobación de publicación y generador de formularios.
6. Conectar MAIRA + Gemini con reglas y permisos, evaluación de documentos y propuestas de flujos.
7. Ingresar workflow real Famisanar, normalizar etapas y probar rutas sin codificación por modalidad.
