# WMS Backend - AGV Control & Warehouse Management System 🚀

Este repositorio contiene el "cerebro" y motor de orquestación del Sistema de Gestión de Almacenes (WMS) diseñado para el control de robots móviles autónomos (AGV). El backend está desarrollado bajo una arquitectura asíncrona enfocada en el alto rendimiento, la consistencia transaccional de inventarios y el cierre de lazo con hardware en tiempo real.

## 🏗️ Arquitectura del Sistema y Flujo de Datos

El ecosistema se divide en una capa de software web y una red de dispositivos físicos que interactúan de forma distribuida:

* **Framework Core:** FastAPI (Python 3.11+) - Seleccionado por su soporte nativo para operaciones I/O asíncronas (`asyncio`).
* **Motor de Persistencia:** PostgreSQL - Base de datos relacional que garantiza transacciones bajo el estándar ACID.
* **Capa de Transporte IoT:** MQTT (Mosquitto) - Protocolo de mensería liviano para comunicación bidireccional de baja latencia con hardware embebido.
* **Seguridad:** Control de Acceso Basado en Roles (RBAC) y hashing de credenciales mediante Bcrypt nativo.

---

## 🛠️ Estado Actual del Desarrollo (Sprint 3)

### 1. Gestión de Datos y Persistencia (90%)

* [x] Migración arquitectónica completa de SQLite a **PostgreSQL**.
* [x] Modelado relacional de 5 entidades core: `Roles`, `Users`, `Inventory`, `Vehicles` y `WorkOrders`.
* [x] Sistema de inyección automática de datos semilla (Sembrado de Admin maestro al arranque).

### 2. Seguridad y Autenticación (80%)

* [x] Cifrado criptográfico de contraseñas mediante **Bcrypt nativo** en el servidor.
* [x] Endpoints funcionales de autenticación y registro (`/login`, `/usuarios`).
* [x] Configuración de directivas **CORS** para intercomunicación segura con interfaces React/Vite.

### 3. Conectividad de Red y Cierre de Lazo (85%)

* [x] Cliente **MQTT integrado asíncronamente** (`paho-mqtt` v2.0) corriendo en un hilo independiente sin congelar la API web.
* [x] Suscripción activa al árbol de tópicos de telemetría y publicación de comandos.
* [x] **SDK Polimórfico Embebido (`WMS_Client.h`):** Librería unificada en C++ para estandarizar los payloads JSON de los 3 subsistemas físicos del proyecto (AGV, Infraestructura y Visión).

---

## 📦 Contrato de Interfaces de Hardware (SDK Embebido)

Para mitigar fallos por variables mal estructuradas durante la integración, el Backend provee la librería **`WMS_Client.h`**. Al inicializarse, el firmware debe declarar su `TipoDispositivo` (`AGV_SOFTWARE`, `INFRAESTRUCTURA`, o `VISION_ARTIFICIAL`) para habilitar sus funciones nativas y empaquetar automáticamente los JSON hacia los tópicos correctos.

### 📋 Mapeo de Mensajes y Tópicos Estándar

#### 1. Software del AGV (`AGV_SOFTWARE`)

Reporta su estado operativo y velocidad de encoders. No incluye batería ni posición local.

* **Tópico:** `wms/agv/{client_id}/telemetry`
* **Payload JSON:** `{"velocidad": float, "estado": string}`

#### 2. Infraestructura y Racks (`INFRAESTRUCTURA`)

Informa alertas de los sensores de proximidad en estanterías cuando un paquete es posicionado, y capturas del lector QR de entrada para registrar qué mercancía ingresa.

* **Tópico Sensores:** `wms/infra/sensores/eventos` -> `{"pos_x": int, "pos_y": int, "estado_fisico": "ocupado"|"vacio"}`
* **Tópico Lector QR:** `wms/infra/qr/lecturas` -> `{"codigo": string}`

#### 3. Visión Artificial (`VISION_ARTIFICIAL`)

Cámara aérea cenital dedicada a trazar las coordenadas físicas lógicas de la flota en tiempo real.

* **Tópico:** `wms/agv/{target_agv_id}/position`
* **Payload JSON:** `{"x": int, "y": int}`

---

## 👥 Guía de Trabajo Colaborativo (Git Flow)

¡Hola niños! Ya dejé configurado el repositorio central, la estructura de carpetas y las librerías base para nuestro servidor (WMS Backend).

Para que todos podamos trabajar al mismo tiempo sin borrar el código del otro, vamos a usar una regla de oro: **Nadie programa directamente en la rama `main**`. Cada uno creará una "rama" para su tarea, y luego uniremos todo.

Aquí tienen el paso a paso exacto de lo que deben hacer. (Abran la terminal en VS Code y copien estos comandos).

### 🛠️ FASE 1: Descargar el proyecto (Solo se hace la primera vez)

1. **Clonar el repositorio:**
Vayan a la carpeta donde guardan sus proyectos de la universidad y ejecuten:
```bash
git clone https://github.com/Ing-Chochu/g4-wms-backend.git

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

```


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



#### ⚡ Copiado y pegado rápido:

```bash
git add .
git commit -m "feat: "
git push

```

¡Y listo! Cuando su código esté subido, me avisan y yo me encargo de hacer el "Merge" (unir su código con el main de todos).

---

## 📅 Proyecciones y Hoja de Ruta (Sprint 4)

* **Seguridad Avanzada:** Transición de tokens simulados a la implementación estricta de **JSON Web Tokens (JWT)** firmados criptográficamente para resguardar las rutas operativas.
* **Cálculo de Caminos:** Implementación matemática del algoritmo **A* (A-Star)** real en la cuadrícula del almacén para evitar colisiones.
* **Feedback Activo:** Programación de disparadores lógicos dentro del motor MQTT para actualizar de forma automatizada los estados de inventario en la base de datos tras las lecturas físicas de los ESP32.

---

**Desarrollado por:** Arnulfo Josue Sanchez Sanchez

**Semestre:** Noveno - Ingeniería Mecatrónica

**Universidad:** Universidad de Pamplona