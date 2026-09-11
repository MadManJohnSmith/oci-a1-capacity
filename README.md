# OCI A1: un intento por ejecución

Lanza `VM.Standard.A1.Flex` (2 OCPU, 12 GB) en `mx-queretaro-1` desde el volumen de arranque existente indicado en `launch.py`. Usa el compartimento del volumen y la subred configurada. No inyecta claves SSH ni modifica el contenido del volumen; conserva su configuración. Nunca inicia ni termina instancias existentes.

## Configuración

Cuando decidas publicar estos archivos en GitHub, crea dos secretos del repositorio:

- `OCI_CONFIG`: configuración OCI en formato INI con sección `[DEFAULT]`, `user`, `fingerprint`, `tenancy` y, si procede, `pass_phrase`. Puede incluir `key_file`: se sustituye por la ruta temporal de la clave. La región se fija en el script y la tenencia debe coincidir con la configurada.
- `OCI_API_KEY`: contenido completo de la clave privada PEM correspondiente.

La identidad necesita permisos para leer el volumen y sus attachments, crear la instancia desde ese volumen y utilizar la subred/VNIC. Los secretos se escriben temporalmente con permisos `0600` y se eliminan al salir; no se imprimen mensajes ni cuerpos de errores del SDK.

El workflow se ejecuta cada 10 minutos y manualmente; GitHub puede retrasar u omitir ejecuciones programadas, que requieren el workflow en la rama predeterminada. La concurrencia serializa ejecuciones de este workflow en el mismo repositorio. Tras una respuesta satisfactoria de lanzamiento, se deshabilita mediante `gh api`, usando `github.token` con `actions: write`. Esto confirma aceptación, no que la instancia ya esté `RUNNING`. Un fallo al deshabilitar marca la ejecución como fallida; los siguientes intentos vuelven a comprobar el volumen.

## Ejecución local

Instala `requirements.txt` en un entorno virtual. Exporta los dos secretos anteriores sin guardarlos en Git y define `OCI_REPOSITORY=propietario/repositorio` con el mismo nombre estable que tendrá GitHub. `GITHUB_REPOSITORY`, si existe, tiene prioridad.

```sh
env -u __PYVENV_LAUNCHER__ python -m pip install -r requirements.txt
env -u __PYVENV_LAUNCHER__ python launch.py --check
env -u __PYVENV_LAUNCHER__ python launch.py
python -m unittest discover -v
```

`--check` solo consulta OCI: no lanza ni deshabilita el workflow y no demuestra que haya capacidad. También está disponible como casilla manual del workflow. Las pruebas usan mocks y no acceden a OCI.

## Seguridad y límites

- Consulta todos los attachments del volumen y omite el lanzamiento si alguno no está `DETACHED` o el volumen no está `AVAILABLE`.
- Hace una sola llamada de lanzamiento, sin reintentos internos. El token determinista SHA-256 combina repositorio y volumen: los intentos tras respuestas ambiguas reutilizan el mismo token. No cambies ese identificador ni ejecutes copias concurrentes desde otros repositorios o equipos.
- OCI caduca tokens a las 24 horas y puede invalidarlos antes. Las comprobaciones no son un bloqueo atómico; no se garantiza exclusión global frente a otros actores ni idempotencia indefinida.
- Solo `500 InternalError` con `Out of host capacity` se trata como falta de capacidad normal. Autenticación, configuración, cuotas, errores de red y otros fallos producen salida no cero sin revelar detalles sensibles.
- La elegibilidad **Always Free no está garantizada**: verifica tu cuenta, región principal, cuotas y consumos de cómputo, almacenamiento y red. GitHub Actions consume minutos y puede generar costes según el plan.

SDK fijado a `oci==2.185.2`, versión consultada en el entorno local oficial.

## Monitor local persistente

El repositorio remoto existe; el workflow de GitHub está deshabilitado manualmente (verificación: 2026-09-11). No lo habilites mientras el servicio local esté activo.

`local_runner.py` usa la configuración OCI local, un bloqueo local y un token persistente. La espera de capacidad empieza en 10 segundos y nunca baja de 10; tras más de tres respuestas consecutivas de capacidad aumenta 10 segundos por respuesta, hasta 300. Una aceptación reinicia el retardo y la racha. `OCI_CAPACITY_DELAY` permite fijar el valor inicial entre 10 y 300 segundos. Cada ciclo realiza como máximo un lanzamiento secuencial, sin ráfagas, concurrencia ni reintentos internos del SDK. HTTP 429 aplica una espera exponencial de 30, 60, 120… hasta 600 segundos, respetando cualquier `Retry-After` mayor (segundos o fecha HTTP, cabecera sin distinción de mayúsculas). Los demás errores recuperables esperan al menos 300 segundos y el monitor espera 300. Se conserva el retardo, la racha y la espera pendiente al reiniciar el servicio local, sin renovar el token. El estado y log registran operaciones/estados HTTP, categoría de respuesta, duración del ciclo, rachas, espera programada real y `Retry-After` numérico; no registran cabeceras ni errores crudos. Se detiene ante errores permanentes o al caducar su ventana de seguridad de 23 horas sin instancia conocida: requiere reconciliación manual, no borrar el estado ni renovar el token a ciegas. Si encuentra una instancia, solo la monitoriza; no la inicia, detiene ni termina. El bloqueo no excluye otros equipos ni GitHub.

Comprobaciones reales de solo lectura, usando el Python del entorno virtual OCI:

```sh
env -u PYTHONHOME -u PYTHONPATH -u __PYVENV_LAUNCHER__ "$OCI_VENV/bin/python" local_runner.py --check
env -u PYTHONHOME -u PYTHONPATH -u __PYVENV_LAUNCHER__ "$OCI_VENV/bin/python" check_local.py
```

Define `OCI_VENV` con el directorio de tu entorno ya instalado. El monitor inicializa su caché local; `check_local.py` requiere esa caché y guarda allí la evaluación. No publiques configuración, estado ni logs sin sanear. Las cuotas y el almacenamiento visible no garantizan capacidad física, ausencia de cargos ni elegibilidad Always Free. Las notificaciones de escritorio son de mejor esfuerzo; consulta también el estado y los logs locales.

Las revisiones manuales y sus límites se documentan en [reports/hourly-reviews.md](reports/hourly-reviews.md).
