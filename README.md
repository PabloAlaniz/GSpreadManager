# GSpreadManager

## Descripción
GSpreadManager es un módulo de Python diseñado para facilitar la interacción con Google Sheets. Permite a los usuarios realizar operaciones comunes como leer, escribir y actualizar hojas de cálculo de Google Sheets de manera eficiente y automatizada.

## Características
- Conexión segura a Google Sheets usando la API de Google.
- Funciones para leer, escribir, y actualizar hojas de cálculo.
- Métodos para buscar y manipular datos dentro de las hojas de cálculo.

## Pre-requisitos

Para utilizar el conector `GSpreadManager`, es necesario realizar una configuración inicial en Google Cloud y en tus hojas de cálculo de Google. Sigue estos pasos:

### 1. Crear una Cuenta de Servicio en Google Cloud
- Accede a [Google Cloud Console](https://console.cloud.google.com/).
- Crea un nuevo proyecto o selecciona uno existente.
- En el menú lateral, ve a "IAM y administración" > "Cuentas de servicio" y crea una nueva cuenta de servicio.
- Descarga la clave de la cuenta de servicio en formato JSON. Este archivo será necesario para autenticar tu aplicación.

### 2. Habilitar las APIs de Google Drive y Google Sheets
- Dentro del mismo proyecto en Google Cloud Console, ve a la sección "Biblioteca" en el menú "APIs y servicios".
- Busca y habilita las APIs de "Google Sheets" y "Google Drive".

### 3. Dar Permiso a la Cuenta de Servicio en las Hojas de Cálculo
- Abre la hoja de cálculo de Google que deseas manipular.
- Comparte la hoja de cálculo con el email de la cuenta de servicio creada, asignándole permisos de edición.
- Este paso es necesario para que la cuenta de servicio pueda acceder y modificar tus hojas de cálculo.

Una vez completados estos pasos, tu entorno estará listo para utilizar `GSpreadManager`.


## Requisitos
- Python 3.7 o superior.
- Paquetes: `gspread`, `oauth2client`.

## Instalación
Para instalar GSpreadManager, sigue estos pasos:

Localmente (desde el código fuente):
```bash
pip install GSpreadManager
```

## Uso Básico
Aquí hay un ejemplo básico de cómo usar GSpreadManager para conectarse a una hoja de cálculo de Google y leer datos:

```python
from gspreadmanager import GoogleSheetConector

# Crear una instancia del conector
conector = GoogleSheetConector(doc_name='NombreDelDocumento', json_google_file='ruta/credenciales.json', sheet_name='NombreDeLaHoja')

# Leer datos
datos = conector.read_sheet_data()
```
## Contribuir
Las contribuciones son bienvenidas. 

## Licencia
MIT License
