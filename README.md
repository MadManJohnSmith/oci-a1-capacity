# OCI A1 Capacity Runner

Monitor local y workflow de GitHub Actions para intentar crear una instancia `VM.Standard.A1.Flex` desde un boot volume existente cuando Oracle Cloud Infrastructure (OCI) informa que vuelve a haber capacidad física.

> **Importante:** este proyecto no garantiza que OCI tenga capacidad, no garantiza la elegibilidad Always Free y no elimina el riesgo de costes. Ejecuta los intentos solo si entiendes las cuotas, permisos y facturación de tu cuenta.

## Por qué existe este proyecto

Este proyecto se creó con una intención concreta: **obtener acceso a los recursos Always Free de OCI**, concretamente volver a levantar una instancia `VM.Standard.A1.Flex` (Ampere A1) desde un boot volume existente. El boot volume conserva un sistema instalado, pero OCI lleva tiempo rechazando cada creación con `Out of host capacity` porque no hay hosts A1 libres en el AD de la región. El runner automatiza el reintento periódico para tomar el primer host que se libere, sin intervención manual.

Ese objetivo encaja con el programa Always Free, que históricamente incluía 4 OCPU y 24 GB de Ampere A1 de uso gratuito continuo. Véase la sección siguiente: Oracle redujo esos límites en 2026.

## Cambio de límites Always Free (junio de 2026)

El **15 de junio de 2026**, Oracle redujo a la mitad el límite Always Free de Ampere A1. El cambio se aplicó sin anuncio público (los avisos por correo aparecieron hacia el 12 de junio y la documentación oficial refleja los nuevos valores desde cerca del 21 de junio de 2026):

| | Antes del 15-jun-2026 | Desde el 15-jun-2026 |
|---|---|---|
| OCPU A1 | 4 | 2 |
| Memoria A1 | 24 GB | 12 GB |
| Consumo mensual equivalente | 3.000 OCPU-h + 18.000 GB-h | 1.500 OCPU-h + 9.000 GB-h |

Consecuencias prácticas:

- Una cuenta Always Free nueva solo puede usar **2 OCPU / 12 GB en total** de A1: una instancia de ese tamaño, o dos de 1 OCPU / 6 GB.
- Con la nueva asignación horaria, una instancia A1 en marcha continua consume el allowance gratuito en ~15–16 días al mes; mantenerse dentro de Always Free puede exigir detener la instancia parte del mes.
- Tenancies PAYG (con método de pago registrado) mantienen 4 OCPU / 24 GB según reportes de la comunidad y confirmaciones de soporte de Oracle.

La configuración por defecto de este proyecto (2 OCPU / 12 GB) ya coincide con el nuevo límite Always Free. La combinación 4/24 sigue disponible vía `OCI_OCPUS`/`OCI_MEMORY_GB` para quien conserve el límite anterior.

## Inicio rápido

Requisito previo único: la configuración estándar del CLI de OCI en `~/.oci/config` (perfil `DEFAULT`) con permisos para leer el boot volume, sus attachments y crear una instancia desde él.

```sh
python3 -m venv ~/venvs/oci-official          # la ruta que run.sh usa por defecto
~/venvs/oci-official/bin/pip install -r requirements.txt
./run.sh local_runner.py --check              # verificación read-only del boot volume
./run.sh local_runner.py --status             # último resultado del monitor

# Monitor persistente como servicio de usuario:
cp oci-vm.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now oci-vm.service
journalctl --user -u oci-vm.service -f
```

Con eso el runner queda intentando cada 5 minutos y avisando en escritorio/webhook cuando la instancia arranque. Si prefieres otro venv, exporta `OCI_VENV=/ruta/al/venv` antes de usar `run.sh`. El resto de este documento detalla el comportamiento, la configuración opcional y los riesgos.

## Público objetivo

Este repositorio está dirigido a:

- Operadores de OCI que conocen compartments, boot volumes, VCN/subnets, policies y API keys.
- Mantenedores de repositorios GitHub que entienden secretos, permisos de workflows y ramas protegidas.
- Usuarios de Linux con experiencia básica en Python, entornos virtuales y servicios `systemd --user`.

No es un servicio administrado, un sistema de alta disponibilidad ni un tutorial para cuentas OCI sin configurar. El operador es responsable de validar región, cuotas, red, costes, seguridad y estado de la cuenta.

## Qué hace

- Consulta el boot volume configurado y todos sus attachments.
- Intenta crear una instancia A1 con un token de reintento estable.
- Reintenta de forma secuencial y con backoff cuando OCI devuelve falta de capacidad.
- Conserva el estado local para sobrevivir a reinicios.
- Se detiene ante una respuesta ambigua que podría haber aceptado un lanzamiento, para reconciliar antes de crear otra instancia.
- Puede monitorizar una instancia encontrada; no la inicia, detiene ni termina.
- Ofrece comprobaciones de solo lectura y un informe local sanitizable.

## Qué no hace

- No fabrica capacidad física ni reserva una instancia.
- No garantiza Always Free, ausencia de cargos ni disponibilidad de red/IP pública.
- No inyecta claves SSH ni modifica el contenido del boot volume.
- No coordina automáticamente equipos distintos, otro repositorio o un runner de GitHub con el monitor local.
- No termina recursos existentes ni limpia recursos automáticamente.
- No debe ejecutarse simultáneamente desde varios operadores contra el mismo boot volume.

## Definiciones

- **Boot volume:** volumen de arranque desde el que se crea la instancia.
- **Attachment:** relación entre un boot volume y una instancia. Un attachment activo bloquea un nuevo intento.
- **Capacidad física:** disponibilidad real de hosts A1 en el AD; es distinta de una cuota libre.
- **Cuota:** límite administrativo de OCPU, memoria, almacenamiento u otros recursos. Una cuota libre no prueba capacidad física.
- **Always Free:** programa de facturación con condiciones de cuenta, región, recursos y consumo. Este proyecto no puede determinar por sí solo la elegibilidad.
- **Token de reintento:** identificador enviado a OCI para que solicitudes repetidas puedan deduplicarse durante su ventana de validez.
- **Lanzamiento ambiguo:** timeout, error de red o caída del proceso después de enviar una solicitud, pero antes de conocer su respuesta.
- **Reconciliación:** consulta posterior de attachments/estado para decidir si OCI creó o no la instancia antes de reintentar.
- **Backoff y jitter:** espera creciente y variación aleatoria acotada para reducir presión y sincronización con otros clientes.

## Datos de creación configurados

Los valores estructurales están definidos en `launch.py`. La configuración solicitada por defecto es:

| Parámetro | Valor |
|---|---|
| Región | `mx-queretaro-1` |
| Availability Domain | `KsWN:MX-QUERETARO-1-AD-1` |
| Shape | `VM.Standard.A1.Flex` |
| OCPU | `2` |
| Memoria | `12 GB` |
| Display name | `oci-a1-capacity` en el intento único; `oci-a1` en el monitor local |
| Boot volume | OCID configurado en `launch.py` |
| Subnet | OCID configurado en `launch.py` |
| IP pública | Se solicita (`assign_public_ip=True`) |
| Claves SSH | No se inyectan |
| Disco | Se conserva el contenido del boot volume existente |
| Acciones sobre instancias existentes | Solo lectura/monitorización |

`OCI_OCPUS` y `OCI_MEMORY_GB` permiten seleccionar otra combinación Flex válida entre 1–4 OCPU, 6–12 GB por OCPU y 24 GB como máximo. Una configuración válida no garantiza que la cuota o la capacidad estén disponibles.

**Configuración solicitada no significa instancia creada.** Comprueba siempre `--check`, `--status`, los attachments de OCI y el estado de la instancia. El último estado conocido del proyecto puede seguir siendo `capacity` sin instancia creada.

## Diagramas

Se entregan dos diagramas standalone con SVG inline, temas claro/oscuro, búsqueda y exportación desde el visor:

- [Arquitectura del sistema](oci-a1-architecture.html) — componentes locales, OCI, estado y límites de seguridad.
- [Flujo seguro de lanzamiento](oci-a1-flow.html) — comprobación, capacidad, aceptación y reconciliación de solicitudes ambiguas.

Las especificaciones editables son `oci-a1-architecture.json` y `oci-a1-flow.json`. Se validan con Archify en perfil `showcase`. El diagrama de arquitectura también pasó la comprobación automatizada de navegador; el flujo pasó validación semántica y de composición, pero su viewer puede requerir scroll vertical en algunos escritorios por el panel de tarjetas.

## Arquitectura

```text
launch.py
  └─ intento único o comprobación read-only

local_runner.py
  ├─ lock local
  ├─ runner-state.json (token, pending, instancia y backoff)
  ├─ status.json (último resultado sanitizado)
  ├─ runner.log (operaciones y tiempos)
  └─ reconciliación antes de volver a lanzar

check_local.py
  └─ assessment read-only de OCI, cuotas y almacenamiento

.github/workflows/
  ├─ capacity.yml (intentos OCI y dispatch de capacidad)
  └─ ci.yml (tests y compilación sin secretos)

oci-vm.service
  └─ monitor persistente como servicio systemd --user
```

## Requisitos

- Cuenta OCI con la región y recursos configurados.
- Python compatible con el SDK fijado.
- `oci==2.185.2`, fijado en `requirements.txt`.
- Linux si se desea utilizar el servicio `systemd --user`.
- Para GitHub Actions: repositorio con secretos y permisos de workflow configurados.
- Una identidad OCI con permisos mínimos para leer el boot volume y attachments, consultar la red y crear una instancia desde ese volumen.

Consulta las policies de tu tenancy y compartment antes de ejecutar. No otorgues permisos administrativos globales solo para probar este proyecto.

## Configuración de credenciales

### GitHub Actions

Crea estos secretos del repositorio:

- `OCI_CONFIG`: contenido INI con sección `[DEFAULT]`, `user`, `fingerprint`, `tenancy` y, si corresponde, `pass_phrase`. El `key_file` puede existir, pero el script lo sustituye por un archivo temporal.
- `OCI_API_KEY`: contenido completo de la clave privada PEM correspondiente.

Los secretos se escriben temporalmente y no deben aparecer en logs, issues, reportes ni commits. Rota la API key si sospechas que fue expuesta.

### Ejecución local

No guardes credenciales en el repositorio. Usa variables de entorno o el archivo estándar de OCI con permisos restrictivos. Para el monitor local, `clients()` usa la configuración OCI local del usuario; `launch.py` hace lo mismo cuando no detecta los secretos de Actions.

Variables habituales:

| Variable | Uso | Valor por defecto |
|---|---|---|
| `OCI_REPOSITORY` | Repositorio estable para el token de `launch.py` | `local/oci-a1-capacity` fuera de GitHub |
| `GITHUB_REPOSITORY` | Repositorio usado automáticamente en Actions | lo proporciona GitHub |
| `OCI_OCPUS` | OCPU Flex solicitadas | `2` |
| `OCI_MEMORY_GB` | Memoria solicitada | `12` |
| `OCI_CAPACITY_DELAY` | Retardo inicial de capacidad, 10–300 s | `10` |
| `OCI_CAPACITY_MAX_DELAY` | Tope del retardo de capacidad, 10–300 s | `300` |
| `OCI_VENV` | Entorno usado por comandos documentados | depende del shell |
| `OCI_NOTIFY_WEBHOOK` | Webhook HTTPS opcional | desactivado |
| `OCI_NOTIFY_WEBHOOK_HOSTS` | Hosts permitidos para el webhook | ninguno; webhook rechazado |
| `OCI_ENABLE_SSH_PROBE` | Habilita prueba TCP/banner SSH opt-in | desactivado |

Los webhooks requieren HTTPS y, para ser aceptados, un host incluido en `OCI_NOTIFY_WEBHOOK_HOSTS`.

## Instalación local

Desde la raíz del repositorio. El lanzador `run.sh` ejecuta el intérprete de `~/venvs/oci-official` por defecto (o el de `OCI_VENV` si lo defines), así que crea el venv en esa ruta para que todos los comandos documentados funcionen sin más:

```sh
python3 -m venv ~/venvs/oci-official
~/venvs/oci-official/bin/python -m pip install -r requirements.txt
```

Si usas otra ruta, exporta `OCI_VENV` en tu shell o en el servicio. El lanzador limpia variables de entorno problemáticas:

```sh
./run.sh -m unittest discover -v
./run.sh local_runner.py --check
```

## Comandos

### Intento único

```sh
./run.sh launch.py --check   # solo lectura
./run.sh launch.py           # como máximo una llamada de lanzamiento
```

`launch.py --check` no lanza una instancia y no deshabilita workflows. La salida `ready` solo significa que el boot volume está disponible y sin attachments activos; no demuestra capacidad física.

**Ejecución local:** si no hay secretos exportados, `launch.py` lee la configuración estándar de `~/.oci/config` y usa el repositorio estable `local/oci-a1-capacity` para el token de reintento. En GitHub Actions sigue usando los secretos `OCI_CONFIG`/`OCI_API_KEY` y `GITHUB_REPOSITORY`; si defines solo uno de los dos secretos, termina con error en lugar de mezclar orígenes de credenciales.

### Monitor persistente

```sh
./run.sh local_runner.py --check
./run.sh local_runner.py --status
./run.sh local_runner.py
```

`--status` lee únicamente `status.json`. El monitor usa `~/.cache/oci-vm/` con permisos restrictivos y guarda:

- `runner-state.json`: token persistente, `launch_pending`, instancia conocida y backoff.
- `status.json`: resultado y próxima acción.
- `runner.log`: operaciones, categorías y duraciones sin cuerpos crudos del SDK.
- `launch.lock`: exclusión local entre procesos.

### Assessment read-only

```sh
./run.sh check_local.py
./run.sh check_local.py --markdown
```

`--markdown` genera un borrador basado en el assessment y el log local. Revísalo antes de publicarlo: no sustituye una auditoría humana y no debe incluir OCIDs, IPs, credenciales ni logs sin sanear.

## Servicio systemd de usuario

El archivo `oci-vm.service` es una plantilla para instalación local:

```sh
mkdir -p ~/.config/systemd/user
cp oci-vm.service ~/.config/systemd/user/oci-vm.service
systemctl --user daemon-reload
systemctl --user enable --now oci-vm.service
systemctl --user status oci-vm.service
journalctl --user -u oci-vm.service -f
```

El servicio aplica `UMask=0077`, `NoNewPrivileges`, `PrivateTmp`, protección del sistema de archivos, límites de reinicio y restricción de familias de red. `ProtectHome=read-only` permite leer la configuración pero solo declara como escribible la caché del runner.

No ejecutes simultáneamente este servicio y el workflow de capacidad contra el mismo boot volume. El lock local no coordina máquinas diferentes.

## GitHub Actions

**Estado actual (septiembre de 2026):** el workflow `capacity.yml` está deshabilitado manualmente en GitHub. El mecanismo activo es el monitor local (`oci-vm.service`), que corre de forma permanente. Re-habilita el workflow temporalmente desde la pestaña Actions solo cuando la máquina local vaya a estar apagada, y en ese caso detén el monitor local para no lanzar contra el mismo boot volume desde dos sitios.

### `capacity.yml`

Se dispara por:

- programación cron;
- `workflow_dispatch` manual, con opción `check` read-only;
- `repository_dispatch` de tipo `retry`.

El workflow tiene `contents: read` y `actions: write`. Tras una respuesta `launched`, intenta deshabilitarse usando `github.token`. La aceptación no significa que la instancia esté `RUNNING`.

El workflow puede consumir minutos y generar costes. GitHub puede retrasar u omitir cron, y los workflows programados requieren estar disponibles en la rama predeterminada.

### `ci.yml`

Ejecuta tests y compilación Python sin secretos ni permisos de escritura:

```sh
python -m unittest discover -v
python -m py_compile launch.py local_runner.py check_local.py test_launch.py test_runner.py
```

No habilites el workflow de capacidad mientras el monitor local esté activo.

## Seguridad y comportamiento ante fallos

1. Antes de lanzar, se verifican el estado del boot volume y los attachments.
2. Un resultado conocido de `500 InternalError` con `Out of host capacity` se trata como falta de capacidad.
3. Un timeout o error de red después de preparar el lanzamiento se trata como ambiguo: se conserva `launch_pending` y se detiene para reconciliar.
4. Si aparece un attachment válido, se guarda la instancia y se monitoriza; no se lanza una segunda instancia.
5. Errores 429 respetan `Retry-After` con tope de 600 s y backoff exponencial.
6. Los retardos incorporan jitter acotado para evitar sincronización entre clientes.
7. El estado local se valida por tipo, tamaño, propietario, permisos y estructura básica.
8. La sonda SSH está desactivada por defecto. No se registran banners ni IPs salvo que se habilite explícitamente.
9. Los errores del SDK se reducen a tipo/categoría/estado HTTP; no se publican mensajes ni cuerpos crudos.

### Estados importantes

| Estado | Significado | Acción recomendada |
|---|---|---|
| `ready` | Boot volume disponible y sin attachment | Puede intentarse un lanzamiento |
| `capacity` | OCI rechazó por falta de host | Esperar el siguiente intento |
| `accepted` | OCI aceptó y devolvió una instancia | Verificar estado/attachment |
| `monitor` | Hay una instancia conocida | No lanzar otra; observar |
| `reconcile_required` | Una solicitud podría haber sido aceptada | Detener y revisar OCI antes de borrar estado |
| `permanent_error` | Error de configuración, validación o política | Corregir causa y revisar estado |
| `permanent_local_error` | Fallo local al iniciar o persistir estado | Revisar permisos, caché y entorno |

### Recuperación segura

Si aparece `reconcile_required`:

```sh
./run.sh local_runner.py --status
./run.sh local_runner.py --check
./run.sh check_local.py
```

Después revisa attachments e instancias desde la consola o CLI de OCI. No borres `runner-state.json`, no cambies el token y no reinicies con un token nuevo hasta confirmar que no existe una instancia creada.

## Costes y límites

- OCI puede cobrar cómputo, IP pública, red, almacenamiento, backups u otros consumos según la cuenta.
- GitHub Actions consume minutos y puede cobrar según el plan.
- Una cuota libre no prueba capacidad física.
- Always Free depende de la cuenta, región principal, límites y consumo total. Desde el 15 de junio de 2026 el límite A1 Always Free es de 2 OCPU / 12 GB (antes 4 OCPU / 24 GB); véase la sección «Cambio de límites Always Free».
- El lock es solo local; no existe exclusión global entre máquinas.
- OCI puede caducar o invalidar tokens de reintento.
- El programa no termina instancias ni recursos creados por el operador.

## Pruebas y mantenimiento

Ejecuta antes de cada cambio:

```sh
./run.sh -m unittest discover -v
./run.sh -m py_compile launch.py local_runner.py check_local.py test_launch.py test_runner.py
git diff --check
```

Al actualizar `oci`:

1. Prueba primero en una rama.
2. Ejecuta toda la suite sin secretos.
3. Ejecuta `--check` contra OCI, nunca el lanzamiento como prueba automática.
4. Revisa cambios de timeouts, modelos y políticas.
5. Actualiza la versión fijada y documenta la revisión.

## Privacidad y contribuciones

No abras issues ni pull requests con:

- API keys, fingerprints, passphrases o archivos OCI;
- OCIDs completos si no son necesarios;
- IPs públicas, logs sin sanear o `runner-state.json`;
- secretos de GitHub o capturas de configuración.

Para contribuir:

1. Crea una rama.
2. Añade tests para cambios de comportamiento.
3. Ejecuta la suite y la compilación.
4. Revisa permisos y exposición de datos.
5. Describe claramente si el cambio puede realizar llamadas OCI.

## Licencia

Este proyecto se distribuye bajo la [licencia MIT](LICENSE).

## Estado operativo

El histórico de reportes horarios manuales se retiró del repositorio; sus observaciones de ventanas concretas no eran garantías actuales. Para conocer el estado real, usa `--status`, `--check` y `check_local.py` descritos arriba.
