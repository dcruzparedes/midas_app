# AGENTS.md — MIDAS App

## Resumen del proyecto

`midas_app` es una app de Frappe/ERPNext para **Corporación Midas** que automatiza la
generación de **propuestas de sistemas solares fotovoltaicos** (modelo EPC: Ingeniería,
Procura y Construcción).

Flujo de trabajo:

1. El usuario captura la información en una **Cotización Midas** (Doctype propio `Cotizacion Midas`, NO el `Quotation` de ERPNext).
2. Desde la cotización se genera una **Propuesta Solar** (botón "Generar Propuesta Midas").
3. `midas_app/midas/solar_calc.py` calcula los resultados (potencia DC/AC, ahorro, inversión, retorno, etc.).
4. `midas_app/midas/charts.py` genera las gráficas (SVG).
5. La propuesta se exporta a **PDF** (WeasyPrint) o **Word** (python-docx) y tiene un **Print Format** (Jinja/HTML).

> Nota: la app ya **no** usa Custom Fields sobre `Quotation`. Ese enfoque fue reemplazado por
> el Doctype propio `Cotizacion Midas`. No volver a añadir Custom Fields a `Quotation`.

## Stack y versiones

- Frappe: `17.0.0-dev` (rama de desarrollo)
- ERPNext: `16.32.0` (`version-16`)
- Python >= 3.10
- Bench en `/home/daniel/frappe-bench` (WSL Ubuntu); el repo vive en `apps/midas_app/`

> **Ojo:** hay desalineación de versiones (Frappe 17 dev + ERPNext 16). Verificar antes de
> migraciones que no cause conflictos.

## Comandos

El bench corre dentro de WSL. Desde PowerShell usar `wsl`:

```powershell
wsl -e bash -c "cd /home/daniel/frappe-bench && bench --site midas.local migrate"
wsl -e bash -c "cd /home/daniel/frappe-bench && bench start"
wsl -e bash -c "cd /home/daniel/frappe-bench && bench --site midas.local run-tests --app midas_app"
```

Ejecutar un solo test:

```bash
bench --site midas.local run-tests --app midas_app --doctype "Propuesta Solar"
```

Exportar fixtures (solo `Print Format` está registrado en `hooks.py`):

```bash
bench --site midas.local export-fixtures
```

## Estructura

```
apps/midas_app/
├── midas_app/
│   ├── hooks.py                 # app_name, fixtures=["Print Format"], add_to_apps_screen
│   ├── modules.txt              # módulo declarado: MIDAS
│   ├── api.py                   # has_app_permission()
│   ├── fixtures/                # SOLO print_format.json
│   ├── patches/                 # delete_propuesta_solar_test, create_midas_desktop_icon
│   ├── midas/
│   │   ├── solar_calc.py        # compute_solar_metrics (fórmulas de cálculo)
│   │   ├── charts.py            # generación de gráficas SVG (line/bar/pie/donut)
│   │   └── doctype/             # cliente, compania, cotizacion_midas(+_item/_tax),
│   │                            # equipo, servicio, propuesta_solar(+_equipo/_consumo_mensual/_flujo_caja/_perfil_horario)
│   ├── public/images/           # logo_midas.jpg
│   ├── templates/print_formats/ # propuesta_solar.html (fuente del Print Format)
│   └── workspace_sidebar/       # midas.json
├── pyproject.toml
└── README.md
```

> Nota: `modules.txt` declara el módulo como `MIDAS` pero la carpeta es `midas` (minúsculas).
> Inconsistencia existente; respetar salvo corrección explícita.

## Lógica central (léela antes de tocar cálculos)

- `midas_app/midas/solar_calc.py::compute_solar_metrics(doc)` — usado por **ambos** `Cotizacion Midas` y `Propuesta Solar`. Contiene `DEPARTMENT_KWH_PER_KWP` (18 departamentos de Honduras), `TARIFF_LPS_PER_KWH`, `TARIFF_USD_PER_KWH`, `DC_TO_AC_RATIO = 1.25`, `EXCHANGE_RATE = 26.8255`.
- `midas_app/midas/charts.py` — `ensure_chart_data(doc)` rellena los child tables (`consumo_mensual`, `perfil_horario`, `flujo_caja`) con datos por defecto si están vacíos; `get_proposal_charts(doc)` devuelve las gráficas.
- `propuesta_solar.py` expone whitelisted: `get_quotation_data`, `download_proposal_pdf` (WeasyPrint), `download_proposal_word` (python-docx).
- Los campos `npv`, `irr`, `energy_injected`, `energy_self_consumed`, `injection_pct` **existen en el Doctype pero NO están calculados todavía** (solo se leen en el export a Word). No asumir que tienen valor.

## Gotchas (cosas que un agente fallaría sin ayuda)

- **El HTML del Print Format está duplicado.** La fuente es `templates/print_formats/propuesta_solar.html`, pero lo que se usa en runtime viene del fixture `fixtures/print_format.json` (campo `html`, `custom_format=1`, `print_format_type=Jinja`). Al editar la plantilla hay que **regenerar el fixture y migrar** (`bench export-fixtures` + `bench --site midas.local migrate`), si no el cambio no se refleja en la DB.
- `propuesta_solar.json` ya declara `"default_print_format": "Propuesta Solar"` (sin esto Frappe imprime con el formato genérico "Standard").
- **Dependencias Python no declaradas:** `weasyprint`, `python-docx`, `cairosvg`, `beautifulsoup4` se usan en `propuesta_solar.py` pero NO están en `pyproject.toml`. Hay que instalarlas a mano en el entorno del bench (`env/bin/pip install python-docx weasyprint cairosvg`). `weasyprint` además requiere libs del sistema (pango/gdk-pixbuf) vía `apt`.
- **Moneda del site es USD (`$`).** Los campos `Currency` de la app NO llevan `options`, así que usan el default del sistema (`frappe.db.get_default("currency")`). Si algún monto deja de salir en `$`, revisar `System Settings.currency` y `frappe.db.set_default("currency", "USD")` (NO basta con `set_single_value`, no sincroniza `tabDefaultValue`).
- Hay un archivo basura trackeado por git: `midas_app/public/images/logo_midas.jpg:Zone.Identifier` (artefacto de Windows). Borrar del índice (`git rm --cached`) si se toca el área de imágenes.
- El remoto git es `upstream` apuntando a `github.com/dcruzparedes/midas_app.git`, rama `main` (el README dice `--branch develop`, obsoleto).
- Los scripts `.js` replican lógica de cálculo en cliente (ej. `recalc_row` en `cotizacion_midas.js` duplica `calculate_item_totals` de `cotizacion_midas.py`). Si cambias una fórmula, revisa la otra copia.

## Convenciones de código

Definidas en `pyproject.toml` (ruff) — **ruff es la fuente de verdad para lint/format:**

- `line-length = 110`
- Indentación con **tabs** (`indent-style = "tab"`), 4 espacios de ancho
- Doble comilla (`quote-style = "double"`)
- `pre-commit` corre ruff (import-sort I, linter, format), eslint, prettier, pyupgrade.

> Ojo: `.editorconfig` dice `max_line_length = 99`, pero ruff usa 110. Sigue a ruff.
> JSON de doctypes/fixtures: espacio, indent 2, **sin** newline final (`insert_final_newline = false`).

## Documento de referencia

La propuesta de referencia está en el equipo local (fuera del repo):

- `C:\Users\danie\Desktop\DevOps\Proyecto\Automatización de oferta.docx` — formato de la oferta.
- `C:\Users\danie\Desktop\DevOps\Proyecto\Calculos para Página Daniel.xlsx` — fórmulas de cálculo.

La empresa que firma es **Corporación Midas** (el docx de ejemplo referencia "Elite Energy Solutions").

## Estado actual / pendientes

Hecho:

- [x] Doctypes `Cotizacion Midas` (con items y taxes), `Cliente`, `Compania`, `Equipo`, `Servicio`.
- [x] Doctype `Propuesta Solar` + child tables (`Propuesta Equipo`, consumo mensual, perfil horario, flujo de caja).
- [x] Fórmulas de cálculo en `solar_calc.py`.
- [x] Print Format Jinja/HTML con logo y `default_print_format`.
- [x] Gráficas SVG (técnicas y financieras) en el documento.
- [x] Export a Word (`.docx`) y PDF con botones "Descargar Word/PDF".
- [x] Logo de la app e ícono de escritorio.

Pendientes:

- [ ] Modelo financiero avanzado: calcular `npv`, `irr`, `energy_injected`, `energy_self_consumed`, `injection_pct` (hoy solo se leen, valen 0/None).
- [ ] Asegurar que `Cotizacion Midas` y `Propuesta Solar` compartan las mismas fórmulas sin duplicación.
