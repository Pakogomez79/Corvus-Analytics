# Corvus XBRL Enterprise - Arquitectura y Cronograma de Desarrollo

**Fecha de creación:** 10 de diciembre de 2025  
**Última actualización:** 10 de diciembre de 2025  
**Versión:** 2.0

---

## 📋 Resumen del Proyecto

**Corvus XBRL Enterprise** es una plataforma integral de análisis financiero XBRL que permite:
- Cargar y procesar archivos XBRL de diferentes taxonomías
- Homologar conceptos a un modelo canónico para comparabilidad
- Realizar análisis financieros multi-empresa o multi-periodo
- Generar alertas automáticas cuando indicadores salen de rango
- Dashboards personalizables por usuario

### Usuarios Finales
- Analistas financieros
- Auditores internos y externos
- Contadores de empresas clientes
- Administradores del sistema

### Capacidad Objetivo
- ~100 usuarios concurrentes
- ~1000 archivos XBRL/año
- Taxonomías NIIF (SFC Colombia: bancos, seguros, entidades vigiladas)

---

## 🏗️ Arquitectura de Módulos

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CORVUS XBRL ENTERPRISE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────┐ │
│  │  🔐 ADMINISTRACIÓN  │    │  📋 CONFIG. XBRL    │    │  📤 CARGA DATOS │ │
│  ├─────────────────────┤    ├─────────────────────┤    ├─────────────────┤ │
│  │ • Usuarios          │    │ • Empresas          │    │ • Upload XBRL   │ │
│  │ • Roles             │    │ • Periodos          │    │ • Validación    │ │
│  │ • Permisos          │    │ • Estados Financ.   │    │ • Aprobación    │ │
│  │ • Bitácora          │    │ • Taxonomías        │    │ • Historial     │ │
│  │ • Config. General   │    │ • Homologación      │    │ • Reproceso     │ │
│  └─────────────────────┘    └─────────────────────┘    └─────────────────┘ │
│                                                                             │
│  ┌─────────────────────────────────────────────────┐    ┌─────────────────┐ │
│  │           📊 ANÁLISIS FINANCIERO                │    │   📈 DASHBOARD  │ │
│  ├─────────────────────────────────────────────────┤    ├─────────────────┤ │
│  │ • Selector de Análisis                          │    │ • Widgets       │ │
│  │   ├─ Multi-empresa + Un periodo                 │    │   configurables │ │
│  │   └─ Una empresa + Multi-periodo                │    │ • KPIs          │ │
│  │ • Comparativos Estados Financieros              │    │ • Gráficos      │ │
│  │ • Análisis Horizontal (variaciones)             │    │ • Accesos       │ │
│  │ • Análisis Vertical (estructura %)              │    │   rápidos       │ │
│  │ • Indicadores/Ratios financieros                │    └─────────────────┘ │
│  │ • Gráficos comparativos                         │                        │
│  │ • Análisis guardados                            │    ┌─────────────────┐ │
│  └─────────────────────────────────────────────────┘    │   🔔 ALERTAS    │ │
│                                                          ├─────────────────┤ │
│  ┌─────────────────────────────────────────────────┐    │ • Umbrales      │ │
│  │              📄 EXPORTACIÓN                     │    │ • Notificaciones│ │
│  ├─────────────────────────────────────────────────┤    │ • Historial     │ │
│  │ • PDF con logo corporativo                      │    └─────────────────┘ │
│  │ • Excel formateado                              │                        │
│  │ • CSV                                           │                        │
│  └─────────────────────────────────────────────────┘                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flujo Principal del Sistema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. ADMINISTRADOR configura el sistema                                      │
│     ┌──────────────────────────────────────────────────────────────────┐   │
│     │ • Crea usuarios y asigna roles                                    │   │
│     │ • Registra empresas en el catálogo                                │   │
│     │ • Importa taxonomías XBRL (SFC, NIIF)                             │   │
│     │ • Configura homologación: Concepto XBRL → Línea Estado Financiero │   │
│     │ • Define umbrales para alertas automáticas                        │   │
│     └──────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. USUARIO carga archivos XBRL                                             │
│     ┌──────────────────────────────────────────────────────────────────┐   │
│     │ • Sube archivo .xbrl o .xml                                       │   │
│     │ • Sistema parsea con Arelle                                       │   │
│     │ • Extrae: entidad, periodo, taxonomía, hechos                     │   │
│     │ • Aplica homologación → hechos normalizados                       │   │
│     │ • Estado: 🟡 Pendiente (solo visible para quien cargó)            │   │
│     └──────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. SUPERVISOR valida archivo (flujo de aprobación)                         │
│     ┌──────────────────────────────────────────────────────────────────┐   │
│     │ • Revisa datos extraídos                                          │   │
│     │ • Aprueba: 🟢 Validado (disponible para análisis)                 │   │
│     │ • Rechaza: 🔴 Rechazado (con observaciones, requiere recarga)     │   │
│     │ • Registro en bitácora                                            │   │
│     └──────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. USUARIO crea análisis financiero                                        │
│     ┌──────────────────────────────────────────────────────────────────┐   │
│     │ a) Selecciona MODO:                                               │   │
│     │    • Multi-empresa + Un periodo (benchmarking, ranking)           │   │
│     │    • Una empresa + Multi-periodo (tendencias, evolución)          │   │
│     │                                                                   │   │
│     │ b) Elige empresas y/o periodos a comparar                         │   │
│     │                                                                   │   │
│     │ c) Selecciona TIPO de análisis:                                   │   │
│     │    • Comparativo de Estados Financieros                           │   │
│     │    • Análisis Horizontal (variaciones)                            │   │
│     │    • Análisis Vertical (estructura %)                             │   │
│     │    • Indicadores financieros (ratios)                             │   │
│     │                                                                   │   │
│     │ d) Sistema genera reporte con gráficos                            │   │
│     │                                                                   │   │
│     │ e) GUARDA análisis para consulta posterior                        │   │
│     └──────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  5. SISTEMA genera alertas automáticas                                      │
│     ┌──────────────────────────────────────────────────────────────────┐   │
│     │ • Si un indicador supera/baja del umbral → Alerta                 │   │
│     │ • Notificación al usuario en dashboard                            │   │
│     │ • Estado: Nueva → Revisada → Cerrada                              │   │
│     └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología | Razón |
|------|------------|-------|
| **Backend** | FastAPI + Python 3.11 | Async, rápido, tipado |
| **Templates** | Jinja2 + HTMX | Interactividad sin JS complejo |
| **Interactividad** | Alpine.js | Micro-framework, ~15kb |
| **Gráficos** | Chart.js | Todos los tipos de gráfico |
| **CSS** | Corvus CSS (custom) | Material Pro style, tonos azules |
| **Auth** | FastAPI-Users + JWT | Extensible a LDAP |
| **ORM** | SQLAlchemy 2.0 | Multi-BD |
| **Migraciones** | Alembic | Versionado de esquema |
| **PDF** | xhtml2pdf | Sin dependencias externas |
| **Excel** | openpyxl | Formatos profesionales |
| **XBRL** | Arelle | Parser oficial |
| **Servidor** | Uvicorn + Gunicorn | ASGI production-ready |

**💰 Costo total de licencias: $0**

---

## 🎨 Diseño UI/UX

### Estructura de Layout
```
┌────────────────────────────────────────────────────────────────┐
│  HEADER: Logo Corvus | Búsqueda | Notificaciones | Usuario    │
├──────────────┬─────────────────────────────────────────────────┤
│              │                                                 │
│   SIDEBAR    │              CONTENIDO PRINCIPAL                │
│              │                                                 │
│  Principal   │   ┌─────────────────────────────────────────┐  │
│  • Dashboard │   │  Breadcrumb: Inicio / Módulo / Página   │  │
│              │   ├─────────────────────────────────────────┤  │
│  XBRL        │   │                                         │  │
│  • Cargar    │   │         ÁREA DE CONTENIDO               │  │
│  • Entidades │   │                                         │  │
│  • Archivos  │   │    (Cards, Tablas, Gráficos, Forms)     │  │
│              │   │                                         │  │
│  Reportes    │   │                                         │  │
│  • Comparar  │   │                                         │  │
│  • Análisis  │   │                                         │  │
│  • Indicador │   └─────────────────────────────────────────┘  │
│              │                                                 │
│  Alertas     │                                                 │
│              │                                                 │
│  Admin       │                                                 │
│  • Usuarios  │                                                 │
│  • Config    │                                                 │
│              │                                                 │
└──────────────┴─────────────────────────────────────────────────┘
```

### Paleta de Colores
| Variable | Color | Uso |
|----------|-------|-----|
| `--corvus-primary` | #1e3a5f | Sidebar, header, botones principales |
| `--corvus-primary-dark` | #0d1f33 | Hover states, sombras |
| `--corvus-accent` | #00bcd4 | Highlights, links, badges |
| `--corvus-gradient` | #1e3a5f → #00bcd4 | Backgrounds destacados |
| `--success` | #48bb78 | Estados OK, validado |
| `--warning` | #ed8936 | Alertas, pendiente |
| `--danger` | #f56565 | Errores, rechazado |

### Idioma
- Español únicamente

---

## 📊 Detalle de Módulos

### 🔐 Módulo 1: Administración

| Funcionalidad | Descripción | Prioridad |
|---------------|-------------|-----------|
| **Usuarios** | CRUD, activar/desactivar, reset contraseña | Alta |
| **Roles** | Admin, Analista, Auditor, Consultor | Alta |
| **Permisos** | Matriz rol × módulo × acción (ver/crear/editar/eliminar) | Alta |
| **Bitácora** | Log de acciones: quién, qué, cuándo, IP | Alta |
| **Config. General** | Logo empresa, nombre, parámetros globales | Media |

### 📋 Módulo 2: Configuración XBRL

| Funcionalidad | Descripción | Prioridad |
|---------------|-------------|-----------|
| **Empresas** | Catálogo: NIT, razón social, sector, tipo | Alta |
| **Periodos** | Definición: mensual, trimestral, anual, personalizado | Alta |
| **Estados Financieros** | Catálogo canónico: Balance, PyG, Flujo, Patrimonio | Alta |
| **Taxonomías** | Importación y gestión de taxonomías SFC/NIIF | Alta |
| **Homologación** | Mapeo concepto XBRL → línea canónica | **Crítica** |

### 📤 Módulo 3: Carga de Datos

| Funcionalidad | Descripción | Prioridad |
|---------------|-------------|-----------|
| **Upload XBRL** | Drag & drop, validación formato | Alta |
| **Parsing** | Extracción con Arelle, feedback detallado | Alta |
| **Homologación** | Aplicación automática del mapeo | Alta |
| **Flujo Aprobación** | Pendiente → Validado → Rechazado | Media |
| **Historial** | Lista de cargas con filtros | Media |
| **Reproceso** | Re-homologar archivos existentes | Baja |

### 📊 Módulo 4: Análisis Financiero

| Funcionalidad | Descripción | Prioridad |
|---------------|-------------|-----------|
| **Selector** | Modo multi-empresa o multi-periodo | **Crítica** |
| **Comparativos** | Tablas lado a lado, estados financieros | Alta |
| **Análisis Horizontal** | Variaciones absolutas y porcentuales | Alta |
| **Análisis Vertical** | Estructura % (línea vs total) | Alta |
| **Indicadores** | ROE, ROA, Liquidez, Solvencia, etc. | Alta |
| **Gráficos** | Barras, líneas, pie, treemap | Alta |
| **Análisis Guardados** | Guardar, consultar, compartir | Media |

### 📈 Módulo 5: Dashboard

| Funcionalidad | Descripción | Prioridad |
|---------------|-------------|-----------|
| **Widgets** | Configurables por usuario | Media |
| **KPIs** | Indicadores principales | Alta |
| **Gráficos resumen** | Tendencias, comparativos rápidos | Media |
| **Accesos rápidos** | Links a funciones frecuentes | Baja |

### 🔔 Módulo 6: Alertas

| Funcionalidad | Descripción | Prioridad |
|---------------|-------------|-----------|
| **Umbrales** | Configuración por indicador y empresa | Media |
| **Generación** | Automática al cargar XBRL | Media |
| **Centro notificaciones** | Lista con estados | Media |
| **Historial** | Consulta de alertas cerradas | Baja |

### 📄 Módulo 7: Exportación

| Funcionalidad | Descripción | Prioridad |
|---------------|-------------|-----------|
| **PDF** | Con logo corporativo, formato profesional | Alta |
| **Excel** | Formateado, con gráficos | Alta |
| **CSV** | Datos crudos | Alta |

---

## 📅 Cronograma de Desarrollo

### Metodología
- Sprints semanales
- Gestión: Chat (por ahora)
- Repositorio: GitHub

---

### Resumen de Fases

| Fase | Semanas | Descripción | Módulos |
|------|---------|-------------|---------|
| **F1** | 1-4 | Fundamentos | UI Layout, Autenticación, Bitácora, BD |
| **F2** | 5-8 | Configuración XBRL | Empresas, Periodos, Taxonomías, Homologación |
| **F3** | 9-12 | Carga y Procesamiento | Upload, Parsing, Validación, Aprobación |
| **F4** | 13-17 | Análisis Financiero | Selector, Comparativos, Horizontal, Vertical, Indicadores |
| **F5** | 18-21 | Dashboard y Alertas | Widgets, KPIs, Umbrales, Notificaciones |
| **F6** | 22-24 | Producción | SQL Server, Optimización, Documentación |

**Total: 24 semanas (~6 meses)**

---

### FASE 1: Fundamentos (Semanas 1-4)

| Sprint | Entregables |
|--------|-------------|
| **S1** | ✅ Diseño UI/Layout (header, sidebar, dashboard base), CSS framework Corvus |
| **S2** | Sistema de autenticación (login, registro, logout, sesiones) |
| **S3** | Gestión de usuarios y roles (CRUD, asignación, estados) |
| **S4** | Permisos y bitácora (matriz permisos, log de acciones, consulta logs) |

---

### FASE 2: Configuración XBRL (Semanas 5-8)

| Sprint | Entregables |
|--------|-------------|
| **S5** | Catálogo de empresas (CRUD, NIT, sector, tipo, búsqueda) |
| **S6** | Gestión de periodos contables (tipos, fechas, estados) |
| **S7** | Catálogo de estados financieros canónicos (Balance, PyG, Flujo, Patrimonio) |
| **S8** | Gestión de taxonomías y homologación (importar, mapear conceptos) |

---

### FASE 3: Carga y Procesamiento (Semanas 9-12)

| Sprint | Entregables |
|--------|-------------|
| **S9** | Upload XBRL mejorado (drag & drop, validaciones, feedback detallado) |
| **S10** | Parsing avanzado (extracción completa, aplicación homologación) |
| **S11** | Flujo de aprobación (estados, validación supervisor, bitácora) |
| **S12** | Historial de cargas (filtros, reproceso, estadísticas) |

---

### FASE 4: Análisis Financiero (Semanas 13-17)

| Sprint | Entregables |
|--------|-------------|
| **S13** | Selector de análisis (multi-empresa/multi-periodo, selección entidades) |
| **S14** | Comparativos de estados financieros (tablas lado a lado, filtros) |
| **S15** | Análisis horizontal (variaciones absolutas y %, entre periodos) |
| **S16** | Análisis vertical (estructura %, cada línea vs total activo/ventas) |
| **S17** | Indicadores financieros (ROE, ROA, liquidez, solvencia, endeudamiento) |

---

### FASE 5: Dashboard y Alertas (Semanas 18-21)

| Sprint | Entregables |
|--------|-------------|
| **S18** | Gráficos comparativos (barras, líneas, pie, integración Chart.js) |
| **S19** | Dashboard personalizable (widgets, drag & drop, guardar layout) |
| **S20** | Motor de alertas (configuración umbrales, generación automática) |
| **S21** | Centro de notificaciones (alertas, estados, historial) |

---

### FASE 6: Producción (Semanas 22-24)

| Sprint | Entregables |
|--------|-------------|
| **S22** | Análisis guardados (guardar, consultar, compartir, exportar) |
| **S23** | Migración SQL Server, pruebas de carga, optimización queries |
| **S24** | Documentación usuario/admin, guía despliegue, capacitación |

---

## 📊 Línea de Tiempo Visual

```
Dic 2025    Ene 2026       Feb            Mar            Abr            May           Jun
   |----F1----|-----F2-----|-----F3------|------F4------|-----F5-----|----F6----|
   Layout      Empresas     Upload        Selector       Dashboard     Producción
   Auth        Periodos     Parsing       Comparativos   Alertas       SQL Server
   Usuarios    Taxonomías   Aprobación    Horizontal     Widgets       Docs
   Bitácora    Homologación Historial     Vertical       KPIs          Deploy
                                          Indicadores
```

**Inicio:** Diciembre 2025  
**Fin estimado:** Junio 2026

---

## 🖥️ Entornos

| Entorno | Base de Datos | Sistema Operativo |
|---------|---------------|-------------------|
| Desarrollo | MySQL 8.0 | Windows 10/11 |
| Producción | SQL Server 2019 | Windows Server / Linux |

---

## 🗄️ Modelo de Datos (Entidades Principales)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    User      │     │    Role      │     │  Permission  │
├──────────────┤     ├──────────────┤     ├──────────────┤
│ id           │────▶│ id           │────▶│ id           │
│ email        │     │ name         │     │ module       │
│ password     │     │ description  │     │ action       │
│ name         │     │ permissions[]│     │ name         │
│ role_id      │     └──────────────┘     └──────────────┘
│ is_active    │
│ created_at   │     ┌──────────────┐     ┌──────────────┐
└──────────────┘     │   AuditLog   │     │    Alert     │
                     ├──────────────┤     ├──────────────┤
┌──────────────┐     │ id           │     │ id           │
│   Entity     │     │ user_id      │     │ entity_id    │
├──────────────┤     │ action       │     │ indicator    │
│ id           │     │ module       │     │ value        │
│ identifier   │     │ details      │     │ threshold    │
│ name         │     │ ip_address   │     │ status       │
│ sector       │     │ created_at   │     │ created_at   │
│ type         │     └──────────────┘     └──────────────┘
│ is_active    │
└──────────────┘     ┌──────────────┐     ┌──────────────┐
       │             │   Taxonomy   │     │  Canonical   │
       │             ├──────────────┤     ├──────────────┤
       ▼             │ id           │     │ id           │
┌──────────────┐     │ name         │     │ code         │
│     File     │     │ version      │     │ name         │
├──────────────┤     │ namespace    │     │ statement    │
│ id           │     │ is_active    │     │ section      │
│ entity_id    │────▶└──────────────┘     │ order        │
│ filename     │            │             └──────────────┘
│ taxonomy_id  │            │                    ▲
│ period_start │            ▼                    │
│ period_end   │     ┌──────────────┐     ┌──────────────┐
│ status       │     │   Mapping    │     │    Fact      │
│ uploaded_by  │     ├──────────────┤     ├──────────────┤
│ approved_by  │     │ id           │     │ id           │
│ created_at   │     │ taxonomy_id  │     │ file_id      │
└──────────────┘     │ concept_qname│     │ canonical_id │
                     │ canonical_id │     │ value        │
                     └──────────────┘     │ unit         │
                                          │ decimals     │
┌──────────────┐     ┌──────────────┐     └──────────────┘
│   Analysis   │     │  Dashboard   │
├──────────────┤     ├──────────────┤
│ id           │     │ id           │
│ user_id      │     │ user_id      │
│ name         │     │ layout_json  │
│ type         │     │ updated_at   │
│ mode         │     └──────────────┘
│ config_json  │
│ created_at   │
└──────────────┘
```

---

## 📝 Notas Técnicas

### Flujo de Aprobación de Archivos

| Estado | Descripción | Visible para |
|--------|-------------|--------------|
| 🟡 **Pendiente** | Recién cargado, sin validar | Solo quien lo cargó |
| 🟢 **Validado** | Aprobado por supervisor | Todos los usuarios |
| 🔴 **Rechazado** | Con observaciones | Solo quien lo cargó |

*Este flujo es configurable y puede desactivarse si no se requiere.*

### Homologación de Taxonomías

El sistema permite comparar archivos de **diferentes taxonomías** gracias al mapeo canónico:

```
Taxonomía A (SFC 2024)              Taxonomía B (NIIF 2023)
┌─────────────────────┐             ┌─────────────────────┐
│ sfc_ActivosCorrient │             │ ifrs_CurrentAssets  │
│ sfc_Efectivo        │             │ ifrs_CashEquivalent │
│ sfc_CuentasPorCobrar│             │ ifrs_Receivables    │
└──────────┬──────────┘             └──────────┬──────────┘
           │                                    │
           ▼                                    ▼
     ┌─────────────────────────────────────────────┐
     │         MODELO CANÓNICO (Estados Fin.)     │
     ├─────────────────────────────────────────────┤
     │ BALANCE.ACTIVO.CORRIENTE                   │
     │ BALANCE.ACTIVO.CORRIENTE.EFECTIVO          │
     │ BALANCE.ACTIVO.CORRIENTE.CUENTAS_X_COBRAR  │
     └─────────────────────────────────────────────┘
```

### Despliegue
- Instalación directa (sin Docker por ahora)
- Compatible Windows Server y Linux
- Sin proxy/firewall que afecte conexiones externas

### Seguridad
- Cifrado en tránsito (HTTPS)
- Auditoría completa de acciones
- Logs almacenados en BD (retención 3 años)

### Futuras Mejoras (post-MVP)
- Integración LDAP/SSO
- Notificaciones por correo
- App móvil (opcional)

---

## 📌 Próximos Pasos

- [x] Definir arquitectura v2.0
- [x] Crear repositorio GitHub
- [x] Sprint 1: UI Layout base
- [ ] Iniciar Sprint 2 (Autenticación)
- [ ] Configurar Alembic para migraciones

---

*Documento actualizado - Corvus XBRL Enterprise v2.0*
