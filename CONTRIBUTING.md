# Guía de contribución

¡Gracias por tu interés en mejorar **GSpreadManager**! Esta guía resume cómo
preparar el entorno, correr las verificaciones y proponer cambios.

## Entorno de desarrollo

Requiere Python 3.9 o superior.

```bash
# Clonar e instalar en modo editable con las dependencias de desarrollo
git clone https://github.com/PabloAlaniz/GSpreadManager.git
cd GSpreadManager
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -e .[dev]
```

Esto instala el paquete junto con `pytest`, `pytest-cov`, `ruff` y `pandas`.

## Correr las verificaciones

```bash
# Tests con cobertura (mínimo 80 %)
pytest

# Linter
ruff check .

# Formato
ruff format .            # aplica el formato
ruff format --check .    # solo verifica (lo que corre el CI)
```

Antes de abrir un PR, asegurate de que los tests y el linter pasen en verde.
Podés automatizarlo localmente con [pre-commit](https://pre-commit.com/):

```bash
pip install pre-commit
pre-commit install
```

## Convención de commits

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` nueva funcionalidad
- `fix:` corrección de bug
- `docs:` cambios de documentación
- `test:` agregar o ajustar tests
- `chore:` tareas de mantenimiento (CI, tooling, deps)
- `refactor:` cambios internos sin alterar el comportamiento

## Pull Requests

1. Creá una rama descriptiva a partir de `main`.
2. Incluí tests para cualquier cambio de comportamiento.
3. Actualizá el `CHANGELOG.md` si corresponde.
4. Mantené el PR enfocado en un solo objetivo.
