-- =========================================================================
-- VISTAS DEL SISTEMA DE INCIDENCIAS
-- Basado en especificación de esquema BD v2.4 (vistas.txt)
-- =========================================================================

-- =========================================================================
-- 1. VISTA DE INVENTARIO COMPLETO DE EQUIPOS
-- =========================================================================
-- Consolida los datos del equipo, su hardware (detalle_pc) y sus catálogos (ubicación y estado)
CREATE OR REPLACE VIEW public.vw_inventario_equipos AS
SELECT 
    e.id AS equipo_id,
    e.codigo_qr,
    e.nombre AS equipo_nombre,
    tu.nombre AS ubicacion_hospital,
    te.nombre AS estado_operativo_maquina,
    e.activo,
    
    -- Especificaciones de Hardware desde detalle_pc
    d.usuario_asignado,
    d.ip,
    d.tipo_ip,
    d.mac,
    d.dominio,
    d.sistema_operativo,
    d.version_so,
    d.antivirus,
    d.software_adicional,
    d.marca_modelo_cpu,
    d.procesador,
    d.ram_gb,
    d.ram_tipo,
    d.ram_slots,
    d.almacenamiento_tipo,
    d.almacenamiento_capacidad,
    d.puertos_video,
    d.monitor_marca,
    d.monitor_modelo,
    d.monitor_serial,
    d.monitor_bn,
    d.teclado_marca,
    d.teclado_serial,
    d.teclado_bn,
    d.mouse_marca,
    d.mouse_serial,
    d.mouse_bn,
    d.proteccion_electrica_tipo,
    d.proteccion_electrica_marca,
    d.proteccion_electrica_bn,
    d.impresora_marca,
    d.impresora_modelo,
    d.impresora_ip,
    d.impresora_bn,
    d.observaciones,
    d.fecha_levantamiento,
    
    d.id AS detalle_pc_id
FROM public.equipos e
LEFT JOIN public.tipo_general tu ON e.tipo_ubicacion_id = tu.id AND tu.categoria = 'UBICACION'
LEFT JOIN public.tipo_general te ON e.tipo_estado_id = te.id AND te.categoria = 'ESTADO_EQUIPO'
LEFT JOIN public.detalle_pc d ON d.equipo_id = e.id;


-- =========================================================================
-- 2. VISTA DE INCIDENCIAS DETALLADAS Y TRAZABILIDAD
-- =========================================================================
-- Cruza incidencias con equipos, técnicos y catálogos, calculando tiempos de SLA
CREATE OR REPLACE VIEW public.vw_incidencias_detalladas AS
SELECT 
    i.id AS incidencia_id,
    i.reportado_por_nombre,
    i.reportado_por_cedula,
    i.descripcion,
    i.estado,
    i.detalle_verificacion_cierre,
    
    -- Tiempos de control y SLAs
    i.fecha_reporte,
    i.fecha_asignacion,
    i.fecha_proceso,
    i.fecha_solucion,
    i.duracion_hasta_asignacion_min,
    i.duracion_proceso_min,
    i.duracion_solucion_min,
    i.duracion_total_min,
    
    -- Formato legible de tiempo transcurrido total (ej: "3h 15m")
    CASE 
        WHEN i.duracion_total_min IS NOT NULL THEN 
            CONCAT(FLOOR(i.duracion_total_min / 60), 'h ', MOD(i.duracion_total_min, 60), 'm')
        ELSE 'En proceso'
    END AS duracion_total_formateada,

    -- Datos del Equipo asociado
    e.id AS equipo_id,
    e.codigo_qr,
    e.nombre AS equipo_nombre,
    tu.nombre AS ubicacion_actual,
    te.nombre AS estado_operativo_maquina,

    -- Datos del Técnico Asignado
    u.id AS tecnico_id,
    u.nombre AS tecnico_nombre,
    u.email AS tecnico_email

FROM public.incidencias i
LEFT JOIN public.equipos e ON i.equipo_id = e.id
LEFT JOIN public.tipo_general tu ON e.tipo_ubicacion_id = tu.id AND tu.categoria = 'UBICACION'
LEFT JOIN public.tipo_general te ON e.tipo_estado_id = te.id AND te.categoria = 'ESTADO_EQUIPO'
LEFT JOIN public.usuarios u ON i.tecnico_id = u.id;


-- =========================================================================
-- 3. VISTA DE INCIDENCIAS ACTIVAS (Para el panel del Supervisor)
-- =========================================================================
-- Filtra rápidamente las incidencias que están abiertas o en proceso
CREATE OR REPLACE VIEW public.vw_incidencias_activas AS
SELECT * 
FROM public.vw_incidencias_detalladas 
WHERE estado IN ('PENDIENTE', 'EN_PROCESO');


-- =========================================================================
-- 4. VISTA DE KPIS Y RENDIMIENTO TÉCNICO
-- =========================================================================
-- Agrupa métricas para las estadísticas del dashboard administrativo
CREATE OR REPLACE VIEW public.vw_kpis_rendimiento AS
SELECT 
    COUNT(*) AS total_incidencias,
    COUNT(*) FILTER (WHERE estado = 'PENDIENTE') AS total_pendientes,
    COUNT(*) FILTER (WHERE estado = 'EN_PROCESO') AS total_en_proceso,
    COUNT(*) FILTER (WHERE estado = 'RESUELTO') AS total_resueltas,
    ROUND(AVG(duracion_total_min) FILTER (WHERE duracion_total_min IS NOT NULL), 2) AS tiempo_promedio_resolucion_min
FROM public.incidencias;
