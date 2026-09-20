# Despliegue en producción y CI/CD

Este documento explica cómo se empaqueta y despliega la aplicación en producción, y cómo
funciona el pipeline de integración y despliegue continuo (CI/CD).

## 1. Arquitectura de despliegue

La app se empaqueta en una **imagen Docker** y se ejecuta como un **stack** (conjunto de
contenedores) en un servidor con **Portainer**.

### Componentes

| Componente | Descripción |
|---|---|
| `Dockerfile` | Capa que agrega las librerías de sistema (`pango/cairo`) sobre la imagen base. |
| `docker-compose.yml` | Define los servicios que corren en producción. |
| `.github/workflows/build-deploy.yml` | Pipeline que construye la imagen, la sube a Docker Hub y dispara el deploy. |
| Docker Hub | Registro donde se publica la imagen (`tuusuario/midas_app`). |
| Portainer | Orquesta el stack en el servidor. |

### Servicios del `docker-compose.yml`

- `mariadb` — base de datos.
- `redis-cache` y `redis-queue` — caché y cola de trabajos.
- `crear-sitio` — corre **una sola vez**: crea el sitio, instala `midas_app` y migra.
- `backend` — el servidor web (Frappe) en el puerto 8000.
- `worker` — procesa trabajos en segundo plano.
- `scheduler` — tareas programadas.
- `socketio` — comunicación en tiempo real.
- `frontend` — nginx que sirve la app y el websocket.

## 2. Cómo se construye la imagen

La imagen se construye en **dos pasos** dentro del pipeline:

1. **Build base (frappe_docker)** — usa el `Containerfile` oficial de frappe_docker para crear
   una imagen con Frappe (`v16.31.0`) + la app `midas_app` (clonada desde el repo). La versión
   de Frappe se fija con `FRAPPE_BRANCH=v16.31.0` (no se actualiza sola).
2. **Capa de impresión (nuestro `Dockerfile`)** — toma la imagen del paso 1 y le agrega las
   librerías `pango/cairo` que WeasyPrint necesita para el PDF.

> Las dependencias de Python (`weasyprint`, `python-docx`, `cairosvg`, `htmldocx`) se instalan
> automáticamente durante el build base, porque están declaradas en `pyproject.toml`.

## 3. Puesta en marcha en Portainer (una sola vez)

1. En Portainer → **Stacks → Add stack** (Compose), pega el contenido de `docker-compose.yml`.
2. Define las variables de entorno:
   - `IMAGE_NAME` = `tuusuario/midas_app:latest`
   - `SITE_NAME` = `devops-midasgdp.rdtech.lat` (o el dominio del sitio)
   - `ADMIN_PASSWORD` = contraseña del administrador
   - `DB_ROOT_PASSWORD` = contraseña de MariaDB
3. Crea el stack. La primera vez, el servicio `crear-sitio` crea el sitio e instala la app.
4. En el stack → **Webhooks → Add webhook**, copia la URL y guárdala como secreto en GitHub
   (`PORTAINER_WEBHOOK_URL`).

A partir de ahí, cada vez que se suba una imagen nueva, Portainer hace *pull* y redeploya el stack.

## 4. CI/CD explicado

### Flujo completo

```
git push (cambios en main)
      │
      ▼
GitHub Actions (build-deploy.yml)
      │
      ├─ build-and-push (job): construye la imagen
      │     ├─ checkout frappe_docker + midas_app
      │     ├─ apps.json (lista la app)
      │     ├─ build base (Containerfile frappe_docker)
      │     ├─ build capa de impresión (Dockerfile)
      │     └─ login + push a Docker Hub
      │
      ▼
deploy (job): curl -X POST al webhook de Portainer
      │
      ▼
Portainer hace pull de la imagen nueva y redeploya el stack
      │
      ▼
App actualizada y corriendo
```

### Qué es CI y qué es CD

- **CI (Integración Continua)** — cada `push` a `main` dispara un **build automático** de la
  imagen. Si algo se rompe en el build, el pipeline falla y te enteras al instante.
- **CD (Despliegue Continuo)** — tras el build exitoso, la imagen se publica y se despliega
  **automáticamente** (webhook → Portainer). No hay intervención manual.

### Jobs y steps del `build-deploy.yml`

**Job `build-and-push`** (corre en el runner `self-hosted, ARM64`):

1. `Checkout frappe_docker` — baja el repo oficial con el `Containerfile`.
2. `Checkout midas_app` — baja nuestro repo (para el `Dockerfile`).
3. `Generate apps.json` — crea la lista de apps a instalar (nuestra app).
4. `Build image` — construye la imagen base (frappe + app).
5. `Agregar dependencias de impresión` — construye la capa de `pango/cairo` con nuestro `Dockerfile`.
6. `Login a Docker Hub` + `Push Docker Image` — publica la imagen (`:latest` y `:sha`).
7. `Limpiar apps.json` — borra el archivo temporal.

**Job `deploy`:**

1. `Trigger Portainer Webhook` — `curl -X POST` a la URL del webhook, que dispara el redeploy.

### Runner self-hosted

El pipeline corre en un **runner auto-hospedado** instalado en el servidor. A continuación la guía
esencial para instalarlo en un servidor **Linux ARM64**.

#### 1. Pre-requisitos

- Docker instalado y funcionando (`docker --version`).
- Acceso SSH al servidor con un usuario con `sudo` (en el ejemplo, `ubuntu`).
- El servidor es **ARM64 (aarch64)** → el runner debe ser **Linux ARM64**.

#### 2. Crear usuario dedicado y acceso a Docker

```bash
sudo useradd -m -s /bin/bash runner
sudo usermod -aG docker runner
```

> `runner` se crea sin contraseña (no puede usar `sudo` todavía). Es normal.

#### 3. Obtener los comandos de registro desde GitHub

1. Repo → **Settings → Actions → Runners → New self-hosted runner**.
2. Elegir **Linux** y arquitectura **ARM64**.
3. Copiar solo la **URL de descarga**, el **checksum** y el **token**.
   - El token es de un solo uso y expira. Si falla o lo pegas mal, genera otro.

#### 4. Descargar, verificar y extraer

Entrar como `runner` y descargar (usa la URL exacta que te dé GitHub):

```bash
sudo -iu runner
mkdir actions-runner && cd actions-runner

# URL de ejemplo; usa la versión exacta que te dé GitHub
curl -o actions-runner-linux-arm64.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.337.0/actions-runner-linux-arm64-2.337.0.tar.gz
```

Verificar el checksum (pega el que te dé GitHub):

```bash
echo "<checksum>  actions-runner-linux-arm64.tar.gz" | shasum -a 256 -c
# Debe imprimir: actions-runner-linux-arm64.tar.gz: OK
```

Extraer:

```bash
tar xzf ./actions-runner-linux-arm64.tar.gz
```

#### 5. Registrar el runner (`config.sh`)

```bash
./config.sh --url https://github.com/dcruzparedes/midas_app --token <TOKEN>
```

En las preguntas:

- *Enter the name of the runner group* → **dejar vacío** y Enter (grupo Default).
- *Enter the name of runner* → escribe el nombre (ej. `oracle-arm64`).
- *Enter any additional labels* → Enter (quedan `self-hosted, Linux, ARM64`).
- *Enter name of work folder* → Enter (`_work`).

Debe terminar con **"Runner successfully added"**.

#### 6. Instalarlo como servicio (sobrevive a cierres y reinicios)

`./run.sh` solo sirve para probar en primer plano; **no** usarlo como método definitivo.

El comando `svc.sh install` necesita `sudo`, y `runner` no tiene. Solución: darle sudo desde el
usuario `ubuntu` (no desde `runner`):

```bash
exit                                        # salir de la sesión de runner
echo "runner ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/runner

sudo -iu runner
cd ~/actions-runner
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
```

#### 7. Verificar

- En GitHub → **Settings → Actions → Runners** → el runner aparece en **Idle**.
- En el servidor: `sudo ./svc.sh status` (o `sudo systemctl status actions.runner.*`).

#### 8. Errores comunes

| Síntoma | Causa / solución |
|---|---|
| `sudo` pide contraseña de `runner` | `runner` no tiene contraseña; correr `sudo` como `ubuntu`, o usar la línea del sudoers del paso 6. |
| "Could not find runner group named X" | Escribiste el nombre en el campo del grupo; déjalo vacío. |
| "Runner successfully added" pero se detiene al cerrar SSH | Estás usando `./run.sh` en primer plano; instala el servicio (paso 6). |
| Token rechazado | El token es de un solo uso o expiró; genera uno nuevo. |

#### 9. Desinstalar o re-registrar

```bash
sudo -iu runner
cd ~/actions-runner
sudo ./svc.sh stop && sudo ./svc.sh uninstall   # quita el servicio
./config.sh remove --token <TOKEN_NUEVO>        # quita el registro en GitHub
# luego vuelve a correr config.sh (paso 5)
```

### Secretos de GitHub necesarios

| Secreto | Uso |
|---|---|
| `DOCKERHUB_USERNAME` | Usuario de Docker Hub. |
| `DOCKERHUB_TOKEN` | Token de acceso de Docker Hub (no la contraseña). |
| `PORTAINER_WEBHOOK_URL` | URL del webhook del stack en Portainer. |

## 5. Versiones y actualizaciones

- **Frappe** está **fijado** a `v16.31.0` (`FRAPPE_BRANCH=v16.31.0`): no se actualiza solo.
  Para subir de versión, cambia ese valor y haz `push`.
- **frappe_docker** está fijado a `v3.2.2` (`ref: v3.2.2`).
- **La app** (`midas_app:latest`) se actualiza en cada `push` a `main` (es el CI/CD trabajando).
