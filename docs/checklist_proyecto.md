# Corvus XBRL Enterprise - Checklist Completo del Proyecto

**Fecha de creación:** 10 de diciembre de 2025  
**Última actualización:** 11 de diciembre de 2025  
**Versión:** 1.0

---

## 📊 Resumen de Progreso

| Módulo | Completado | Total | Progreso |
|--------|------------|-------|----------|
| 🔐 Administración | 27 | 32 | 🟩 84% |
| 📋 Configuración XBRL | 5 | 34 | 🟨 15% |
| 📤 Carga de Datos | 0 | 23 | ⬜ 0% |
| 📊 Análisis Financiero | 0 | 55 | ⬜ 0% |
| 📈 Dashboard | 7 | 15 | 🟨 47% |
| 🔔 Alertas | 0 | 18 | ⬜ 0% |
| 📄 Exportación | 0 | 14 | ⬜ 0% |
| 🖥️ Infraestructura | 11 | 16 | 🟩 69% |
| **TOTAL** | **50** | **208** | **24%** |

---

## 🖥️ INFRAESTRUCTURA Y SETUP

### Entorno de Desarrollo
- [x] Crear repositorio GitHub
- [x] Estructura de carpetas base (`app/`, `docs/`, `templates/`, `static/`)
- [x] CSS Framework Corvus (layout, componentes, colores)
- [x] Configurar `.gitignore` completo
- [x] Configurar `requirements.txt` con todas las dependencias
- [x] Configurar variables de entorno (`.env.example`)
- [x] Configurar logging estructurado

### Base de Datos
- [x] Configurar Alembic para migraciones
- [x] Crear migración inicial con modelo de datos
- [x] Script de seed para datos iniciales (create_users.py)
- [x] Configuración dual MySQL/SQL Server
- [ ] Índices y optimización de queries

### Despliegue
- [ ] Guía de instalación Windows
- [ ] Guía de instalación Linux
- [ ] Script de configuración automática
- [ ] Configuración HTTPS/SSL

---

## 🔐 MÓDULO 1: ADMINISTRACIÓN

### 1.1 Autenticación (✅ 87% - 7/8)
- [x] Página de login con diseño MaterialPro
- [x] Formulario de login (username + contraseña)
- [x] Validación de credenciales con bcrypt
- [x] Generación de token JWT (30min expiry)
- [x] Middleware de autenticación (protección de rutas)
- [x] Página de logout
- [ ] Recuperación de contraseña (email) - Requiere SMTP
- [x] Cambio de contraseña con validación de fortaleza

### 1.2 Gestión de Usuarios
- [x] Listado de usuarios (tabla con filtros)
- [x] Crear usuario (formulario)
- [x] Editar usuario
- [x] Activar/Desactivar usuario
- [x] Reset de contraseña por admin
- [x] Perfil de usuario (ver/editar propio)

### 1.3 Gestión de Roles
- [x] Listado de roles
- [x] Crear rol
- [x] Editar rol
- [ ] Eliminar rol (con validación de usuarios asignados)
- [x] Roles predefinidos: Admin, Analista, Auditor, Consultor

### 1.4 Gestión de Permisos
- [ ] Matriz de permisos (rol × módulo × acción)
- [ ] Acciones: Ver, Crear, Editar, Eliminar, Exportar (soporte backend presente)
- [x] Decorador de permisos en rutas
- [ ] Ocultamiento de menús según permisos

### 1.5 Bitácora de Auditoría
- [x] Modelo AuditLog en BD
- [x] Registro automático de login/logout
- [x] Registro de acciones CRUD
- [x] Registro de IP y user-agent
- [x] Listado de logs con filtros (usuario, fecha, módulo)
- [x] Exportación de logs

### 1.6 Configuración General
- [x] Logo de empresa (upload) — soporte implementado; archivos guardados como `/static/images/logo.png`
- [x] Nombre de empresa
- [x] Parámetros globales (formato fechas, moneda, etc.)

---

## 📋 MÓDULO 2: CONFIGURACIÓN XBRL

### 2.1 Catálogo de Empresas
### 2.1 Catálogo de Empresas
- [x] Modelo Entity (NIT, nombre, sector, tipo, estado)
- [x] Listado de empresas con búsqueda y filtros
- [x] Crear empresa
- [x] Editar empresa
- [x] Activar/Desactivar empresa

### 2.2 Gestión de Periodos
- [ ] Modelo Period (tipo, año, fecha_inicio, fecha_fin, estado)
- [ ] Tipos: Mensual, Trimestral, Semestral, Anual
- [ ] Generación automática de periodos por año
- [ ] Listado de periodos
- [ ] Cerrar/Abrir periodo
- [ ] Validación de fechas

### 2.3 Estados Financieros Canónicos
- [ ] Modelo FinancialStatement (código, nombre, tipo)
- [ ] Tipos: Balance General, Estado de Resultados, Flujo de Efectivo, Cambios en Patrimonio
- [ ] Modelo CanonicalLine (código, nombre, statement_id, parent_id, orden)
- [ ] Estructura jerárquica (Activo > Corriente > Efectivo)
- [ ] CRUD de líneas canónicas
- [ ] Importación desde archivo (CSV/JSON)
- [ ] Vista de árbol de estructura

### 2.4 Gestión de Taxonomías
- [ ] Modelo Taxonomy (nombre, versión, namespace, archivo, estado)
- [ ] Upload de archivo de taxonomía
- [ ] Listado de taxonomías
- [ ] Activar/Desactivar taxonomía
- [ ] Visualización de conceptos de una taxonomía
- [ ] Importación de taxonomías SFC

### 2.5 Homologación (Mapeo)
- [ ] Modelo Mapping (taxonomy_id, concept_qname, canonical_id)
- [ ] Interfaz de mapeo: concepto XBRL ↔ línea canónica
- [ ] Búsqueda de conceptos por nombre
- [ ] Sugerencias automáticas (match por nombre similar)
- [ ] Importación de mapeo desde CSV
- [ ] Exportación de mapeo
- [ ] Validación de cobertura (% de conceptos mapeados)
- [ ] Vista de conceptos sin mapear

---

## 📤 MÓDULO 3: CARGA DE DATOS

### 3.1 Upload de Archivos XBRL
- [ ] Página de upload con drag & drop
- [ ] Validación de formato (.xbrl, .xml)
- [ ] Validación de tamaño máximo
- [ ] Barra de progreso de carga
- [ ] Mensaje de éxito/error detallado

### 3.2 Parsing y Extracción
- [ ] Integración con Arelle
- [ ] Extracción de metadatos (entidad, periodo, taxonomía)
- [ ] Extracción de hechos (facts)
- [ ] Aplicación de homologación (mapeo a canónicos)
- [ ] Detección de empresa en catálogo
- [ ] Detección de periodo
- [ ] Manejo de errores de parsing

### 3.3 Flujo de Aprobación
- [ ] Estados de archivo: Pendiente, Validado, Rechazado
- [ ] Pantalla de archivos pendientes (para supervisores)
- [ ] Acción: Aprobar archivo
- [ ] Acción: Rechazar archivo (con observaciones)
- [ ] Notificación al usuario que cargó
- [ ] Configuración: habilitar/deshabilitar flujo

### 3.4 Historial de Cargas
- [ ] Listado de archivos con filtros (entidad, periodo, estado, fecha)
- [ ] Detalle de archivo (metadatos, estadísticas)
- [ ] Vista previa de hechos extraídos
- [ ] Reprocesar archivo (re-aplicar homologación)
- [ ] Eliminar archivo (soft delete)

---

## 📊 MÓDULO 4: ANÁLISIS FINANCIERO

### 4.1 Selector de Análisis
- [ ] Página principal de análisis
- [ ] Selector de modo: Multi-empresa / Multi-periodo
- [ ] **Multi-empresa:** Selección de N empresas + 1 periodo
- [ ] **Multi-periodo:** Selección de 1 empresa + N periodos
- [ ] Dropdown de empresas con búsqueda
- [ ] Dropdown de periodos
- [ ] Validación de archivos disponibles (validados)
- [ ] Botón "Generar Análisis"

### 4.2 Comparativo de Estados Financieros
- [ ] Tabla lado a lado (columnas = empresas o periodos)
- [ ] Filas = líneas canónicas del estado financiero
- [ ] Selector de estado financiero (Balance, PyG, etc.)
- [ ] Formato numérico con miles/decimales
- [ ] Colores para valores positivos/negativos
- [ ] Expandir/Colapsar secciones
- [ ] Ordenar por columna

### 4.3 Análisis Horizontal
- [ ] Variación absoluta (periodo actual - periodo anterior)
- [ ] Variación porcentual (% cambio)
- [ ] Columnas: Valor P1, Valor P2, Var. Abs., Var. %
- [ ] Formato condicional (verde +, rojo -)
- [ ] Aplicable a multi-periodo
- [ ] Gráfico de barras de variaciones

### 4.4 Análisis Vertical
- [ ] Estructura porcentual
- [ ] Base: Total Activo (Balance) o Ventas (PyG)
- [ ] Cada línea muestra: Valor, % del total
- [ ] Comparativo de estructura entre empresas/periodos
- [ ] Gráfico de composición (stacked bar o treemap)

### 4.5 Indicadores Financieros (Ratios)
- [ ] Fórmulas predefinidas:
  - [ ] Liquidez Corriente = Activo Corriente / Pasivo Corriente
  - [ ] Prueba Ácida = (Activo Corriente - Inventarios) / Pasivo Corriente
  - [ ] Capital de Trabajo = Activo Corriente - Pasivo Corriente
  - [ ] Endeudamiento = Pasivo Total / Activo Total
  - [ ] ROE = Utilidad Neta / Patrimonio
  - [ ] ROA = Utilidad Neta / Activo Total
  - [ ] Margen Bruto = Utilidad Bruta / Ventas
  - [ ] Margen Neto = Utilidad Neta / Ventas
  - [ ] Rotación de Cartera
  - [ ] Rotación de Inventarios
- [ ] Tabla de indicadores por empresa/periodo
- [ ] Gráficos de indicadores (barras, líneas)
- [ ] Semáforo (verde/amarillo/rojo según umbrales)

### 4.6 Gráficos Comparativos
- [ ] Gráfico de barras (comparar valores)
- [ ] Gráfico de líneas (tendencias en el tiempo)
- [ ] Gráfico de pie (composición)
- [ ] Gráfico de radar (indicadores)
- [ ] Selector de tipo de gráfico
- [ ] Selector de datos a graficar
- [ ] Exportar gráfico como imagen

### 4.7 Análisis Guardados
- [ ] Modelo Analysis (user_id, nombre, tipo, modo, config_json, created_at)
- [ ] Botón "Guardar análisis"
- [ ] Nombre y descripción del análisis
- [ ] Listado "Mis Análisis"
- [ ] Cargar análisis guardado
- [ ] Editar nombre/descripción
- [ ] Eliminar análisis
- [ ] Compartir análisis con otros usuarios

---

## 📈 MÓDULO 5: DASHBOARD

### 5.1 Dashboard Principal
- [x] KPIs principales (cards)
  - [x] Total empresas activas
  - [x] Archivos cargados este mes
  - [ ] Alertas pendientes
  - [x] Último archivo cargado
- [x] Gráfico: Archivos por mes (últimos 12 meses)
- [x] Gráfico: Distribución por sector
- [x] Tabla: Archivos recientes

### 5.2 Widgets Personalizables
- [ ] Modelo DashboardWidget (user_id, tipo, config_json, orden)
- [ ] Catálogo de widgets disponibles
- [ ] Agregar widget al dashboard
- [ ] Eliminar widget
- [ ] Drag & drop para reordenar
- [ ] Guardar layout del dashboard
- [ ] Reset a configuración por defecto

---

## 🔔 MÓDULO 6: ALERTAS

### 6.1 Configuración de Umbrales
- [ ] Modelo AlertThreshold (indicador, operador, valor, empresa_id, activo)
- [ ] Operadores: >, <, >=, <=, =, entre
- [ ] Umbrales globales (todas las empresas)
- [ ] Umbrales por empresa específica
- [ ] CRUD de umbrales
- [ ] Activar/Desactivar umbral

### 6.2 Generación de Alertas
- [ ] Modelo Alert (entity_id, indicator, value, threshold_id, status, created_at)
- [ ] Generación automática al cargar archivo XBRL
- [ ] Comparación de indicadores vs umbrales
- [ ] Estados: Nueva, Revisada, Cerrada
- [ ] Registro de quién cerró y cuándo

### 6.3 Centro de Notificaciones
- [ ] Icono de campana en header con contador
- [ ] Dropdown con alertas recientes
- [ ] Página de alertas completa
- [ ] Filtros: estado, empresa, indicador, fecha
- [ ] Marcar como revisada
- [ ] Cerrar alerta (con comentario)
- [ ] Historial de alertas cerradas

---

## 📄 MÓDULO 7: EXPORTACIÓN

### 7.1 Exportación PDF
- [ ] Plantilla PDF con logo corporativo
- [ ] Header con fecha, empresa, periodo
- [ ] Tabla de datos formateada
- [ ] Gráficos embebidos
- [ ] Numeración de páginas
- [ ] Generación con xhtml2pdf

### 7.2 Exportación Excel
- [ ] Formato .xlsx con openpyxl
- [ ] Estilos: headers, bordes, colores
- [ ] Múltiples hojas (si aplica)
- [ ] Gráficos embebidos (opcional)
- [ ] Fórmulas para totales

### 7.3 Exportación CSV
- [ ] Datos crudos en CSV
- [ ] Encoding UTF-8 con BOM
- [ ] Separador configurable (coma o punto y coma)

---

## 🧪 TESTING Y CALIDAD

### Tests Unitarios
- [ ] Tests para modelos
- [ ] Tests para servicios de cálculo
- [ ] Tests para parseo XBRL
- [ ] Tests para homologación

### Tests de Integración
- [ ] Tests de endpoints API
- [ ] Tests de flujo de carga
- [ ] Tests de generación de reportes

### Tests End-to-End
- [ ] Flujo completo: carga → análisis → exportación
- [ ] Flujo de aprobación
- [ ] Flujo de alertas

---

## 📚 DOCUMENTACIÓN

### Documentación Técnica
- [ ] README.md actualizado
- [ ] Guía de instalación
- [ ] Guía de configuración
- [ ] Documentación de API (OpenAPI/Swagger)
- [ ] Modelo de datos

### Documentación de Usuario
- [ ] Manual de usuario (PDF)
- [ ] Guía rápida de inicio
- [ ] Video tutoriales (opcional)
- [ ] FAQ

---

## 🚀 PRODUCCIÓN

### Preparación
- [ ] Pruebas de carga (100 usuarios concurrentes)
- [ ] Optimización de queries
- [ ] Configuración de caché (si aplica)
- [ ] Configuración de HTTPS

### Despliegue
- [ ] Migración a SQL Server
- [ ] Backup automático de BD
- [ ] Monitoreo de errores
- [ ] Logs centralizados

### Post-lanzamiento
- [ ] Capacitación a usuarios
- [ ] Soporte inicial
- [ ] Recolección de feedback
- [ ] Plan de mejoras v2.0

---

## 📋 Leyenda

| Símbolo | Significado |
|---------|-------------|
| ⬜ | No iniciado |
| 🟨 | En progreso |
| ✅ | Completado |
| ❌ | Bloqueado/Cancelado |

---

*Checklist generado para Corvus XBRL Enterprise - Actualizar semanalmente*
