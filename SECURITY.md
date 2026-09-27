# Política de seguridad

## Cómo reportar

Usa el **reporte privado de vulnerabilidades** de GitHub (pestaña *Security* → *Report a vulnerability*). Si no está disponible, abre un issue describiendo el problema sin detalles sensibles y espera contacto.

**Nunca incluyas** en un reporte: API keys, fingerprints, passphrases, contenido de `~/.oci/config`, `runner-state.json`, OCIDs completos, IPs públicas ni logs sin sanear. Rota cualquier credencial que sospeches expuesta.

## Alcance

- Fuga o exposición de credenciales/secretos en el código, workflows o documentación.
- Escalada de privilegios vía el webhook opcional (`OCI_NOTIFY_WEBHOOK`) o la sonda SSH opt-in.
- Validación insuficiente del estado persistente (`runner-state.json`, `status.json`) o de entradas de entorno.
- Escritura fuera del sandbox del servicio (`oci-vm.service`).

## Fuera de alcance

- Disponibilidad de capacidad OCI, límites de cuenta, elegibilidad Always Free o facturación.
- Comportamiento de la instancia creada/monitorizada o del boot volume.
- Requisitos de versión: se atiende siempre la última versión en `main` y el último release.
