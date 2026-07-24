# Acceso a la Abogacía - Estudio

Aplicación web privada, de uso personal, para estudiar el examen de acceso a
la abogacía en España: parte común y especialidad de Derecho penal.

No incluye ninguna IA integrada: las preguntas se generan fuera de la
aplicación (por ejemplo, con un asistente de IA en una conversación aparte)
y se importan por CSV/JSON, o se añaden manualmente desde un formulario.

La aplicación se despliega en **Streamlit Community Cloud** para poder
acceder desde cualquier ordenador o móvil, y guarda todos los datos
(incluidos los documentos subidos) en **Turso**, una base de datos SQLite
alojada en la nube, para que nada se pierda entre reinicios o redespliegues.

## Requisitos

- Python 3.11 o superior (para desarrollo/pruebas en local).
- Una cuenta gratuita en [Turso](https://turso.tech) (base de datos).
- Una cuenta gratuita en [Streamlit Community Cloud](https://streamlit.io/cloud) (para el despliegue accesible desde cualquier sitio).
- Una cuenta de GitHub (para conectar el repositorio con Streamlit Cloud).
- Conexión a Internet para usar la aplicación: **no funciona completamente
  offline**, a diferencia de una versión puramente local, porque los datos
  viven en Turso.

## Instalación en local (desarrollo/pruebas)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edita .streamlit/secrets.toml con tus credenciales de Turso y tu contraseña
streamlit run app.py
```

En Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
streamlit run app.py
```

## Despliegue en Streamlit Community Cloud (para acceso desde cualquier sitio)

1. Crea una base de datos gratuita en [Turso](https://turso.tech) y anota su URL (`libsql://...`) y su token de autenticación.
2. Sube el proyecto a un repositorio de GitHub (puede ser privado).
3. Entra en [Streamlit Community Cloud](https://streamlit.io/cloud) y conecta ese repositorio, seleccionando `app.py` como archivo principal.
4. En el panel "Secrets" de la app, añade:
   ```toml
   TURSO_DATABASE_URL = "libsql://tu-base-de-datos.turso.io"
   TURSO_AUTH_TOKEN = "tu-token-de-turso"
   APP_PASSWORD = "elige-tu-propia-contraseña"
   ```
5. Despliega. La app queda accesible desde una URL pública, protegida por tu contraseña.
6. Cada vez que subas cambios al repositorio, la app se redespliega
   automáticamente; tus datos no se pierden porque viven en Turso, no en el
   propio servidor de Streamlit.

## Flujo de trabajo recomendado para generar preguntas

Este es el corazón de cómo se alimenta la app sin IA integrada:

1. Sube o abre tus apuntes/legislación/exámenes en un asistente de IA de tu
   elección (por ejemplo, en una conversación de Claude aparte).
2. Pide que te genere preguntas tipo test en formato CSV según la plantilla
   incluida en [`data/exports/plantilla_preguntas.csv`](data/exports/plantilla_preguntas.csv).
3. Revisa las preguntas generadas (contenido jurídico, referencias legales,
   que no haya errores).
4. Ve a "Añadir preguntas" → "Importar por CSV/JSON" en la aplicación y
   súbelas.
5. Empieza a estudiar.

## Uso inicial

1. (Opcional) Abre "Material" y sube un PDF para tenerlo organizado.
2. Ve a "Añadir preguntas" e importa tu primer lote (o añade alguna
   manualmente).
3. Ve a "Estudiar" y empieza un test.

## Copias de seguridad

Usa "Exportar base de datos" / "Exportar preguntas" en "Configuración"
periódicamente, y guarda esos archivos exportados en tu propio ordenador o
nube personal. Turso también permite exportar/hacer backup de la base de
datos desde su propio panel, como red de seguridad adicional.

## Ejecutar las pruebas

```bash
source .venv/bin/activate
python -m pytest
```

Las pruebas usan un archivo SQLite local temporal a través del mismo
cliente de Turso (`libsql-client`), no una base de datos Turso remota.

## Limitaciones

- No hay OCR: los PDF escaneados sin texto seleccionable no se pueden
  consultar en texto.
- La aplicación no genera ni valida preguntas por sí misma: la calidad
  depende de la revisión que hagas tú antes de importarlas.
- Las preguntas importadas deben considerarse material de estudio propio,
  no oficial, salvo que procedan de la importación de exámenes reales.
- La legislación y referencias deben comprobarse cuando sean importantes.
- La aplicación no ofrece asesoramiento jurídico.
- Necesita conexión a Internet para funcionar, ya que los datos viven en
  Turso.
- La protección de acceso es una contraseña simple, no un sistema de
  seguridad avanzado: suficiente para uso personal, no para datos altamente
  sensibles.
- Los planes gratuitos de Turso y de Streamlit Community Cloud tienen
  límites de uso; para un solo usuario estudiando son más que suficientes,
  pero si algún día se supera el límite gratuito, habría que pasar a un
  plan de pago o revisar el volumen de datos guardado.

## Funciones disponibles

- **Inicio**: resumen de documentos, preguntas activas/oficiales/propias,
  preguntas pendientes de repaso, % de aciertos global y por parte, últimos
  tests realizados, acceso rápido a repasar errores o lanzar un test rápido.
- **Material**: subir PDF/DOCX/PPTX/TXT/MD (clasificados por área, tema,
  tipo e idioma), extracción y previsualización de texto, descarga del
  archivo original, reprocesado y eliminación (con la opción de conservar
  o borrar las preguntas vinculadas).
- **Añadir preguntas**: importación por CSV/JSON con vista previa fila a
  fila (válidas/inválidas con motivo) y selección de qué importar, más un
  formulario manual. Plantilla CSV descargable.
- **Estudiar**: tests personalizados filtrando por área, tema, idioma,
  dificultad, tipo de pregunta, origen (oficial/propia), documento, número
  de preguntas, solo nunca respondidas o solo falladas; modo aprendizaje
  (feedback inmediato con explicación y referencias) o modo examen
  (resultados al finalizar); marcar preguntas para revisar; nivel de
  confianza por respuesta.
- **Simulacro**: modalidad personalizada o con la configuración guardada;
  dos partes (común y penal) con su propio límite de tiempo, navegación
  libre entre preguntas, respuestas en blanco, puntuación final ponderada
  y repaso de respuestas al terminar.
- **Preguntas oficiales**: importación por CSV/JSON con los mismos
  controles de validación, filtro por área/año/estado, identificación de
  anuladas y de reserva (excluidas de los tests normales salvo que se
  active la opción correspondiente en Configuración).
- **Errores**: cuaderno de preguntas falladas con filtros (área, tema,
  varios fallos, marcadas), repaso agrupado o pregunta a pregunta, marcar
  como dominada y reiniciar progreso.
- **Estadísticas**: preguntas respondidas/aciertos/errores/blancos, % de
  acierto, puntuación media, resultado por área/tema/dificultad/tipo,
  evolución de los últimos tests, tiempo medio por pregunta, preguntas más
  falladas, aciertos respondidos con inseguridad, simulacros realizados.
- **Configuración**: idioma de la interfaz, valores del simulacro (número
  de preguntas, tiempos, penalización, pesos, preguntas anuladas),
  exportación de preguntas (CSV/JSON) y de la base de datos completa
  (JSON, con los archivos originales en base64), y borrado total de datos
  con confirmación explícita.
- **Catalán / castellano** en toda la interfaz, con castellano como
  idioma de respaldo.
- **Acceso protegido** por contraseña única, con bloqueo temporal tras
  varios intentos fallidos.

## Estructura final del proyecto

```text
app.py                          Punto de entrada, autenticación y navegación
pages/                          Una página por sección del menú
services/                       Lógica de negocio (BD, auth, extracción, tests, puntuación...)
repositories/                   Acceso a datos (SQL) sobre Turso/SQLite
models/                         Modelos de datos ligeros (dataclasses)
translations/es.json, ca.json   Textos de la interfaz
data/exports/                   Plantillas CSV descargables
tests/                          Pruebas con pytest (55 pruebas)
.streamlit/                     Configuración y plantilla de secretos
```

## Resultado de las pruebas

Todas las pruebas pasan (`python -m pytest`): pruebas unitarias de base de
datos, extracción de texto, importación/validación de preguntas,
puntuación (simulacro incluido), exportación de datos, y pruebas de humo
que arrancan la aplicación real página por página (incluyendo flujos
completos de un test de estudio y de un simulacro de principio a fin) para
detectar errores de ejecución.

## Limitaciones conocidas

- No hay reconocimiento óptico de caracteres (OCR): los PDF escaneados sin
  texto seleccionable no se pueden consultar en texto.
- El simulacro no puede finalizar una parte de forma completamente
  autónoma en segundo plano sin que haya alguna interacción del usuario,
  ya que Streamlit no ofrece temporizadores del lado servidor sin
  dependencias adicionales; el tiempo restante se recalcula en cada
  interacción (responder, navegar, o pulsar "Actualizar tiempo restante"),
  y en cuanto se detecta que el tiempo ha vencido la parte se cierra
  automáticamente antes de aceptar más respuestas.
- La aplicación no genera ni valida preguntas por sí misma: la calidad
  depende de la revisión que hagas tú antes de importarlas.
- Las preguntas importadas deben considerarse material de estudio propio,
  no oficial, salvo que procedan de la importación de exámenes reales.
- La legislación y referencias deben comprobarse cuando sean importantes.
- La aplicación no ofrece asesoramiento jurídico.
- Necesita conexión a Internet para funcionar, ya que los datos viven en
  Turso.
- La protección de acceso es una contraseña simple, no un sistema de
  seguridad avanzado: suficiente para uso personal, no para datos altamente
  sensibles.
- Los planes gratuitos de Turso y de Streamlit Community Cloud tienen
  límites de uso; para un solo usuario estudiando son más que suficientes,
  pero si algún día se supera el límite gratuito, habría que pasar a un
  plan de pago o revisar el volumen de datos guardado.

## Posibles mejoras futuras

- Repetición espaciada más avanzada para el repaso de errores.
- Edición de preguntas ya guardadas desde la propia interfaz (hoy se
  eliminan y se vuelven a importar/añadir).
- Búsqueda de texto libre dentro del contenido extraído de los documentos.
- Sincronización/backup automático periódico hacia un almacenamiento
  externo, además de la exportación manual.

