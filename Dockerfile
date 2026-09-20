# Capa de dependencias de impresión de MIDAS.
# Las deps de Python (weasyprint, python-docx, cairosvg, htmldocx)

ARG BASE_IMAGE
FROM ${BASE_IMAGE}

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libcairo2 \
    libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*
USER frappe
