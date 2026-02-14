# GSpreadManager

[![PyPI version](https://badge.fury.io/py/GSpreadManager.svg)](https://badge.fury.io/py/GSpreadManager)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

GSpreadManager es un wrapper de Python para facilitar la interacción con Google Sheets. Proporciona una interfaz simple y pythonic para operaciones comunes como lectura, escritura, actualización y búsqueda de datos en hojas de cálculo de Google.

## ✨ Características

- 🔐 **Autenticación segura** usando cuentas de servicio de Google
- 📖 **Lectura flexible** de datos (listas, diccionarios, pandas DataFrame)
- ✏️ **Escritura y actualización** de celdas, filas y rangos
- 🔍 **Búsqueda y filtrado** de datos
- ⚡ **Operaciones en lote** para mejor rendimiento
- 🐍 **API pythonic** con docstrings completas
- 📦 **Sin dependencias pesadas** - solo gspread, oauth2client y pandas

---

## 🚀 Quick Start

### Instalación

```bash
pip install GSpreadManager
```

### Configuración Inicial

#### 1. Crear Cuenta de Servicio en Google Cloud

1. Accede a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un proyecto nuevo o selecciona uno existente
3. Ve a **IAM y administración > Cuentas de servicio**
4. Crea una nueva cuenta de servicio
5. Descarga la clave JSON (la necesitarás para autenticarte)

#### 2. Habilitar APIs Necesarias

En Google Cloud Console, ve a **APIs y servicios > Biblioteca** y habilita:

- ✅ Google Sheets API
- ✅ Google Drive API

#### 3. Compartir Hoja de Cálculo

1. Abre tu hoja de Google Sheets
2. Haz clic en **Compartir**
3. Agrega el email de la cuenta de servicio (lo encuentras en el JSON descargado)
4. Asígnale permisos de **Editor**

### Ejemplo Básico

```python
from gspreadmanager import GoogleSheetConector

# Conectar a una hoja
conector = GoogleSheetConector(
    doc_name='Mi Hoja de Cálculo',
    json_google_file='path/to/credentials.json',
    sheet_name='Hoja1'  # Opcional, por defecto usa la primera hoja
)

# Leer todos los datos
datos = conector.read_sheet_data(output_format='list')
print(datos)

# Agregar una fila
nueva_fila = [['Juan', 'juan@example.com', '555-1234']]
conector.spreadsheet_append(nueva_fila)

# Actualizar una celda específica
conector.update_cell(conector.sheet, row_index=2, col_index=1, value='María')
```

---

## 📚 Guía de Uso

### Lectura de Datos

#### Leer como lista de listas

```python
# Leer todos los datos
datos = conector.read_sheet_data(output_format='list')
# Resultado: [['Header1', 'Header2'], ['Valor1', 'Valor2'], ...]

# Saltar las primeras N filas
datos = conector.read_sheet_data(skiprows=2, output_format='list')
```

#### Leer como lista de diccionarios

```python
# La primera fila se usa como headers/keys
datos = conector.read_sheet_data(output_format='dict')
# Resultado: [{'Header1': 'Valor1', 'Header2': 'Valor2'}, ...]
```

#### Leer como pandas DataFrame

```python
# Ideal para análisis de datos
df = conector.read_sheet_data(output_format='pandas')
print(df.head())
print(df.describe())
```

#### Leer un rango específico

```python
# Leer filas 1-10, columnas A-D
datos = conector.spreadsheet_read_range(
    sheet=conector.sheet,
    tab_name='Hoja1',
    fila_start=1,
    fila_end=10,
    column_start='A',
    column_end='D'
)
```

### Escritura de Datos

#### Agregar filas al final

```python
# Agregar una fila
nuevos_datos = [['Ana', 'ana@example.com', '555-5678']]
conector.spreadsheet_append(nuevos_datos)

# Agregar múltiples filas
nuevos_datos = [
    ['Carlos', 'carlos@example.com', '555-1111'],
    ['Diana', 'diana@example.com', '555-2222']
]
conector.spreadsheet_append(nuevos_datos, tab_name='Contactos')
```

#### Insertar datos en una fila específica

```python
datos = [['Nuevo', 'Dato', 'Aquí']]
conector.spreadsheet_insert(
    sheet_name='Mi Hoja',
    worksheet_name='Hoja1',
    data=datos,
    fila=5  # Insertar en la fila 5
)

# Si fila=None, inserta al final
conector.spreadsheet_insert('Mi Hoja', 'Hoja1', datos, fila=None)
```

### Actualización de Datos

#### Actualizar una celda

```python
# Actualizar celda en fila 3, columna 2
conector.update_cell(
    sheet=conector.sheet,
    row_index=3,
    col_index=2,
    value='Nuevo Valor'
)
```

#### Actualizar una fila completa

```python
# Actualizar desde la columna 1
nueva_fila = ['Valor1', 'Valor2', 'Valor3']
conector.update_row(
    sheet=conector.sheet,
    row_index=5,
    data=nueva_fila
)

# Actualizar desde una columna específica
conector.update_row(
    sheet=conector.sheet,
    row_index=5,
    data=nueva_fila,
    start_column=3  # Empieza desde la columna C
)
```

#### Actualizaciones en lote (más eficiente)

```python
# Actualizar múltiples rangos en una sola operación
updates = [
    {
        "range": "Hoja1!A1:C2",
        "values": [
            ["Header1", "Header2", "Header3"],
            ["Valor1", "Valor2", "Valor3"]
        ]
    },
    {
        "range": "Hoja1!E1:F2",
        "values": [
            ["Columna5", "Columna6"],
            ["Data5", "Data6"]
        ]
    }
]
conector.batch_update(updates)
```

### Búsqueda y Filtrado

#### Buscar filas por valor en columna

```python
# Buscar todas las filas donde la columna 0 (primera) sea 'Juan'
filas_encontradas = conector.get_rows_where_column_equals(
    column=0,
    value='Juan'
)

# Resultado: [(row_number, [celda1, celda2, ...]), ...]
for numero_fila, contenido_fila in filas_encontradas:
    print(f"Fila {numero_fila}: {contenido_fila}")
```

#### Encontrar primera celda vacía en columna

```python
# Útil para encontrar dónde insertar el próximo registro
fila, indice = conector.get_row_with_empty_in_column(
    sheet=conector.sheet,
    column_letter='B'
)

if fila:
    print(f"Primera celda vacía en columna B está en la fila {indice}")
else:
    print("No hay celdas vacías en la columna B")
```

### Utilidades

#### Obtener la última fila con datos

```python
# En la hoja actual
ultima = conector.get_last_row()

# En una hoja específica
ultima = conector.get_last_row(tab_name='Ventas')

print(f"La última fila con datos es: {ultima}")
```

#### Cambiar de pestaña

```python
# Conectar a otra pestaña del mismo documento
nueva_hoja = conector.connect_to_sheet(
    doc_name='Mi Hoja de Cálculo',
    sheet_name='Otra Pestaña'
)
```

---

## 🏗️ Arquitectura

### Estructura del Proyecto

```
GSpreadManager/
├── gspreadmanager/
│   ├── __init__.py          # Exporta GoogleSheetConector
│   ├── connector.py         # Clase principal con toda la lógica
│   └── config.py            # Configuraciones y constantes
├── setup.py                 # Configuración de instalación
├── README.md                # Este archivo
└── LICENSE                  # Licencia MIT
```

### Dependencias

- **gspread** (>=3.0.0): Cliente de Google Sheets API
- **oauth2client** (>=4.1.0): Autenticación con cuentas de servicio
- **pandas** (>=1.0.0): Manipulación de datos (opcional, solo para formato DataFrame)

### Flujo de Autenticación

```
1. Cargar credenciales desde JSON
        ↓
2. Crear objeto ServiceAccountCredentials
        ↓
3. Autorizar cliente gspread
        ↓
4. Abrir documento por nombre
        ↓
5. Seleccionar hoja (worksheet)
        ↓
6. Listo para operaciones CRUD
```

---

## 🔧 API Reference

### Clase: `GoogleSheetConector`

#### Constructor

```python
GoogleSheetConector(doc_name, json_google_file, sheet_name=None)
```

**Parámetros:**
- `doc_name` (str): Nombre del documento de Google Sheets
- `json_google_file` (str): Ruta al archivo JSON de credenciales
- `sheet_name` (str, opcional): Nombre de la hoja específica (por defecto: primera hoja)

**Atributos:**
- `sheet_title`: Nombre del documento
- `json_google_file`: Ruta a credenciales
- `tab_name`: Nombre de la hoja actual
- `sheet`: Objeto worksheet activo
- `options`: Configuración para value_input_option

---

#### Métodos de Lectura

##### `read_sheet_data(tab_name=None, skiprows=0, output_format='list')`

Lee todos los datos de una hoja.

**Parámetros:**
- `tab_name` (str, opcional): Nombre de la pestaña
- `skiprows` (int): Filas a saltar desde el inicio
- `output_format` (str): Formato de salida ('list', 'dict', 'pandas')

**Returns:**
- list/dict/DataFrame según `output_format`

**Ejemplo:**
```python
# Como lista
data = conector.read_sheet_data(output_format='list')

# Como diccionarios
data = conector.read_sheet_data(output_format='dict')

# Como DataFrame
df = conector.read_sheet_data(output_format='pandas')
```

---

##### `spreadsheet_read_range(sheet, tab_name, fila_start, fila_end, column_start, column_end)`

Lee un rango específico de celdas.

**Parámetros:**
- `sheet`: Objeto worksheet
- `tab_name` (str): Nombre de la pestaña
- `fila_start` (int): Fila inicial
- `fila_end` (int): Fila final
- `column_start` (str): Columna inicial (ej: 'A')
- `column_end` (str): Columna final (ej: 'D')

**Returns:**
- list[dict]: Lista de diccionarios con `{"fila": int, "values": list}`

---

##### `get_rows_where_column_equals(column, value)`

Busca filas donde una columna tiene un valor específico.

**Parámetros:**
- `column` (int): Índice de columna (0-indexed)
- `value`: Valor a buscar

**Returns:**
- list[tuple]: Lista de tuplas (row_number, row_values)

**Ejemplo:**
```python
# Buscar todas las filas donde la columna A (índice 0) sea 'Activo'
resultados = conector.get_rows_where_column_equals(0, 'Activo')
for num_fila, valores in resultados:
    print(f"Fila {num_fila}: {valores}")
```

---

##### `get_last_row(tab_name=None)`

Obtiene el número de la última fila con datos.

**Parámetros:**
- `tab_name` (str, opcional): Nombre de la pestaña

**Returns:**
- int: Índice de la última fila (0 si está vacía)

---

##### `get_row_with_empty_in_column(sheet, column_letter)`

Encuentra la primera fila con celda vacía en una columna.

**Parámetros:**
- `sheet`: Objeto worksheet
- `column_letter` (str): Letra de la columna (ej: 'B')

**Returns:**
- tuple: (row_values, row_index) o (None, None)

---

#### Métodos de Escritura

##### `spreadsheet_append(data, tab_name=None)`

Agrega filas al final de la hoja.

**Parámetros:**
- `data` (list[list]): Lista de filas a agregar
- `tab_name` (str, opcional): Nombre de la pestaña

**Returns:**
- dict: Resultado de la operación

**Ejemplo:**
```python
nuevas_filas = [
    ['Ana', 'ana@example.com'],
    ['Luis', 'luis@example.com']
]
conector.spreadsheet_append(nuevas_filas, tab_name='Contactos')
```

---

##### `spreadsheet_insert(sheet_name, worksheet_name, data, fila=None)`

Inserta datos en una fila específica o al final.

**Parámetros:**
- `sheet_name` (str): Nombre del documento
- `worksheet_name` (str): Nombre de la hoja
- `data` (list[list]): Datos a insertar
- `fila` (int, opcional): Fila donde insertar (None = al final)

**Returns:**
- dict: Resultado de la operación

**Raises:**
- ValueError: Si los datos no son válidos

---

#### Métodos de Actualización

##### `update_cell(sheet, row_index, col_index, value)`

Actualiza una celda específica.

**Parámetros:**
- `sheet`: Objeto worksheet
- `row_index` (int): Índice de fila (1-indexed)
- `col_index` (int): Índice de columna (1-indexed)
- `value`: Nuevo valor para la celda

**Ejemplo:**
```python
# Actualizar celda B3 (fila 3, columna 2)
conector.update_cell(conector.sheet, 3, 2, 'Nuevo Valor')
```

---

##### `update_row(sheet, row_index, data, start_column=None)`

Actualiza una fila completa o parte de ella.

**Parámetros:**
- `sheet`: Objeto worksheet
- `row_index` (int): Índice de fila
- `data` (list): Valores a escribir
- `start_column` (int, opcional): Columna inicial (por defecto: 1)

**Ejemplo:**
```python
# Actualizar fila 5 completa
conector.update_row(conector.sheet, 5, ['A', 'B', 'C'])

# Actualizar desde columna 3
conector.update_row(conector.sheet, 5, ['X', 'Y'], start_column=3)
```

---

##### `batch_update(range_data, value_input_option='USER_ENTERED')`

Actualiza múltiples rangos en una sola operación (más eficiente).

**Parámetros:**
- `range_data` (list[dict]): Lista de updates con formato:
  ```python
  {"range": "Hoja1!A1:B2", "values": [[val1, val2], [val3, val4]]}
  ```
- `value_input_option` (str): 'USER_ENTERED' o 'RAW'

**Ejemplo:**
```python
updates = [
    {"range": "Ventas!A1:C1", "values": [["Mes", "Producto", "Total"]]},
    {"range": "Ventas!A2:C3", "values": [
        ["Enero", "Widget", 100],
        ["Febrero", "Gadget", 200]
    ]}
]
conector.batch_update(updates)
```

---

#### Métodos de Conexión

##### `connect_to_sheet(doc_name, sheet_name=None)`

Conecta a una hoja específica.

**Parámetros:**
- `doc_name` (str): Nombre del documento
- `sheet_name` (str, opcional): Nombre de la hoja (None = primera)

**Returns:**
- Worksheet: Objeto de hoja de cálculo

**Ejemplo:**
```python
# Cambiar a otra pestaña
nueva_hoja = conector.connect_to_sheet('Mi Documento', 'Ventas 2024')
```

---

## 🧪 Testing

### Ejecutar Tests

```bash
# Instalar dependencias de desarrollo
pip install -e ".[dev]"

# Ejecutar tests
pytest tests/

# Con coverage
pytest --cov=gspreadmanager tests/
```

### Tests Manuales

Crea un archivo `test_manual.py`:

```python
from gspreadmanager import GoogleSheetConector

# Configura tus credenciales
conector = GoogleSheetConector(
    doc_name='Test Sheet',
    json_google_file='credentials.json'
)

# Test 1: Leer datos
print("Test 1: Lectura")
datos = conector.read_sheet_data(output_format='list')
print(f"Leídas {len(datos)} filas")

# Test 2: Escribir datos
print("\nTest 2: Escritura")
test_data = [['Test', 'Data', 'Row']]
conector.spreadsheet_append(test_data)
print("Fila agregada exitosamente")

# Test 3: Buscar
print("\nTest 3: Búsqueda")
resultados = conector.get_rows_where_column_equals(0, 'Test')
print(f"Encontradas {len(resultados)} filas con 'Test'")
```

---

## 📊 Casos de Uso Comunes

### 1. ETL: Exportar datos de base de datos a Sheets

```python
import sqlite3
from gspreadmanager import GoogleSheetConector

# Leer de SQLite
conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute("SELECT nombre, email, telefono FROM usuarios")
usuarios = cursor.fetchall()

# Escribir a Google Sheets
conector = GoogleSheetConector('Reporte Usuarios', 'creds.json')
headers = [['Nombre', 'Email', 'Teléfono']]
conector.spreadsheet_append(headers)
conector.spreadsheet_append(usuarios)
```

### 2. Sincronización periódica

```python
import schedule
import time
from gspreadmanager import GoogleSheetConector

def sync_data():
    conector = GoogleSheetConector('Inventario', 'creds.json')
    # Leer datos de API
    api_data = fetch_from_api()  # Tu función
    # Limpiar hoja (eliminar filas viejas) y escribir nuevas
    conector.sheet.clear()
    conector.spreadsheet_append(api_data)
    print("Sincronización completada")

# Ejecutar cada hora
schedule.every().hour.do(sync_data)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 3. Dashboard con pandas

```python
from gspreadmanager import GoogleSheetConector
import matplotlib.pyplot as plt

# Leer como DataFrame
conector = GoogleSheetConector('Ventas 2024', 'creds.json')
df = conector.read_sheet_data(output_format='pandas')

# Análisis
ventas_por_mes = df.groupby('Mes')['Total'].sum()
ventas_por_mes.plot(kind='bar')
plt.title('Ventas Mensuales')
plt.show()

# Estadísticas
print(df.describe())
```

### 4. Formulario de registro con validación

```python
from gspreadmanager import GoogleSheetConector

def registrar_usuario(nombre, email, telefono):
    conector = GoogleSheetConector('Registro', 'creds.json')
    
    # Verificar si email ya existe
    existentes = conector.get_rows_where_column_equals(1, email)  # Columna B
    if existentes:
        return "Error: Email ya registrado"
    
    # Agregar nuevo usuario
    nueva_fila = [[nombre, email, telefono]]
    conector.spreadsheet_append(nueva_fila)
    return "Usuario registrado exitosamente"

# Uso
resultado = registrar_usuario("Ana García", "ana@example.com", "555-1234")
print(resultado)
```

---

## 🚀 Deployment

### Publicar a PyPI

```bash
# 1. Instalar herramientas
pip install twine wheel

# 2. Crear distribución
python setup.py sdist bdist_wheel

# 3. Subir a PyPI
twine upload dist/*
```

### Uso en Cloud Functions / Lambda

```python
# requirements.txt
GSpreadManager>=1.0.0

# main.py
from gspreadmanager import GoogleSheetConector
import os

def cloud_function(request):
    # Credenciales desde variable de entorno
    creds_json = os.environ.get('GOOGLE_CREDS_JSON')
    
    # Escribir a archivo temporal
    with open('/tmp/creds.json', 'w') as f:
        f.write(creds_json)
    
    # Usar GSpreadManager
    conector = GoogleSheetConector(
        'Mi Hoja',
        '/tmp/creds.json'
    )
    
    datos = conector.read_sheet_data(output_format='dict')
    return {"status": "ok", "rows": len(datos)}
```

---

## 🤝 Contribuir

Las contribuciones son bienvenidas! Por favor:

1. **Fork** el repositorio
2. Crea una **branch** para tu feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. **Push** a la branch (`git push origin feature/AmazingFeature`)
5. Abre un **Pull Request**

### Guía de Estilo

- Seguir PEP 8
- Agregar docstrings a todas las funciones públicas
- Incluir type hints donde sea posible
- Agregar tests para nuevas funcionalidades

### Reportar Bugs

Abre un issue en GitHub con:
- Descripción del bug
- Pasos para reproducirlo
- Comportamiento esperado vs actual
- Versión de Python y dependencias

---

## 📝 Changelog

### v1.0.0 (Actual)
- ✅ Lectura de datos (list, dict, pandas)
- ✅ Escritura (append, insert)
- ✅ Actualización (cell, row, batch)
- ✅ Búsqueda y filtrado
- ✅ Utilidades (last_row, empty_cell)

### Roadmap

- [ ] Soporte para múltiples documentos simultáneos
- [ ] Cache de autenticación
- [ ] Operaciones asíncronas (async/await)
- [ ] CLI para operaciones comunes
- [ ] Soporte para gráficos y fórmulas

---

## 📄 Licencia

MIT License - ver archivo [LICENSE](LICENSE) para detalles.

---

## 🙏 Agradecimientos

- [gspread](https://github.com/burnash/gspread) - Cliente de Google Sheets API
- [oauth2client](https://github.com/googleapis/oauth2client) - Autenticación OAuth2
- [pandas](https://pandas.pydata.org/) - Análisis de datos

---

## 📞 Soporte

- 📧 Email: [tu-email@example.com]
- 🐛 Issues: [GitHub Issues](https://github.com/PabloAlaniz/GSpreadManager/issues)
- 📖 Docs: [Este README]

---

**Hecho con ❤️ por Pablo Alaniz**
