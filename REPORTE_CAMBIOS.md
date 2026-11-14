# Reporte de Cambios y Correcciones Realizadas

Este documento detalla todas las modificaciones efectuadas en el proyecto **Sistema de Incidencias**, explicando el problema detectado, el motivo técnico del fallo y la solución implementada.

---

## 1. Script de Inicio para Linux (`Iniciar_Sistema.sh`)

* **Archivo modificado:** `Iniciar_Sistema.sh`
* **Problema:** Al ejecutar el script en Linux, el navegador se abría inmediatamente mostrando un error de conexión (*"No se puede conectar con el servidor"* / *Connection Refused*). Además, la consola quedaba congelada sin ningún mensaje visible.
* **Causa técnica:**
  1. `xdg-open http://127.0.0.1:8000/panel` se ejecutaba de forma síncrona **antes** de que el servidor Uvicorn comenzara a escuchar conexiones en el puerto 8000.
  2. El parámetro `--log-level warning` ocultaba los mensajes informativos habituales de arranque del servidor.
  3. No se validaba la existencia de la carpeta del entorno virtual `venv`.
* **Solución aplicada:**
  * Se agregó verificación de existencia de la carpeta `venv`.
  * La apertura del navegador se trasladó a segundo plano con un temporizador de 2 segundos: `(sleep 2 && xdg-open ...) &`, asegurando que el servidor ya esté operativo cuando el navegador consulte la URL.
  * Se cambió a `--log-level info` y se habilitó `--reload` para facilitar el monitoreo del servidor en desarrollo.

---

## 2. Dependencias de Base de Datos (`requirements.txt`)

* **Archivo modificado:** `requirements.txt`
* **Problema:** Al instalar dependencias en un entorno nuevo mediante `pip install -r requirements.txt` e iniciar el sistema, el programa fallaba con:
  ```text
  ModuleNotFoundError: No module named 'psycopg2'
  ```
* **Causa técnica:** El proyecto migró a PostgreSQL, pero el paquete de conexión `psycopg2-binary` no había sido incorporado al archivo de requerimientos.
* **Solución aplicada:** Se añadió `psycopg2-binary==2.9.13` a `requirements.txt`.

---

## 3. Configuración de Base de Datos (`database.py`)

* **Archivo modificado:** `database.py`
* **Problema:** La cadena de conexión a la base de datos estaba codificada en duro (*hardcoded*), obligando a utilizar un usuario y contraseña específicos (`postgres:1234567`).
* **Causa técnica:** Falta de integración con variables de entorno o archivos `.env`.
* **Solución aplicada:** Se parametrizó con `os.getenv("DATABASE_URL", ...)` manteniendo la URL local como valor por defecto, permitiendo flexibilidad entre entornos de desarrollo y producción.

---

## 4. Plantilla de Variables de Entorno (`.env.example`)

* **Archivo creado:** `.env.example`
* **Problema:** No existía documentación clara de qué variables de entorno podían o debían configurarse en el sistema.
* **Solución aplicada:** Se creó una plantilla con las variables soportadas por `config.py` y `database.py`:
  * `DATABASE_URL`
  * `BASE_URL`
  * `JWT_SECRET` y `JWT_EXPIRE_MINUTES`
  * Credenciales del Administrador inicial (`ADMIN_NOMBRE`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`)
  * Configuración SMTP para envío de correos.

---

## 5. Incompatibilidad de Tipos Booleanos en Servicios de Datos

### A. Gestión de Equipos (`services/equipos.py`)
* **Archivo modificado:** `services/equipos.py`
* **Problema:** Al acceder a la ruta `/equipos/lista` en el navegador, la aplicación respondía con **500 Internal Server Error**.
* **Causa técnica:** En `models.py`, la columna `activo` es de tipo `Boolean`. En PostgreSQL no existe coerción automática entre enteros y booleanos; la consulta `WHERE equipos.activo = 1` lanzaba la excepción:
  ```text
  psycopg2.errors.UndefinedFunction: el operador no existe: boolean = integer
  ```
* **Solución aplicada:**
  * Se sustituyó `models.Equipo.activo == 1` por `models.Equipo.activo.is_(True)`.
  * Se corrigió el borrado lógico en `eliminar_equipo()` de `equipo.activo = 0` a `equipo.activo = False`.

### B. Gestión de Usuarios (`services/usuarios.py`)
* **Archivo modificado:** `services/usuarios.py`
* **Problema / Prevención:** El listado y filtrado de usuarios activos/inactivos presentaba el mismo error potencial de comparación (`Usuario.activo == 1` y `Usuario.activo == 0`).
* **Solución aplicada:** Se reemplazaron por `Usuario.activo.is_(True)`, `Usuario.activo.is_(False)` y `usuario.activo = False`.

### C. Script de Inicialización de BD (`reset_db.py`)
* **Archivo modificado:** `reset_db.py`
* **Solución aplicada:** Se ajustó la asignación al crear el usuario admin de `activo=1` a `activo=True`.

---

## 6. Verificación de Credenciales de Acceso
* Se identificó que las credenciales válidas por defecto para el usuario Administrador son:
  * **Usuario o Correo:** `admin` o `admin@hospital.com`
  * **Contraseña:** `admin123` *(no `admin`)*

---

## 7. Creación e Integración de Vistas SQL en Base de Datos

* **Archivos creados/modificados:** `vistas.sql`, `models.py`, `services/equipos.py`, `services/incidencias.py`
* **Requerimiento:** Integrar las 4 vistas SQL especificadas en `vistas.txt` dentro de la base de datos PostgreSQL y asegurar su ejecución y persistencia en el ciclo de vida del proyecto para control de versiones en git.
* **Vistas implementadas:**
  1. `public.vw_inventario_equipos`: Consolida los datos de cada equipo con sus especificaciones completas de hardware (`detalle_pc`) y catálogos de ubicación y estado operativo.
  2. `public.vw_incidencias_detalladas`: Cruza incidencias con equipos, técnicos y catálogos, calculando métricas de tiempos SLA y formato legible de duración total (`Xh Ym` / `En proceso`).
  3. `public.vw_incidencias_activas`: Filtra rápidamente las incidencias en estado `PENDIENTE` y `EN_PROCESO` para visualización del panel de supervisores.
  4. `public.vw_kpis_rendimiento`: Agrupa indicadores cuantitativos globales (total de incidencias, conteos filtrados por estado y promedio de tiempo de resolución).
* **Solución aplicada:**
  * Se creó el script formal `vistas.sql` con sintaxis `CREATE OR REPLACE VIEW` lista para despliegues o administración vía `psql`.
  * Se integró la función `crear_vistas(conn)` en `models.py` dentro de `migrate_db()`, permitiendo que las vistas se creen o actualicen de forma automática al iniciar la aplicación (`main.py` o scripts de arranque).
  * Se agregaron funciones de consulta en `services/equipos.py` (`listar_inventario_completo_vista`) y `services/incidencias.py` (`obtener_kpis_vista`, `listar_incidencias_detalladas_vista`, `listar_incidencias_activas_vista`).
  * **Optimización de servicios y endpoints para consumir las vistas:**
    * `services/incidencias.py:obtener_estadisticas`: Ahora obtiene los totales y el tiempo promedio directamente desde `vw_kpis_rendimiento`, eliminando la carga de todas las incidencias a memoria RAM y el conteo en bucle de Python.
    * `services/incidencias.py:listar_incidencias_detalle` y `obtener_incidencia_detalle`: Ahora consumen `vw_incidencias_detalladas`, delegando los joins relacionales y el cálculo formateado de duración SLA a PostgreSQL.
    * `routers/incidencias.py`: Las rutas `GET /incidencias/` y `GET /incidencias/{id}` aprovechan la vista para serializar directamente en `IncidenciaDetalleResponse`.
    * `routers/equipos.py`: Se expuso el endpoint `GET /equipos/inventario-completo` que devuelve la vista consolidada de hardware.

---

## 8. Exportación de Datos a Excel (CSV) en Historial y Auditoría

* **Archivos modificados:** `routers/admin.py`, `templates/historial_admin.html`, `templates/auditoria.html`
* **Requerimiento:** Permitir la descarga de los tickets resueltos en el historial de mantenimientos y de los eventos de auditoría en formato CSV compatible directamente con Microsoft Excel.
* **Solución aplicada:**
  * Se implementó el endpoint `GET /admin/historial-general/csv` para exportar todos los tickets resueltos con su información completa (ticket, descripción, equipo, código QR, ubicación, técnico, fechas, duración SLA, próximo mantenimiento a 90 días y verificación de cierre).
  * Se implementó el endpoint `GET /admin/auditoria/csv` para exportar el log cronológico de auditoría (ID, fecha/hora, usuario, rol y acción).
  * Ambos exportadores utilizan codificación UTF-8 con BOM (`\ufeff`) y delimitador punto y coma (`;`), asegurando que Excel en sistemas Windows/Mac abra los archivos reconociendo automáticamente las columnas y los acentos sin errores de codificación.
  * Se agregaron botones interactivos `"📥 Descargar Excel (CSV)"` en la cabecera de las vistas web [historial_admin.html](file:///home/ari/Sistema_de_Incidencias/templates/historial_admin.html) y [auditoria.html](file:///home/ari/Sistema_de_Incidencias/templates/auditoria.html).
