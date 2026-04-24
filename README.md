# Tarea 4 - Analisis de Vulnerabilidades

Organizacion elegida: **FlowiseAI**.

Este repositorio contiene un pipeline reproducible para:

- minar con la API de GitHub los 5 repositorios publicos no-fork con mas estrellas;
- generar SBOM CycloneDX con Syft;
- analizar vulnerabilidades de dependencias con Grype usando el SBOM;
- analizar codigo fuente con CodeQL;
- revisar configuraciones de GitHub Actions;
- consolidar los resultados en un dataset CSV para notebook.

Guia completa: [docs/proceso_flowise.md](docs/proceso_flowise.md)

Ejecucion rapida:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_all.ps1
```

Con Docker:

```powershell
docker build -t flowise-vuln-analysis .
docker run --rm -it -v ${PWD}:/workspace -e GITHUB_TOKEN=$env:GITHUB_TOKEN flowise-vuln-analysis
```

Sin token:

```powershell
docker run --rm -it -v ${PWD}:/workspace flowise-vuln-analysis
```
