# Luthier

`Luthier` es el MVP inicial de `skill-auditor`: una herramienta para auditar skills de agentes con analisis estatico, contratos desacoplados del runtime y salidas utiles para humanos y CI.

## Estado

Hoy el proyecto ya puede:

- Descubrir skills desde carpetas o archivos individuales.
- Leer `SKILL.md` y `AGENTS.md`, incluso cuando conviven en la misma carpeta.
- Calcular metricas objetivas sobre descripcion, tamaño, restricciones, ejemplos y costo de contexto.
- Detectar findings estaticos de calidad, portabilidad y mantenibilidad.
- Detectar conflictos entre skills y rankearlos con `priority` y `recommendation`.
- Generar `report.json`, `report.md` y `summary.txt`.

El analisis LLM todavia esta reservado como expansion posterior. La base ya incluye el contrato `LLMAdapter`, pero el flujo actual funciona completamente sin proveedor externo.

## Estructura

```text
cli/         Entrada de linea de comandos
core/        Descubrimiento, parser, metricas, reglas, scoring y reportes
adapters/    Contratos para integraciones opcionales con LLMs
policies/    Policy packs y señales por familia de modelos
prompts/     Lugar reservado para prompts versionados
schemas/     Schemas JSON de entrada y salida
fixtures/    Skills de ejemplo para pruebas
tests/       Suite de tests
```

## Requisitos

- `Python 3.11+`

## Instalacion

Modo editable:

```bash
python3 -m pip install -e .
```

Sin instalar el paquete, tambien se puede ejecutar con:

```bash
python3 -m cli.main --help
```

## Uso rapido

Auditar una carpeta:

```bash
python3 -m cli.main audit fixtures --output-dir out
```

Auditar un skill individual:

```bash
python3 -m cli.main audit fixtures/simple_skill --output-dir out
```

Comparar conflictos entre skills:

```bash
python3 -m cli.main conflicts fixtures --output-dir out
```

Comparar un subconjunto explicito:

```bash
python3 -m cli.main conflicts fixtures \
  --skills simple_skill,conflicting_skill \
  --output-dir out
```

Fallar en CI si algun skill supera un umbral de riesgo:

```bash
python3 -m cli.main audit fixtures \
  --fail-on-threshold 7 \
  --output-dir out
```

## Flags principales

### `audit`

- `path`: archivo o carpeta a auditar.
- `--profile`: perfil JSON opcional.
- `--format`: formatos de salida separados por coma. Soporta `json`, `md`, `txt`.
- `--output-dir`: carpeta destino.
- `--fail-on-threshold`: devuelve exit code `2` si algun risk score supera el umbral.

### `conflicts`

- `path`: carpeta con skills a comparar.
- `--profile`: perfil JSON opcional.
- `--format`: formatos de salida separados por coma.
- `--output-dir`: carpeta destino.
- `--skills`: lista separada por coma para comparar un conjunto explicito.

## Perfil de evaluacion

El auditor acepta un perfil JSON para contextualizar el analisis. Hay un ejemplo base en [profile.example.json](/mnt/ssd_storage/ParaAgentes/Luthier/profile.example.json).

Campos actuales:

- `language`
- `shell`
- `operating_system`
- `network_access`
- `approval_mode`
- `policy_pack`
- `agent_runtime`
- `model_family`

Si no se pasa `--profile`, se usa un perfil local por defecto.

## Salidas

Cada corrida puede generar:

- `report.json`: salida estructurada estable para automatizacion.
- `report.md`: reporte legible para revision humana.
- `summary.txt`: resumen breve, amigable para CI y scripts.

En modo `conflicts`, cada conflicto incluye:

- `severity`
- `category`
- `evidence`
- `priority`
- `recommendation`

## Qué analiza hoy

Ejemplos de findings individuales ya implementados:

- Descripciones demasiado largas o demasiado vagas.
- Referencias a archivos faltantes.
- Instrucciones especificas de una plataforma cuando el perfil no coincide.
- Mezcla innecesaria de idiomas.
- Exceso de restricciones.
- Flujo sobreespecificado.
- Forcing rigido de herramientas o secuencias.
- Duplicacion interna de instrucciones.
- Desbalance entre longitud y valor operativo.

Ejemplos de conflictos entre skills:

- Shell u OS incompatibles.
- Politicas opuestas sobre preguntas de seguimiento.
- Politicas opuestas sobre navegacion web.
- Herramientas requeridas vs prohibidas.
- Overlap textual o estructural.
- Casos de `misleading-discovery` cuando dos skills se pisan y su descripcion puede inducir una seleccion equivocada.

## Tests

Ejecutar la suite:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Roadmap corto

Los siguientes pasos mas naturales del MVP son:

1. Agregar mas filtros y ranking al modo `conflicts`.
2. Incorporar el comando `report`.
3. Endurecer CI con schema validation, lint y thresholds.
4. Expandir policy packs.
5. Sumar un primer adaptador LLM end-to-end.

## Desarrollo

El estado detallado de implementacion esta en [PLAN.md](/mnt/ssd_storage/ParaAgentes/Luthier/PLAN.md).
