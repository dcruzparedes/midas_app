# Descripción del proyecto y estructura

## 1. ¿Qué es MIDAS?

`midas_app` es una aplicación de **Frappe** para **Corporación Midas** que automatiza la
generación de **propuestas de sistemas solares fotovoltaicos** bajo el modelo **EPC**
(Ingeniería, Procura y Construcción).

La app es **independiente de ERPNext**: usa sus propios doctypes (no depende de `Quotation`,
`Customer`, `Item`, etc.). Solo necesita el framework Frappe para funcionar.

## 2. Flujo de trabajo

1. El usuario captura la información en una **Cotización Midas** (cliente, consumo, tarifa, parámetros del panel).
2. Desde la cotización se genera una **Propuesta Solar** (botón *"Generar Propuesta Midas"*).
3. `solar_calc.py` calcula los resultados (potencia DC/AC, energía generada, ahorro, inversión, retorno).
4. `charts.py` genera las **gráficas** (SVG: barras, línea y tarta).
5. La propuesta se muestra en un **Print Format** (Jinja/HTML) y se exporta a **PDF** y **Word**.

## 3. Funcionalidades principales

- **Cotización Midas**: captura de datos de la oferta (cliente, consumo, tarifa, panel solar) y de servicios.
- **Propuesta Solar**: documento formateado con resultados técnicos y financieros.
- **Gráficas**: consumo vs generación, matriz energética, perfil horario, flujo de caja, etc.
- **Export a PDF** (WeasyPrint) y **Word** (python-docx).
- **Doctypes propios**: Cliente, Compañía, Equipo, Servicio, Cotización Midas, Propuesta Solar.
- **UI en español**, workspace propio y logo personalizado en el login.

## 4. Doctypes principales

| Doctype | Propósito |
|---|---|
| `Cliente` | Datos de los clientes (razón social, RTN, contacto). |
| `Compania` | Datos de la empresa que emite la propuesta (Corporación Midas). |
| `Equipo` | Catálogo de equipos (módulos, inversores) con imagen y especificaciones. |
| `Servicio` | Catálogo de servicios ofrecidos (instalación, O&M, etc.). |
| `Cotizacion Midas` | La oferta comercial, con ítems (servicios) e impuestos. |
| `Propuesta Solar` | El documento final de la propuesta, con equipos y series de cálculo. |

### Tablas hijas (child tables)

- `Cotizacion Midas Item` y `Cotizacion Midas Tax` → ítems e impuestos de la cotización.
- `Propuesta Equipo` → equipos de la propuesta (con imagen).
- `Propuesta Consumo Mensual`, `Propuesta Perfil Horario`, `Propuesta Flujo Caja` → series para las gráficas.
- `Propuesta Pago` → calendario de pagos.

## 5. Stack

- **Frappe**: `v16.31.0`
- **Python**: `>= 3.10`
- **Librerías de impresión**: `weasyprint` (PDF), `python-docx` (Word), `cairosvg` (gráficas a PNG).

## 6. Estructura del repositorio

```
midas_app/
├── .github/
│   └── workflows/
│       └── build-deploy.yml      # CI/CD (build → Docker Hub → deploy)
├── midas_app/
│   ├── hooks.py                  # configuración de la app (logo, CSS, fixtures, pantalla de apps)
│   ├── modules.txt               # módulo declarado: MIDAS
│   ├── api.py                    # has_app_permission() para la pantalla de apps
│   ├── fixtures/
│   │   └── print_format.json     # Print Format (HTML autoritativo en runtime)
│   ├── patches/                  # migraciones (delete_propuesta_solar_test, create_midas_desktop_icon)
│   ├── midas/
│   │   ├── solar_calc.py         # fórmulas de cálculo (compute_solar_metrics)
│   │   ├── charts.py             # generación de gráficas SVG
│   │   └── doctype/              # todos los doctypes (cliente, compania, cotizacion_midas, etc.)
│   ├── public/
│   │   ├── images/               # logo_midas.jpg
│   │   └── css/                  # midas_login.css (estilo del login)
│   ├── templates/
│   │   └── print_formats/
│   │       └── propuesta_solar.html   # fuente del Print Format
│   └── workspace_sidebar/
│       └── midas.json            # barra lateral de Frappe
├── Dockerfile                    # capa de dependencias de impresión (pango/cairo)
├── docker-compose.yml            # stack de producción (mariadb, redis, web, worker, ...)
├── pyproject.toml                # dependencias de Python y apt
└── README.md
```

### Archivos clave

- **`solar_calc.py`** — contiene las constantes y fórmulas del cálculo solar
  (tarifas, ratio DC/AC, tipo de cambio, departamentos de Honduras). Lo usan tanto
  `Cotizacion Midas` como `Propuesta Solar`.
- **`charts.py`** — genera las gráficas SVG (línea, barras, tarta) y rellena los child tables
  con datos por defecto si están vacíos.
- **`propuesta_solar.py`** — expone los métodos de descarga (`download_proposal_pdf`,
  `download_proposal_word`) y `get_quotation_data`.
- **`Dockerfile`** — capa que agrega las librerías de sistema (`pango/cairo`) que necesita
  WeasyPrint sobre la imagen base.
- **`docker-compose.yml`** — define los servicios que corren en producción.
- **`.github/workflows/build-deploy.yml`** — el pipeline de CI/CD.
