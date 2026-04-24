# Proceso reproducible: analisis de vulnerabilidades en FlowiseAI

Este repositorio implementa el proceso pedido en `docs/tarea.md` para la organizacion elegida: **FlowiseAI**, organizacion asociada al proyecto Flowise. La seleccion de repositorios se realiza con la API REST de GitHub y toma los 5 repositorios publicos no-fork con mas estrellas.

## 1. Requisitos

Instalar y dejar en `PATH`:

- `git`
- `python` 3.10 o superior
- `syft` para generar SBOM CycloneDX
- `grype` para analizar vulnerabilidades desde el SBOM
- `codeql` CLI para analisis estatico de codigo

Recomendado:

- Definir `GITHUB_TOKEN` para evitar limites bajos de rate limit:

```powershell
$env:GITHUB_TOKEN = "ghp_xxx"
```

Si no tienes un token valido, dejalo vacio. Un token invalido produce `401 Bad credentials`:

```powershell
$env:GITHUB_TOKEN = ""
```

Tambien puedes usar `.env` para Docker Compose. Copia `.env.example` a `.env` y completa el valor solo si tienes un token valido:

```env
GITHUB_TOKEN=
```

No subas `.env` a Git. El repositorio ya lo ignora en `.gitignore`.

Verificar prerequisitos:

```powershell
python scripts/check_prereqs.py
```

## 2. Ejecucion con Docker

La forma mas portable es Docker, porque instala dentro de la imagen todas las herramientas necesarias: `git`, `python`, `syft`, `grype` y `codeql`.

Construir la imagen:

```powershell
docker build -t flowise-vuln-analysis .
```

Ejecutar el pipeline completo montando el repositorio actual:

```powershell
docker run --rm -it -v ${PWD}:/workspace -e GITHUB_TOKEN=$env:GITHUB_TOKEN flowise-vuln-analysis
```

Sin token:

```powershell
docker run --rm -it -v ${PWD}:/workspace flowise-vuln-analysis
```

En Linux/macOS:

```bash
docker run --rm -it -v "$PWD":/workspace -e GITHUB_TOKEN="$GITHUB_TOKEN" flowise-vuln-analysis
```

Con Docker Compose:

```powershell
docker compose run --rm flowise-vuln-analysis
```

Variables utiles:

- `ORG`: organizacion a analizar. Por defecto `FlowiseAI`.
- `TOP`: cantidad de repositorios. Por defecto `5`.
- `SKIP_CODEQL=1`: omite CodeQL si se quiere una corrida mas corta.
- `REFRESH_REPOS=1`: actualiza repositorios ya clonados con `git pull --ff-only`.
- `GITHUB_TOKEN`: token de GitHub para evitar rate limit.

Ejemplo sin CodeQL:

```powershell
docker run --rm -it -v ${PWD}:/workspace -e GITHUB_TOKEN=$env:GITHUB_TOKEN -e SKIP_CODEQL=1 flowise-vuln-analysis
```

El `Dockerfile` acepta versiones fijas:

```powershell
docker build `
  --build-arg SYFT_VERSION=vX.Y.Z `
  --build-arg GRYPE_VERSION=vX.Y.Z `
  --build-arg CODEQL_VERSION=codeql-bundle-vX.Y.Z `
  -t flowise-vuln-analysis .
```

Si no se pasan versiones, instala las ultimas versiones disponibles al momento de construir la imagen.

Para abrir el notebook desde el contenedor:

```powershell
docker run --rm -it -p 8888:8888 -v ${PWD}:/workspace flowise-vuln-analysis `
  jupyter notebook --ip=0.0.0.0 --port=8888 --allow-root --no-browser
```

## 3. Ejecucion completa sin Docker

Desde la raiz del repositorio:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_all.ps1
```

Esto ejecuta:

1. Mineria de repositorios con GitHub API.
2. Clonado local de los 5 repositorios seleccionados.
3. Generacion de SBOM CycloneDX con Syft.
4. Analisis de vulnerabilidades de dependencias con Grype usando los SBOM.
5. Analisis estatico con CodeQL.
6. Revision de workflows de GitHub Actions.
7. Consolidacion del dataset final.

Si CodeQL no esta instalado o se quiere ejecutar primero solo SBOM/Grype/CI:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_all.ps1 -SkipCodeQL
```

Para refrescar repositorios ya clonados:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_all.ps1 -RefreshRepos
```

## 4. Ejecucion paso a paso

### 4.1 Minar los 5 repositorios con mas estrellas

```powershell
python scripts/mine_github_repos.py --org FlowiseAI --top 5
```

Salidas:

- `data/top_repos.json`
- `data/top_repos.csv`

El JSON incluye fecha de generacion, criterio de seleccion, endpoint usado y metadatos de cada repositorio. El CSV sirve para citar rapidamente el ranking.

### 4.2 Clonar repositorios

```powershell
python scripts/clone_repos.py
```

Salidas:

- `data/repos/<repo>/`

Estos clones se ignoran en Git para no subir codigo de terceros al repositorio de la tarea.

### 4.3 Generar SBOM de codigo y dependencias

```powershell
python scripts/generate_sbom.py
```

Salidas:

- `data/sbom/<repo>.cyclonedx.json`

Syft inspecciona manifiestos y artefactos del codigo fuente clonado para construir el inventario de componentes: paquetes npm, metadatos, versiones, relaciones y evidencias disponibles.

### 4.4 Analizar vulnerabilidades con Grype

```powershell
python scripts/run_grype.py
```

Salidas:

- `reports/grype/<repo>.grype.json`

Grype consume directamente cada SBOM con el prefijo `sbom:`. Esto permite separar el inventario de software del analisis de vulnerabilidades.

### 4.5 Analizar codigo fuente con CodeQL

```powershell
python scripts/run_codeql.py
```

Salidas:

- `reports/codeql/<repo>-<lenguaje>.sarif`
- `reports/codeql/databases/<repo>-<lenguaje>/`

El script detecta lenguajes soportados por extension y usa las consultas predeterminadas disponibles en la instalacion local de CodeQL. Para un analisis mas focalizado, se puede pasar una consulta o suite explicita si esta disponible en la instalacion local:

```powershell
python scripts/run_codeql.py --queries security-extended
```

Nota: CodeQL analiza codigo fuente, no SBOM. El SBOM se usa para el analisis de dependencias con Grype; ambos resultados se integran despues en el dataset.

### 4.6 Revisar CI/CD

```powershell
python scripts/analyze_ci.py
```

Salidas:

- `reports/ci/ci_findings.json`
- `reports/ci/ci_findings.csv`

Reglas incluidas:

- uso de `pull_request_target`
- `permissions: write-all`
- `contents: write`
- `secrets: inherit`
- acciones no fijadas por SHA
- descargas tipo `curl | sh` o `curl | bash`

### 4.7 Consolidar dataset

```powershell
python scripts/consolidate_findings.py
```

Salidas:

- `data/findings.csv`
- `data/summary.json`

Columnas principales de `data/findings.csv`:

- `repo`: repositorio afectado
- `scanner`: `grype`, `codeql` o `workflow-inspector`
- `dimension`: `dependencies`, `source` o `ci_cd`
- `rule_id`: CVE/GHSA/regla de CodeQL/regla CI
- `severity`: severidad reportada o nivel equivalente
- `package_name`, `package_version`, `package_type`: datos de dependencia cuando aplica
- `fixed_versions`: versiones corregidas cuando Grype las reporta
- `description`: evidencia o descripcion resumida
- `source_file`, `line`: ubicacion cuando aplica

## 5. Analisis en notebook

Abrir:

- `notebooks/analisis_flowise.ipynb`

El notebook lee `data/findings.csv` y `data/top_repos.csv` para:

- contar hallazgos por repositorio
- comparar dimensiones: codigo, dependencias y CI/CD
- revisar severidades
- identificar paquetes o reglas mas frecuentes
- dejar interpretacion cualitativa y relacion con los casos de la pauta

## 6. Evidencia esperada para la entrega

Al finalizar, el repositorio deberia contener:

- `data/top_repos.csv` y `data/top_repos.json`
- `data/sbom/*.cyclonedx.json`
- `reports/grype/*.grype.json`
- `reports/codeql/*.sarif`
- `reports/ci/ci_findings.csv`
- `data/findings.csv`
- `data/summary.json`
- `notebooks/analisis_flowise.ipynb`

Los clones en `data/repos/` y las bases de datos de CodeQL en `reports/codeql/databases/` quedan fuera de Git por tamano y porque son reproducibles.

## 7. Criterio de interpretacion

Para cumplir la pauta, el informe final debe conectar los hallazgos con tres preguntas:

1. **Codigo fuente:** que patrones detecta CodeQL y que impacto tendrian si fueran explotables.
2. **Dependencias:** que CVE/GHSA aparecen desde Grype, en que paquetes y si existen versiones corregidas.
3. **CI/CD:** que workflows aumentan riesgo de supply chain, especialmente permisos amplios, acciones no fijadas y ejecucion de scripts descargados.

La discusion debe relacionar esos resultados con el caso Flowise de la pauta: exposicion de instancias, ejecucion remota de codigo y riesgo de ecosistema por dependencias y automatizaciones.
