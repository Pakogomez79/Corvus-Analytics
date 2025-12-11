# Corvus Analytics - Arquitectura y Cronograma de Desarrollo

**Fecha de creación:** 10 de diciembre de 2025  
**Versión:** 1.0

---

## 📋 Resumen del Proyecto

**Corvus Analytics** es una plataforma de análisis financiero XBRL para empresas reguladas por la Superfinanciera y Supersociedades de Colombia. Permite cargar, procesar y comparar estados financieros en formato XBRL, generando reportes, indicadores y alertas automáticas.

### Usuarios Finales
- Analistas financieros
- Auditores
- Reguladores
- Contadores de empresas clientes

### Capacidad
- ~100 usuarios concurrentes
- ~1000 archivos XBRL/año
- Taxonomías NIIF (bancos, seguros, entidades vigiladas)

---

## 🏗️ Arquitectura Técnica

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│  Jinja2 + HTMX + Alpine.js + Chart.js + PicoCSS                 │
│  (SPA-like sin complejidad de React)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │   Auth   │  │  XBRL    │  │ Reportes │  │  Alertas │        │
│  │  Module  │  │  Ingest  │  │ & Graphs │  │  Engine  │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ Auditoría│  │  Export  │  │   API    │                      │
│  │  & Logs  │  │  PDF/XLS │  │ Externa  │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BASE DE DATOS                               │
│         MySQL (desarrollo) │ SQL Server 2019 (producción)       │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │
│  │Entities│ │ Facts  │ │ Users  │ │ Alerts │ │AuditLog│        │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología | Razón |
|------|------------|-------|
| **Backend** | FastAPI + Python 3.11 | Ya iniciado, async, rápido |
| **Templates** | Jinja2 + HTMX | Interactividad sin JS complejo |
| **Interactividad** | Alpine.js | Micro-framework, ~15kb, fácil |
| **Gráficos** | Chart.js | Gratuito, todos los tipos de gráfico |
| **CSS** | PicoCSS + CSS custom | Ligero, profesional, tonos azules |
| **Auth** | FastAPI-Users + JWT | Correo/contraseña, extensible a LDAP |
| **ORM** | SQLAlchemy 2.0 | Multi-BD (MySQL dev, SQL Server prod) |
| **Migraciones** | Alembic | Versionado de esquema |
| **PDF** | xhtml2pdf (gratis) | Sin dependencias externas |
| **XBRL** | Arelle | Ya implementado |
| **Servidor** | Uvicorn + Gunicorn | ASGI production-ready |

**💰 Costo total de licencias: $0**

---

## 🎨 Diseño UI/UX

### Estructura de Layout
- **Header:** Logo Corvus, nombre usuario, menú cuenta, notificaciones
- **Aside (sidebar):** Menú de navegación principal
- **Main:** Contenido dinámico (dashboard, reportes, tablas)

### Paleta de Colores
- Tonos azules corporativos (definir con imagen de referencia)

### Idioma
- Español únicamente

---

## 📊 Funcionalidades por Módulo

### 1. Autenticación y Seguridad
- Login con correo/contraseña
- Roles: admin, analista, auditor, solo-lectura
- Fase 2: Integración LDAP/AD
- Auditoría de acciones (login, logout, cambios críticos)
- Retención de logs: 3 años

### 2. Gestión XBRL
- Carga de archivos XBRL (.xbrl, .xml)
- Parsing con Arelle
- Mapeo canónico desde taxonomías SFC
- Validaciones automáticas

### 3. Reportes Financieros
- Balance General
- Estado de Resultados
- Comparativos multi-entidad y multi-periodo

### 4. Indicadores Financieros
- ROE (Return on Equity)
- ROA (Return on Assets)
- Liquidez
- Endeudamiento

### 5. Gráficos y Dashboard
- Barras comparativas
- Líneas de tendencia
- Pie charts
- Treemaps

### 6. Alertas y Reglas
- Configuración de umbrales por indicador
- Alertas automáticas al cargar XBRL
- Estados: nueva, revisada, cerrada

### 7. Exportaciones
- CSV
- XLSX (formateado)
- PDF (con logo corporativo)

### 8. Integraciones Externas (investigar)
- API Superfinanciera
- API Supersociedades

---

## 📅 Cronograma de Desarrollo

### Metodología
- Sprints semanales
- Gestión: Chat (por ahora)
- Repositorio: GitHub

---

### FASE 1: Fundamentos (Semanas 1-4)

| Sprint | Fechas | Entregables |
|--------|--------|-------------|
| **S1** | Sem 1 | Diseño UI/Layout (header, aside, dashboard base), migración a Alpine.js |
| **S2** | Sem 2 | Sistema de autenticación (login, registro, roles básicos) |
| **S3** | Sem 3 | Auditoría y logs (tabla, registro automático login/logout/acciones) |
| **S4** | Sem 4 | Configuración Alembic + soporte dual MySQL/SQL Server |

---

### FASE 2: Core XBRL (Semanas 5-8)

| Sprint | Fechas | Entregables |
|--------|--------|-------------|
| **S5** | Sem 5 | Mejora ingesta XBRL (validaciones, feedback detallado, progreso) |
| **S6** | Sem 6 | Gestión de entidades y periodos (CRUD, búsqueda, filtros) |
| **S7** | Sem 7 | Comparativos multi-entidad/multi-periodo en una vista |
| **S8** | Sem 8 | Exportación mejorada (PDF profesional con logo, XLSX formateado) |

---

### FASE 3: Reportes Financieros (Semanas 9-12)

| Sprint | Fechas | Entregables |
|--------|--------|-------------|
| **S9** | Sem 9 | Balance General dinámico desde facts canónicos |
| **S10** | Sem 10 | Estado de Resultados dinámico |
| **S11** | Sem 11 | Indicadores ROE, ROA, Liquidez, Endeudamiento (cálculo automático) |
| **S12** | Sem 12 | Dashboard con gráficos (barras, líneas, pie charts) |

---

### FASE 4: Alertas y Reglas (Semanas 13-15)

| Sprint | Fechas | Entregables |
|--------|--------|-------------|
| **S13** | Sem 13 | Motor de reglas (configuración de umbrales por indicador) |
| **S14** | Sem 14 | Generación de alertas automáticas al cargar XBRL |
| **S15** | Sem 15 | Panel de alertas, histórico, estados (nueva/revisada/cerrada) |

---

### FASE 5: Integraciones (Semanas 16-18)

| Sprint | Fechas | Entregables |
|--------|--------|-------------|
| **S16** | Sem 16 | Investigación API SFC/Supersociedades, documentación |
| **S17** | Sem 17 | Conector descarga automática XBRL (si API disponible) |
| **S18** | Sem 18 | Sincronización bajo demanda o programada |

---

### FASE 6: Producción (Semanas 19-20)

| Sprint | Fechas | Entregables |
|--------|--------|-------------|
| **S19** | Sem 19 | Migración a SQL Server, pruebas de carga, optimización |
| **S20** | Sem 20 | Documentación usuario/admin, guía despliegue Windows/Linux |

---

## 📊 Línea de Tiempo Visual

```
Dic 2025    Ene 2026      Feb           Mar           Abr           May
   |----F1----|----F2----|----F3----|----F4----|--F5--|--F6--|
     Layout     XBRL       Reportes    Alertas   APIs   Prod
     Auth       Compare    Indicadores Reglas    Sync   Deploy
     Logs       Export     Dashboard
```

**Total estimado: 20 semanas (~5 meses)**

---

## 🖥️ Entornos

| Entorno | Base de Datos | Sistema Operativo |
|---------|---------------|-------------------|
| Desarrollo | MySQL | Windows 10/11 |
| Producción | SQL Server 2019 | Windows Server / Linux |

---

## 📝 Notas Adicionales

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

## 📌 Checklist Inicio de Proyecto

- [x] Definir arquitectura
- [x] Definir stack tecnológico
- [x] Crear cronograma
- [ ] Crear repositorio GitHub
- [ ] Subir imagen referencia UI
- [ ] Iniciar Sprint 1

---

*Documento generado automáticamente - Corvus Analytics v1.0*
