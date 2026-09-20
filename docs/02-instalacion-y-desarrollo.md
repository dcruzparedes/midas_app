# Instalación y entorno de desarrollo

Esta guía describe dos formas de montar el entorno de **desarrollo**:

- **Método A — WSL + bench nativo** (el que usa el proyecto).
- **Método B — Dev Container de frappe_docker** (alternativa con VS Code).

## Método A — WSL + bench nativo

### 1. Requisitos del sistema

Instalar Python 3.14 con `uv`, Node.js v24, Yarn y las librerías de compilación de MariaDB:

```bash
uv python install 3.14

curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g yarn

sudo apt update && sudo apt install -y libmariadb-dev libmariadb-dev-compat
```

### 2. Restablecer la contraseña de root en MariaDB

Para evitar errores de autenticación al crear sitios, se fija la contraseña de `root` a `root`.

```bash
# 2.1 Detener el servicio e iniciar MariaDB en modo seguro
sudo systemctl stop mariadb
sudo mysqld_safe --skip-grant-tables --skip-networking &

# 2.2 Acceder como superusuario y cambiar la contraseña
sudo mysql -u root
```

Dentro del prompt de MariaDB:

```sql
FLUSH PRIVILEGES;
ALTER USER 'root'@'localhost' IDENTIFIED BY 'root';
EXIT;
```

```bash
# 2.3 Reiniciar MariaDB normalmente
sudo pkill -9 -f mariad
sudo pkill -9 -f mysql
sudo systemctl start mariadb

# 2.4 Verificar el acceso
mysql -u root -proot -e "SELECT 1;"
```

### 3. Inicializar el bench

```bash
cd ~ && rm -rf ~/frappe-bench   # limpiar una instalación anterior
bench init --python $(uv python find 3.14) --version develop frappe-bench
```

### 4. Cambiar a la versión 16 de Frappe

Al clonar Frappe, por defecto solo está la rama `develop`. El proyecto usa la **versión 16**
(`version-16`), necesaria para que el UI salga en la versión correcta/actualizada:

```bash
cd ~/frappe-bench/apps/frappe
git fetch --all          # trae todas las ramas y tags
cd ~/frappe-bench
bench switch-to-branch version-16
```

### 5. Crear y mapear el sitio

```bash
cd ~/frappe-bench
bench new-site midas.local --admin-password admin --db-root-password root
bench use midas.local
```

`bench use midas.local` establece el sitio por defecto para que `bench start` lo sirva directo.

## Método B — Dev Container de frappe_docker (alternativa)

### 1. Configurar el Dev Container (VS Code)

```bash
git clone https://github.com/frappe/frappe_docker
cd frappe_docker
cp -R devcontainer-example .devcontainer
```

Abrir la carpeta en VS Code → `Ctrl+Shift+P` → **Dev Containers: Reopen in Container**.

Si falla por *timeout* al descargar la imagen (`context deadline exceeded`), descargarla
manualmente desde el host y reintentar:

```bash
docker pull frappe/bench:latest
```

### 2. Inicializar el bench

```bash
bench init frappe-bench --frappe-branch version-16 --skip-redis-config-generation
cd frappe-bench
```

> Se omite la generación de Redis local porque en Docker los servicios corren en contenedores
> dedicados.

### 3. Configurar la red para Docker

Editar `sites/common_site_config.json`:

```json
{
  "background_workers": 1,
  "db_host": "mariadb",
  "file_watcher_port": 6787,
  "frappe_user": "frappe",
  "gunicorn_workers": 33,
  "live_reload": true,
  "redis_cache": "redis://redis-cache:6379",
  "redis_queue": "redis://redis-queue:6379",
  "redis_socketio": "redis://redis-cache:6379",
  "serve_default_site": true,
  "socketio_port": 9000,
  "use_redis_auth": false,
  "webserver_port": 8000
}
```

### 4. Crear el sitio

```bash
bench new-site midas.local --mariadb-root-password 123 --admin-password admin
bench use midas.local
```

## Común a ambos métodos

### 1. Clonar e instalar la app

```bash
bench get-app https://github.com/dcruzparedes/midas_app.git
bench --site midas.local install-app midas_app
```

### 2. Dependencias de impresión (PDF/Word)

La app usa `weasyprint` (PDF), `python-docx` (Word) y `cairosvg` (gráficas). Instalarlas en el
entorno del bench:

```bash
env/bin/pip install weasyprint python-docx cairosvg htmldocx

sudo apt-get update && sudo apt-get install -y \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libcairo2 \
    libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 fonts-dejavu
```

> En producción estas dependencias ya van dentro del `Dockerfile`.

### 3. Migrar y arrancar

```bash
bench --site midas.local migrate
bench start
```

Entra en `http://localhost:8000` con el usuario `Administrator` y la contraseña `admin`.

## Flujo diario de desarrollo

Cuando tú o un compañero hacen cambios y haces `git pull`, lo que toca correr depende de qué cambió:

| Qué cambió | Qué hacer |
|---|---|
| **JS / CSS** (frontend) | Nada: `bench watch` (dentro de `bench start`) recompila solo. Refresca el navegador (Ctrl+Shift+R). |
| **Python** (`.py`) | El web se recarga solo; reinicia **worker/scheduler** (`bench restart`). |
| **Doctype / schema** (`.json` de doctypes) | `bench --site midas.local migrate` (obligatorio). |
| **hooks.py / fixtures / patches** | `bench --site midas.local migrate` + `bench clear-cache`. |
| **Dependencias nuevas** (`pyproject.toml`) | `pip install ...` (o `bench setup requirements`). |

Rutina segura después de cada `git pull`:

```bash
git pull
bench --site midas.local migrate
bench clear-cache
bench restart
```

## Nota importante sobre el Print Format

El HTML del Print Format está **duplicado**:

- La fuente es `midas_app/templates/print_formats/propuesta_solar.html`.
- Lo que se usa en runtime viene del fixture `fixtures/print_format.json` (campo `html`).

Por eso, al editar la plantilla debes **regenerar el fixture y migrar**:

```bash
bench --site midas.local export-fixtures
bench --site midas.local migrate
```

Si no lo haces, el cambio no se refleja en la base de datos.
