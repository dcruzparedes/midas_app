# AGENTS.md — MIDAS App

## Resumen del proyecto

`midas_app` es una app de Frappe/ERPNext para **Corporación Midas**. Su objetivo es
automatizar la generación de **propuestas de sistemas solares fotovoltaicos** (modelo EPC:
Ingeniería, Procura y Construcción).

Flujo de trabajo:

1. El usuario captura la información clave de la propuesta en una **cotización (Quotation)**.
2. Un Doctype dedicado (`Propuesta Solar`) almacena el documento formateado de la propuesta.
3. Un conjunto de **fórmulas** calcula los resultados (potencia, ahorro, inversión, retorno, etc.).
4. Un **Print Format** (Jinja/HTML) genera el PDF de la propuesta.

## Stack y versiones

- Frappe: `17.0.0-dev` (rama de desarrollo)
- ERPNext: `16.32.0` (`version-16`)
- Python >= 3.10
- Bench ubicado en `/home/daniel/frappe-bench` (entorno WSL Ubuntu)

> **Ojo:** hay desalineación de versiones (Frappe 17 dev + ERPNext 16). Verificar antes de
> migraciones que no cause conflictos.

## Comandos útiles

El bench corre dentro de WSL. Desde PowerShell usar `wsl`:

```powershell
wsl -e bash -c "cd /home/daniel/frappe-bench && bench --site midas.local migrate"
wsl -e bash -c "cd /home/daniel/frappe-bench && bench start"
wsl -e bash -c "cd /home/daniel/frappe-bench && bench --site midas.local run-tests --app midas_app"
```

Exportar/importar fixtures (Custom Fields, Property Setters, etc.):

```bash
bench --site midas.local export-fixtures
```

## Estructura

```
apps/midas_app/
├── midas_app/
│   ├── hooks.py                 # configuración de la app (fixtures, eventos)
│   ├── modules.txt              # módulo: MIDAS
│   ├── config/                  # config del escritorio (__init__.py)
│   ├── fixtures/                # custom_field.json, property_setter.json, etc.
│   ├── patches/                 # patches de migración
│   ├── midas/
│   │   └── doctype/             # Doctypes (propuesta_solar_test, ...)
│   ├── public/                  # assets estáticos
│   └── templates/               # plantillas
├── pyproject.toml
└── README.md
```

> Nota: `modules.txt` declara el módulo como `MIDAS` pero la carpeta es `midas` (minúsculas).
> Inconsistencia existente; respetar salvo corrección explícita.

## Convenciones de código

Definidas en `pyproject.toml` (ruff):
- `line-length = 110`
- Indentación con **tabs** (indent-style = "tab")
- Doble comilla (`quote-style = "double"`)
- Se aplica `ruff`, `eslint`, `prettier` y `pyupgrade` vía `pre-commit`

## Documento de referencia

La propuesta de referencia está en el equipo local:

- `C:\Users\danie\Desktop\DevOps\Proyecto\Automatización de oferta.docx` — formato de la oferta.
- `C:\Users\danie\Desktop\DevOps\Proyecto\Calculos para Página Daniel.xlsx` — fórmulas de cálculo.

La empresa que firma las propuestas es **Corporación Midas** (aunque el docx de ejemplo
referencie a "Elite Energy Solutions").

## Estado actual / tareas pendientes

- [x] Añadir Custom Fields a `Quotation` para capturar datos clave de la propuesta.
- [x] Crear Doctype `Propuesta Solar` (reemplaza `Propuesta Solar Test`).
- [x] Implementar fórmulas de cálculo en el controller Python.
- [x] Crear Print Format (Jinja/HTML) para generar el PDF.
- [x] Patch para eliminar el placeholder `Propuesta Solar Test`.
- [x] `bench migrate` y verificación.

Pendientes (fases futuras):
- [ ] Añadir gráficas (resultados técnicos/financieros) al Print Format (el logo ya está: `public/images/logo_midas.jpg`).
- [ ] Modelo financiero avanzado (VPN, TIR, inyección/autoconsumo) pendiente de fórmulas.
- [ ] Conectar los campos calculados de `Quotation` con las mismas fórmulas.
