# WMS Backend - AGV Control & Warehouse Management System 🚀

Este repositorio contiene el "cerebro" y motor de orquestación del Sistema de Gestión de Almacenes (WMS) diseñado para el control, localización y despacho de robots móviles autónomos (AGV). El backend está desarrollado bajo una arquitectura asíncrona de alto rendimiento, garantizando la consistencia transaccional de inventarios y el cierre de lazo con hardware en tiempo real a través de protocolos IoT y WebSockets.

## 🏗️ Arquitectura del Sistema y Flujo de Datos

El ecosistema de software interactúa de forma distribuida combinando servicios de red de alta disponibilidad y lógica concurrente:

* **Framework Core:** FastAPI (Python 3.11+) - Operaciones I/O asíncronas nativas mediante `asyncio` y ciclo de vida administrado por manejadores de contexto (`lifespan`).
* **Motor de Persistencia:** PostgreSQL - Base de datos relacional para almacenamiento robusto bajo el estándar ACID, con inyección automática de datos semilla y migraciones de esquemas automatizadas al arranque.
* **Capa de Transporte IoT:** MQTT (Mosquitto) - Cliente asíncrono multi-hilo (`paho-mqtt` v2.0) integrado directamente al ecosistema para la suscripción de telemetría de baja latencia y publicación de comandos HMI.
* **Comunicación HMI en Tiempo Real:** Servidor WebSockets nativo encargado del broadcast de telemetría posicional y despacho inmediato de alarmas críticas hacia las interfaces de usuario.
* **Seguridad Avanzada:** Control de Acceso Basado en Roles (RBAC), encriptación criptográfica de contraseñas mediante `Bcrypt`, y autenticación estricta basada en **JSON Web Tokens (JWT)** con validación cruzada por tokens de sesión únicos en Base de Datos.

---

## 🛠️ Estado y Funcionalidades del Backend (Producción)

### 1. Gestión de Datos, Persistencia y Auditoría
* Mapeo relacional de **7 entidades core** implementadas en SQLAlchemy: `Role`, `User`, `Inventory`, `Vehicle`, `TelemetryLog`, `WorkOrder` y `AuditLog`.
* Mecanismo de siembra automatizado al inicio del servidor para garantizar la existencia de los roles principales (`superadmin`, `admin`, `operario`), las credenciales maestras preconfiguradas y la flota inicial de AGVs (`AGV_01`, `AGV_02`, `agv1`).
* **Mantenimiento Automatizado:** Tarea cron diaria integrada con `APScheduler` encargada de ejecutar rutinas de purga en la base de datos cada mañana a las 03:00 AM, eliminando logs de telemetría mayores a 24 horas y registros de auditoría mayores a 30 días para optimizar el performance del servidor.

### 2. Autenticación y Ciberseguridad Robusta
* Cifrado en servidor mediante `passlib[bcrypt]` para resguardar las credenciales de usuarios.
* Endpoints securizados de gestión (`/login`, `/usuarios`) con inyección de dependencias por portador de fichas (`HTTPBearer`). El sistema invalida dinámicamente accesos previos si el `session_token` del JWT no coincide con el registro activo en la BD.
* Políticas de Intercambio de Recursos de Origen Cruzado (**CORS**) completamente abiertas a nivel LAN para facilitar la intercomunicación con tableros de control en React/Vite.

### 3. Conectividad IoT y Lazo Cerrado (Broker MQTT)
* Hilo independiente para el bucle de red MQTT que impide la congelación de los endpoints HTTP.
* **Feedback Activo (Lazo Cerrado):** Sincronización en tiempo real entre eventos físicos del almacén y la persistencia de datos:
  * **Ingreso por QR:** Al detectar un código de barras de mercancía en el punto de entrada, el sistema consulta el inventario, calcula una posición libre por orden de llegada (FIFO), computa una trayectoria ideal y le publica la orden de movimiento al robot asignado.
  * **Confirmación de Racks:** Al posicionarse físicamente la carga en la estantería, los sensores de proximidad reportan el evento por MQTT, lo que dispara un cambio automático de estado del ítem de `"in_transit"` a `"stored"` usando bloqueos de concurrencia selectivos (`FOR UPDATE`).

### 4. Generación Dinámica de Códigos QR para la Flota
* Endpoint dedicado (`/robots`) para registrar nuevas unidades con especificaciones de carga útil, modelo, velocidad máxima y autonomía.
* Compilación e incrustación automática de la IP de la red local del servidor para interpretar la URI de emparejamiento. El sistema genera una etiqueta QR en formato PNG con diseño estilizado y la retorna directamente al cliente en formato Base64 para su impresión física inmediata.

---

## 📦 Contrato de Interfaces de Hardware (Mensajería MQTT)

Para homogeneizar los payloads JSON transmitidos por el SDK unificado en C++ (`WMS_Client.h`), los tópicos y estructuras de datos obligatorias quedan definidos de la siguiente manera:

### 📋 Mapeo de Mensajes y Tópicos Estándar

#### 1. Telemetría Unificada de la Flota (AGV & Visión)
Concentra los datos posicionales calculados por cámaras cenitales y el estado interno enviado por los microcontroladores (ESP32/Raspberry Pi) de los AGVs.

* **Tópico:** `wms/agv/{client_id}/telemetry`
* **Payload JSON:**
```json
{
  "bateria": float,
  "estado": "idle" | "moving" | "charging" | "error",
  "x": int,
  "y": int
}

#### 2. Infraestructura, Sensores y Racks

Informa alertas físicas provenientes de los sensores ópticos/infrarrojos de las celdas del almacén y del lector QR de entrada.

* **Tópico Sensores de Estantería:** `wms/infra/sensores/eventos`
* **Payload JSON:** `{"pos_x": int, "pos_y": int, "estado_fisico": "ocupado" | "vacio"}`


* **Tópico Lector QR Principal:** `wms/infra/qr/lecturas`
* **Payload JSON:** `{"codigo": string}`



#### 3. Tópico de Comandos y Rutas Hacia el AGV

Ruta de navegación calculada por el backend en una cuadrícula lógica (por defecto de 5x4) usando un algoritmo simplificado de búsqueda de caminos óptimos.

* **Tópico:** `wms/agv/{client_id}/commands`
* **Payload JSON:**

```json
{
  "action": "store" | "almacenar",
  "sku": string,
  "target": {"x": int, "y": int},
  "path": [{"x": int, "y": int}, {"x": int, "y": int}]
}

```

---

## 👥 Guía de Trabajo Colaborativo (Git Flow)

¡Hola niños! Ya dejé configurado el repositorio central, la estructura de carpetas y las librerías base para nuestro servidor (WMS Backend).

Para que todos podamos trabajar al mismo tiempo sin borrar el código del otro, vamos a usar una regla de oro: **Nadie programa directamente en la rama `main**`. Cada uno creará una "rama" para su tarea, y luego uniremos todo.

Aquí tienen el paso a paso exacto de lo que deben hacer. (Abran la terminal en VS Code y copien estos comandos).

### 🛠️ FASE 1: Descargar el proyecto (Solo se hace la primera vez)

1. **Clonar el repositorio:**
Vayan a la carpeta donde guardan sus proyectos de la universidad y ejecuten:

```bash
git clone [https://github.com/Ing-Chochu/g4-wms-backend.git](https://github.com/Ing-Chochu/g4-wms-backend.git)

```

2. **Entrar a la carpeta del proyecto:**

```bash
cd g4-wms-backend

```

3. **Crear el Entorno Virtual (Nuestra burbuja de trabajo):**

```bash
python -m venv venv

```

4. **Activar el Entorno:**

* **En Windows:** ```bash
.\venv\Scripts\activate

```
*(Nota: Si les sale un error rojo en Windows, primero ejecuten `Set-ExecutionPolicy Unrestricted -Scope CurrentUser` y luego intenten de nuevo).*

* **En macOS/Linux:**
```bash
source venv/bin/activate

```

*(Deben ver un `(venv)` verde en su terminal. Si no lo ven, no avancen).*

5. **Instalar todas las librerías mágicamente:**

```bash
pip install -r requirements.txt

```

### 👨‍💻 FASE 2: Empezar a trabajar en tu tarea (La Regla de Oro)

Antes de escribir una sola línea de código, debes crear tu propia rama para no dañar el proyecto principal.

1. **Actualiza tu compu (por si alguien subió algo nuevo):**

```bash
git pull origin main

```

2. **Crea tu rama y muévete a ella:**
*(Cambia `mi-tarea` por lo que vayas a hacer, ej: `feat/base-de-datos` o `feat/api-login`).*

```bash
git checkout -b feat/mi-tarea

```

### 💾 FASE 3: Guardar y subir tus cambios (El Pan de cada día)

Cuando termines una función o al final del día de trabajo, debes guardar tu progreso en la nube. Ejecuta estos 3 comandos en orden:

1. **Prepara todos los archivos que cambiaste:**

```bash
git add .

```

2. **Toma la "foto" y ponle un mensaje de qué hiciste:**

```bash
git commit -m "feat: agregue las tablas de usuarios y roles"

```

3. **Sube tu rama a GitHub:**
*(La primera vez que subas tu rama, usa este comando completo. Las siguientes veces solo bastará con poner `git push`).*

```bash
git push -u origin feat/mi-tarea

```

#### ⚡ Copiado y pegado rápido para actualizaciones subsecuentes:

```bash
git add .
git commit -m "feat: <mensaje_aqui>"
git push

```

¡Y listo! Cuando su código esté subido, me avisan y yo me encargo de hacer el "Merge" (unir su código con el main de todos).

---

**Desarrollado por:** Arnulfo Josue Sanchez Sanchez, Tomas Betancurd, Angel Cardenas y Gabriel Vega

**Semestre:** Noveno - Ingeniería Mecatrónica

**Universidad:** Universidad de Pamplona