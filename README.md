# MIDAS

Aplicación de [Frappe](https://frappeframework.com/) para **Corporación Midas** que automatiza la
generación de **propuestas de sistemas solares fotovoltaicos** bajo el modelo EPC
(Ingeniería, Procura y Construcción).

## ¿Qué hace?

1. El usuario captura la información en una **Cotización Midas** (doctype propio).
2. Desde la cotización se genera una **Propuesta Solar** con los cálculos técnicos y financieros.
3. La propuesta incluye **gráficas** y se exporta a **PDF** y **Word**.

## Documentación

- [Descripción del proyecto y estructura](docs/01-descripcion-y-estructura.md)
- [Instalación y entorno de desarrollo](docs/02-instalacion-y-desarrollo.md)
- [Despliegue en producción y CI/CD](docs/03-produccion-y-ci-cd.md)

## Stack

- Frappe `v16.31.0`
- Python `>= 3.10`

## Licencia

MIT
