# OCI A1 Capacity Runner en el Poco X3 Pro

El monitor se ejecuta en el chroot Ubuntu ARM64 de TWRP, no dentro de Android ni de una instancia OCI. No usar `systemctl` en el teléfono: systemd está offline. No reiniciar el teléfono para probarlo; las instrucciones del workspace prohíben arranques normales.

## Instalación actual

- Usuario sin shell: `oci-a1` (home privado `/var/lib/oci-a1`, modo `0700`).
- Código de despliegue: `/opt/oci-a1/app` (root, solo lectura para el servicio). Venv ARM64: `/opt/oci-a1/venv` con SDK `oci==2.185.2`.
- Credenciales: `/var/lib/oci-a1/.oci/config` y `api_key.pem` (modo `0600`); la ruta `key_file` del config apunta al PEM local. No copiar estos archivos al repositorio.
- Estado: `/var/lib/oci-a1/.cache/oci-vm/` (modo `0700`), particularmente `runner-state.json`, `status.json`, `runner.log`, `launch.lock` y `cron.lock`.
- ntfy: `/var/lib/oci-a1/.config/oci-a1/ntfy-url` (modo `0600`) contiene una URL privada copiada del `EZARR_NTFY_URL` ya configurado en el teléfono. No imprimirla en logs ni comandos públicos. `phone-supervisor.sh` activa ese canal y desactiva la notificación de escritorio; una publicación de prueba devolvió respuesta HTTP satisfactoria, pero no confirma la recepción en un dispositivo suscrito. Si el runner se detiene por `ENOSPC` (espacio o inodos agotados) o `EDQUOT` (cuota), envía un mensaje específico de **almacenamiento lleno** en lugar del aviso genérico de error local. Solo se detecta si el runner intenta operar y la red de ntfy todavía funciona; no es un monitor preventivo ni cubre todo el teléfono.
- `cron` ya lo inicia el stack bajo TWRP; `/etc/cron.d/oci-a1` invoca `phone-cron.sh` cada minuto. Este usa `flock` para impedir duplicados y `phone_cron.py` espera al runner, registra `last-exit` y no reinicia si este sale con código `2`. El archivo `paused` en el home impide nuevos arranques. Los fallos recuperables se reintentan en el siguiente tick. La primera ejecución después de que cron arranque depende del hook y watchdog existentes; **no se verificó con un reinicio del teléfono**.
- Consulta bajo demanda: `/etc/cron.d/oci-a1-http` mantiene `phone_status.py` en `127.0.0.1:18791`, ejecutado como `oci-a1`; Tailscale Serve publica únicamente esta ruta en la tailnet por HTTPS, puerto 18443. No se configura Cloudflare Funnel ni nginx. Solo devuelve un conjunto permitido de campos, no el estado bruto o las credenciales.
- Resumen diario: `/etc/cron.d/oci-a1-status` ejecuta `phone_status.py --daily` a las **22:22 de America/Mexico_City**. Lee los registros rotados de las últimas 24 horas y envía estado, ciclos y rechazos de capacidad por ntfy. `daily-sent` impide duplicados el mismo día; si falla el envío, cron lo intentará al día siguiente, no dentro de la misma noche. La prueba de ntfy se envió por separado, sin adelantar el resumen programado.

## Consulta sin SSH

Desde un dispositivo conectado a **la misma tailnet de Tailscale**, abre `https://localhost-0.<nombre-tailnet>.ts.net:18443/status` (el nombre completo de la tailnet lo ves con `tailscale status`). El JSON muestra `service`, `result`, `last_update`, `age_seconds`, `stale`, `next_attempt`, `capacity_streak`, `attempts`, `launch_pending` e `instance_state`. No incluye token, OCIDs, IP pública ni URL ntfy. `attempts` es el total acumulado de intentos del monitor; `capacity_streak` es solo la racha de rechazos por capacidad y vuelve a cero en cuanto OCI responde otra cosa. Durante un intento en curso es normal ver `launch_pending` en `true` con `next_attempt` todavía del ciclo anterior. Si `stale=true`, el archivo dejó de actualizarse; si la URL no abre, podrían haber fallado Tailscale, el servicio HTTP, el teléfono o la conectividad, y el último resultado no es prueba de salud actual. Fuera de la tailnet, el enlace no debe responder. Se validó desde la PC usando Tailscale, sin SSH.

No activar Tailscale Funnel para esta ruta. Tailscale Serve debe seguir marcándola `tailnet only`; el backend Python escucha solo en loopback y rechaza peticiones cuyo origen no sea loopback. Si Tailscale no puede obtener certificado o el cliente no está conectado, revisar su estado antes de compartir el enlace.

## Homarr privado

El tablero [MediaServer](https://ezarr.rocks/boards/MediaServer) se cambió a **privado** usando la interfaz de Homarr. Se retiraron sus asignaciones como inicio **global** en escritorio y móvil, conservando las asignaciones personales. Las cuentas locales autorizadas mantienen sus permisos existentes; la cuenta administradora puede editar y la otra puede verlo. Una visita sin sesión a `/` y a `/boards/MediaServer`, tanto por `ezarr.rocks` como por la IP LAN, mostró el formulario de acceso y no el tablero. Homarr aún puede servir recursos estáticos o páginas públicas de inicio de sesión; la restricción comprobada es la del tablero y sus datos.

El widget `OCI A1 · Estado` es un **Custom Widget** de Homarr con `GET http://127.0.0.1:18791/status`, sin token adicional; Homarr consulta desde el propio teléfono. Muestra servicio, último resultado OCI, indicador `Datos obsoletos`, estado de instancia cuando exista, segundos desde la actualización e `Intentos` (`$.attempts`, el total acumulado). Se confirmó que sigue mostrando `running`, `capacity` e `Intentos` después de recargar el tablero. El campo `Intentos` se sembró una sola vez a partir de la racha de capacidad vigente al desplegar el contador (2026-10-18), así que a partir de ahí solo crece. Si `Datos obsoletos` muestra `true`, no confundir el último resultado con salud actual. La URL de Tailscale sigue siendo privada y no se expuso el archivo `status.json`.

Para editar los mapeos se usa `Manage → Custom Widgets → OCI A1 · Estado`. El campo de ruta JSON es un combobox: **primero** hay que pulsar el botón `Test` de la sección *API Connection* (sin él la lista dice "Run a test to browse response fields") y luego elegir el campo de la lista; escribir la ruta a mano no la guarda. `Save` persiste en la tabla `custom_widget_definition` (`display_config`), lo que permite comprobar el cambio con una consulta de solo lectura a `/appdata/db/db.sqlite`. Un campo nuevo no debe llevar unidad: el formulario puede heredar la unidad de la fila anterior.

`local_runner.py` mantiene `attempts` en `runner-state.json`; como el proceso ya está corriendo, un cambio ahí solo surte efecto tras reiniciar el runner (SIGTERM al proceso y esperar el siguiente tick de cron), igual que cualquier otra actualización del runner.

Se guardó una copia consistente de la base SQLite previa al cambio en `/root/homarr-private-backups/db-before-oci-widget-20261018-152105.sqlite` del teléfono (modo `0600`, comprobación de integridad `ok`). Para revertir el **widget**, quitar el elemento del tablero en modo edición y, si ya no se usa, borrar su definición en `Manage → Custom Widgets`. Para revertir la **privacidad**, usar el ajuste de visibilidad de Homarr: hacerlo público volvería a exponer las integraciones y el estado OCI, así que no hacerlo sin una decisión explícita. Una recuperación completa de la base requeriría coordinar parada y backup de Homarr; no sustituir una base activa por la copia directamente.

## Consultas seguras

Desde la PC:

```sh
ssh root@<IP-del-telefono> 'runuser -u oci-a1 -- env HOME=/var/lib/oci-a1 /opt/oci-a1/venv/bin/python /opt/oci-a1/app/local_runner.py --status'
ssh root@<IP-del-telefono> 'runuser -u oci-a1 -- env HOME=/var/lib/oci-a1 /opt/oci-a1/venv/bin/python /opt/oci-a1/app/local_runner.py --check'
ssh root@<IP-del-telefono> 'pgrep -u oci-a1 -af "[l]ocal_runner.py|[p]hone_cron.py"; stat -c "%a %U:%G %n" /var/lib/oci-a1/.cache/oci-vm/runner-state.json'
systemctl --user is-active oci-vm.service
```

`--check` lee OCI y puede revelar identificadores de attachments si los hay; no lanza instancias. `--status` es local. No pegar el contenido completo de los archivos de estado o secretos en un issue. El resultado `capacity` indica falta de capacidad reportada por OCI, no un fallo del traslado. GitHub Actions `capacity.yml` debe seguir `disabled_manually` para no agregar otro lanzador.

## Pausar y reanudar

La pausa preventiva no interrumpe el proceso que ya está corriendo. Para una parada ordenada sin duplicar escritores:

```sh
ssh root@<IP-del-telefono> 'install -m 0600 -o oci-a1 -g oci-a1 /dev/null /var/lib/oci-a1/paused; pkill -TERM -u oci-a1 -f "^/opt/oci-a1/venv/bin/python /opt/oci-a1/app/local_runner.py$" || true'
```

Confirmar que ya no haya proceso `local_runner.py` y que el supervisor haya terminado. `phone_cron.py` guarda `last-exit`; una salida `2` implica fallo permanente, que debe corregirse antes de reiniciar. Para reanudar con el estado conservado, una vez que el otro host esté detenido, retirar `paused` y, **solo después de resolver una salida permanente**, retirar `last-exit` (no `runner-state.json`). Cron lanzará el monitor en el siguiente minuto.

## Reversión a la PC

1. Crear `paused` en el teléfono, mandar SIGTERM al runner y esperar su terminación. No detenerlo a la fuerza en medio de una llamada OCI: si persiste `launch_pending`, la siguiente ejecución debe reconciliar la solicitud antes de volver a lanzar. Confirmar que no haya otro lanzador activo y que el workflow de GitHub permanezca deshabilitado.
2. Trasladar el `runner-state.json` **definitivo** del teléfono a `/home/alan/.cache/oci-vm/runner-state.json` con propietario `alan`, modos `0700` en directorio y `0600` en el archivo; copiar `status.json` opcionalmente. Conservar token, marca de pendiente y eventos notificados. Nunca sustituir el estado por una copia antigua ni borrar una solicitud pendiente.
3. Habilitar e iniciar la unidad instalada en la PC con `systemctl --user enable --now oci-vm.service`, no la plantilla del repositorio. Verificar proceso único y `--status`. La PC necesitará configurar ntfy por separado si se desea conservar este canal tras la reversión.

## Actualizar

Con el servicio pausado, ejecutar pruebas (`./run.sh -m unittest discover -p 'test_*.py' -q`) y actualizar los archivos del runner en `/opt/oci-a1/app`, respetando dueño `root:root` y scripts ejecutables. Actualizar el venv ARM64 si cambia `requirements.txt`; actualizar también `phone_status.py` y `phone-status-cron.sh` cuando corresponda. El backend HTTP se mantiene de forma independiente del runner: sus archivos de cron son `/etc/cron.d/oci-a1-http` y `/etc/cron.d/oci-a1-status`. Para despublicar la URL privada sin afectar los intentos OCI, `tailscale serve --https=18443 off` elimina únicamente esa ruta. No trasladar el venv x86 de la PC ni exponer la URL ntfy en crontab o el repositorio. No modificar `arr-stack`, el watchdog, los montajes ni el cortafuegos como parte del monitor.
