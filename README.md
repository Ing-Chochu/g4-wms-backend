# WMS Backend - AGV Control & Warehouse Management System 🚀

Este repositorio contiene el "cerebro" del sistema de gestión de almacenes (WMS) para el control de robots móviles autónomos (AGV). El backend está desarrollado bajo una arquitectura de microservicios asíncronos enfocada en el alto rendimiento, la trazabilidad de inventarios y la seguridad industrial.

## 🏗️ Arquitectura del Sistema
El sistema se basa en una estructura modular que separa la lógica de negocio, la persistencia de datos y la comunicación IoT.

* **Framework:** FastAPI (Python 3.11+) - Seleccionado por su soporte nativo para `asyncio`.
* **Base de Datos:** PostgreSQL - Motor relacional para integridad de datos.
* **Protocolo IoT:** MQTT (Mosquitto) - Comunicación bidireccional en tiempo real con hardware.
* **Seguridad:** RBAC (Role-Based Access Control) con hashing Bcrypt.



## 🛠️ Estado Actual del Desarrollo (Sprint 3 - Finalizado)

### 1. Gestión de Datos y Persistencia (90%)
- [x] Migración completa de SQLite a **PostgreSQL**.
- [x] Modelado de entidades: `Users`, `Roles`, `Inventory`, `WorkOrders` y `Vehicles`.
- [x] Sistema de inyección de datos semilla (Sembrado automático de Admin al arrancar).

### 2. Seguridad y Autenticación (80%)
- [x] Implementación de **Bcrypt nativo** para protección de credenciales.
- [x] Endpoints de Registro y Login (`/usuarios`, `/login`).
- [x] Configuración de **CORS** para integración segura con el Frontend (React/Vite).

### 3. Lógica Logística y Algoritmos (75%)
- [x] **Asignación FIFO:** Algoritmo de búsqueda de espacios disponibles en la matriz de almacenamiento.
- [x] **Cálculo de Rutas:** Integración inicial del algoritmo de búsqueda de caminos (Pathfinding).
- [x] Contratos de datos (Schemas) alineados con los requisitos del equipo de Interfaz.

### 4. Conectividad Industrial (80%)
- [x] Cliente **MQTT integrado** asíncrono (Paho-MQTT).
- [x] Publicación de comandos de ruta formateados en JSON.
- [x] Suscripción activa a telemetría de AGVs.

---

## 📅 Hoja de Ruta (Lo que falta por pulir)

Para el cierre del proyecto (Sprint 4), se tienen proyectadas las siguientes mejoras y adiciones técnicas:

### 🛡️ Seguridad Avanzada
* **Implementación de JWT (JSON Web Tokens):** Pasar de tokens simulados a tokens reales firmados para proteger cada endpoint.
* **Middleware de Autorización:** Restringir el acceso a funciones críticas (como mover robots) solo a usuarios con rol `admin`.

### 🧠 Optimización del "Cerebro" (Algoritmia)
* **Refactorización de A* (A-Star):** Implementar la lógica de evitación de obstáculos dinámica basándose en la telemetría en tiempo real de otros AGVs.
* **Optimización de Matriz:** Lógica para redistribución de carga (Slotting optimization).

### 🔄 Cierre de Lazo (Feedback Loop)
* **Manejador de Mensajes (on_message):** Programar el procesamiento automático de la telemetría para actualizar el estado del inventario en la DB de `in_transit` a `stored` sin intervención humana.
* **Gestión de Errores MQTT:** Lógica de reintento y "Last Will and Testament" para detectar desconexiones de robots.

### 📊 Monitoreo en Tiempo Real
* **WebSockets:** Implementar un canal de datos en vivo para enviar la posición X,Y de los AGVs al Dashboard sin necesidad de refrescar la página.

---

## 🚀 Instalación y Pruebas Rápidas

1.  **Clonar el repositorio:** `git clone [URL-DEL-REPO]`
2.  **Activar Entorno Virtual:** `source venv/bin/activate` o `.\venv\Scripts\activate`
3.  **Instalar Dependencias:** `pip install -r requirements.txt`
4.  **Configurar Variables de Entorno:** (Ver archivo `.env.example`)
5.  **Ejecutar Servidor:** ```bash
    uvicorn app.main:app --reload
    ```
6.  **Documentación Interactiva:** Visitar `http://127.0.0.1:8000/docs` para probar los endpoints.