# PLAN

Checklist de implementación para construir `skill-auditor` como motor desacoplado del runtime, con análisis estático fuerte, análisis LLM opcional vía adaptadores y reportes útiles para humanos y CI.

## Estado actual

- Base del MVP operativa en `Python`.
- Comandos disponibles: `audit` y `conflicts`.
- Reportes disponibles: `report.json`, `report.md`, `summary.txt`.
- Descubrimiento consolidado para `SKILL.md` y `AGENTS.md` en la misma carpeta.
- Parsing estructurado básico para descripción, secciones, referencias, uso, restricciones y ejemplos.
- Cobertura de tests actual: descubrimiento, parsing básico, métricas objetivas, reglas estáticas, conflictos y serialización.

## Próximas prioridades sugeridas

1. Completar reglas estáticas pendientes: sobreespecificación, forcing rígido y duplicación interna.
2. Mejorar `conflicts` con ranking y sugerencias accionables.
3. Agregar `report` como comando explícito y flags de policy/runtime/model family.
4. Endurecer CI: schema validation, test runner y thresholds.
5. Expandir policy packs y contratos LLM sin acoplar el core.

## 0. Definición inicial

- [x] Confirmar stack del MVP.
- [x] Elegir `Python` o `TypeScript` como implementación inicial.
- [x] Mantener contratos, schemas y formatos agnósticos del runtime.
- [x] Definir alcance de la primera entrega: `audit` + reglas estáticas + reportes básicos.
- [x] Documentar supuestos operativos iniciales: SO, shell, idioma, acceso a red, modo de aprobación.

## 1. Estructura del repositorio

- [x] Crear estructura base del proyecto:

```text
skill-auditor/
  cli/
  core/
  adapters/
  policies/
  prompts/
  schemas/
  tests/
  fixtures/
```

- [x] Crear archivo de configuración de ejemplo `profile.example.json`.
- [x] Crear carpeta de fixtures con skills de prueba simples y conflictivos.
- [ ] Definir convenciones de nombres para módulos, reportes y policies.

## 2. Modelos y contratos

- [x] Definir `EvaluationProfile`.
- [x] Definir `DiscoveredSkill`.
- [x] Definir `SkillMetrics`.
- [x] Definir `Finding`.
- [x] Definir `Conflict`.
- [x] Definir `AuditReport`.
- [x] Crear schemas JSON versionados para entrada y salida.
- [x] Validar que `report.json` sea estable para automatización.

## 3. Descubrimiento e ingesta

- [x] Implementar recorrido de directorios de skills.
- [x] Detectar `SKILL.md`, `AGENTS.md` y archivos auxiliares relevantes.
- [x] Detectar scripts adjuntos por extensión y permisos.
- [x] Extraer nombre y descripción del skill.
- [x] Medir tamaño total del skill y tamaño de la descripción.
- [x] Resolver referencias internas a archivos y recursos.
- [x] Detectar señales de plataforma: shell, SO, tooling, runtime.
- [x] Normalizar la salida de descubrimiento en una estructura única.
- [x] Cubrir casos con múltiples skills por carpeta o directorios incompletos.

## 4. Parser de skills

- [x] Parsear encabezados y secciones de `SKILL.md`.
- [x] Extraer bloques de uso, restricciones, ejemplos y archivos referenciados.
- [x] Identificar lenguaje dominante y mezcla de idiomas.
- [x] Estimar tokens del contenido total y de la descripción.
- [x] Separar contenido operativo de contenido narrativo.
- [x] Tolerar formatos imperfectos sin romper el pipeline.

## 5. Métricas objetivas

- [x] Medir longitud de descripción en caracteres.
- [x] Medir longitud de descripción en tokens estimados.
- [x] Medir tamaño total de `SKILL.md`.
- [x] Contar encabezados.
- [x] Contar pasos imperativos.
- [x] Contar restricciones como `must`, `always`, `never`, `required`.
- [x] Contar ejemplos.
- [x] Contar referencias a herramientas.
- [x] Medir porcentaje estimado de contenido no operativo.
- [x] Medir densidad de instrucción.
- [x] Medir costo de contexto estimado.

## 6. Reglas estáticas de análisis individual

- [x] Detectar descripciones demasiado largas o poco discriminativas.
- [x] Detectar instrucciones vagas o demasiado genéricas.
- [x] Detectar sobreespecificación de pasos sin justificación.
- [x] Detectar forcing rígido de herramientas o secuencias.
- [x] Detectar duplicación interna de instrucciones.
- [x] Detectar referencias rotas.
- [x] Detectar scripts potencialmente no portables por SO o shell.
- [x] Detectar mezcla innecesaria de idiomas.
- [x] Detectar restricciones excesivas que reduzcan utilidad del skill.
- [x] Detectar desbalance entre longitud y valor operativo.

## 7. Scoring derivado

- [x] Calcular `discoverability score`.
- [x] Calcular `specificity score`.
- [x] Calcular `portability score`.
- [x] Calcular `maintainability score`.
- [x] Calcular `risk score`.
- [x] Calcular `context cost score`.
- [ ] Documentar cómo se calcula cada score.
- [x] Separar métricas objetivas de heurísticas ajustables.

## 8. Modo `audit`

- [x] Implementar comando para auditar una carpeta completa.
- [x] Implementar comando para auditar un skill individual.
- [x] Generar salida estructurada por skill.
- [x] Incluir findings de optimización, compatibilidad y mantenibilidad.
- [x] Incluir scorecard por skill.
- [x] Hacer que el comando acepte `--profile profile.json`.

## 9. Conflictos sin LLM

- [x] Implementar comparación entre skills por pares.
- [x] Detectar conflictos de idioma.
- [ ] Detectar conflictos de tono o rol.
- [x] Detectar conflictos sobre herramientas obligatorias/prohibidas.
- [x] Detectar conflictos sobre shell o SO.
- [x] Detectar conflictos sobre confirmaciones obligatorias vs no preguntar.
- [x] Detectar conflictos sobre navegación web obligatoria/prohibida.
- [x] Detectar solapamientos grandes por similitud textual y estructural.
- [x] Generar matriz de conflictos con severidad y evidencia.

## 10. Modo `conflicts`

- [x] Implementar comando `conflicts` para grupos de skills.
- [x] Permitir filtrar por conjunto explícito.
- [ ] Permitir filtrar por grupo o carpeta.
- [x] Rankear solapamientos por prioridad.
- [x] Sugerir cuándo fusionar, dividir o renombrar skills.
- [x] Marcar skills cuya descripción puede inducir selección errónea.

## 11. Clustering y reducción de ruido

- [ ] Implementar agrupamiento por similitud antes de comparaciones profundas.
- [ ] Limitar comparaciones exhaustivas en colecciones grandes.
- [ ] Conservar trazabilidad entre clusters y conflictos reportados.
- [ ] Preparar la base para usar clusters también en la fase con LLM.

## 12. Adaptadores de LLM

- [x] Definir interfaz común `LLMAdapter`.
- [x] Definir contrato de entrada para prompts estructurados.
- [ ] Definir contrato de salida con findings, evidencia y severidad.
- [ ] Implementar un primer adaptador funcional end-to-end.
- [ ] Preparar adaptadores mínimos para `Codex`, `Claude Code` y `OpenCode`.
- [x] Mantener la integración opcional: el auditor debe servir sin LLM.

## 13. Prompts estructurados

- [ ] Crear prompt para auditar un skill individual.
- [ ] Crear prompt para comparar skills.
- [ ] Crear prompt para síntesis del reporte.
- [ ] Forzar formato estructurado de salida.
- [ ] Pedir evidencia explícita y resolución mínima propuesta.
- [ ] Evitar prompts libres difíciles de versionar.

## 14. Policy packs

- [x] Crear `generic-agentic` como policy pack base.
- [ ] Crear `openai-gpt5`.
- [ ] Crear `claude-4x`.
- [x] Definir señales positivas por familia de modelos.
- [x] Definir señales negativas por familia de modelos.
- [ ] Definir heurísticas de scoring por policy.
- [ ] Versionar reglas y prompts por policy pack.
- [ ] Hacer que el `EvaluationProfile` seleccione policy pack automáticamente o por override.

## 15. Reportes

- [x] Generar `report.json`.
- [x] Generar `report.md`.
- [x] Generar `summary.txt`.
- [x] Incluir perfil de evaluación en la salida.
- [x] Incluir skills auditados con métricas, findings y scores.
- [x] Incluir conflictos cruzados con severidad y evidencia.
- [x] Mantener compatibilidad de `report.json` con CI y tooling externo.

## 16. CLI y experiencia de uso

- [x] Diseñar comando base `skill-auditor audit <path> --profile profile.json`.
- [x] Diseñar comando base `skill-auditor conflicts <path> --profile profile.json`.
- [ ] Diseñar comando base `skill-auditor report <path> --format md,json`.
- [ ] Definir flags para activar o desactivar LLM.
- [ ] Definir flags para elegir `model_family`, `agent_runtime` y `policy`.
- [x] Definir códigos de salida claros.
- [x] Agregar `--fail-on-threshold` para uso en CI.

## 17. Testing

- [x] Crear fixtures de skills válidos, débiles y conflictivos.
- [x] Cubrir descubrimiento e ingesta.
- [x] Cubrir parsing de `SKILL.md`.
- [x] Cubrir métricas objetivas.
- [x] Cubrir reglas estáticas individuales.
- [x] Cubrir conflictos rule-based.
- [x] Cubrir serialización del reporte.
- [ ] Cubrir selección de policy packs por perfil.
- [ ] Cubrir adaptadores con mocks.

## 18. CI y endurecimiento

- [ ] Agregar validación de schemas.
- [ ] Agregar ejecución de tests.
- [ ] Agregar lint/format.
- [ ] Publicar artefactos de reporte en CI.
- [ ] Soportar thresholds que fallen el pipeline.
- [ ] Agregar diff entre versiones de skills o snapshots.

## 19. Documentación

- [ ] Documentar la arquitectura por capas.
- [ ] Documentar el `evaluation-profile`.
- [ ] Documentar formato de salida y campos del JSON.
- [ ] Documentar criterios de scoring.
- [ ] Documentar limitaciones del análisis estático.
- [ ] Documentar cuándo conviene activar el análisis con LLM.

## 20. Criterio de MVP

- [x] Descubre skills desde archivos externos sin acoplarse al runtime.
- [x] Audita skills individuales con métricas y reglas estáticas.
- [x] Detecta conflictos simples entre skills.
- [x] Produce `report.json`, `report.md` y `summary.txt`.
- [x] Usa `profile.json` para contextualizar el análisis.
- [x] Funciona sin LLM y puede ampliarse con adaptadores.

## 21. Post-MVP

- [ ] Mejorar similitud semántica con embeddings o clustering más rico.
- [ ] Agregar más policies por familia/modelo.
- [ ] Agregar recomendaciones automáticas de reescritura.
- [ ] Agregar diff de calidad entre versiones de un mismo skill.
- [ ] Evaluar una segunda implementación del CLI si se justifica por portabilidad.
