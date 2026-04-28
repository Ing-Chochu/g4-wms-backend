# 🏭 WMS Backend - Grupo 4 (AS/RS Automatizado)

Este repositorio contiene el Producto Mínimo Viable (MVP) para el sistema WMS Backend, diseñado bajo una arquitectura de eventos asíncronos para orquestar la flota de AGVs y gestionar el inventario del almacén.

## 🛠️ Arquitectura y Stack Tecnológico
* **Core API:** FastAPI v0.136.0 (Operaciones asíncronas).
* **Persistencia:** SQLite vía SQLAlchemy 2.0 (Diseño desacoplado, listo para migrar a PostgreSQL).
* **Comunicaciones IoT:** Eclipse Mosquitto (Broker Local) + Paho-MQTT v2.1.0.
* **Algoritmos Core:** Asignación de espacio **FIFO** y enrutamiento base **A*** (A-Star).

## 🚀 Guía de Arranque Rápido

1. **Instalar dependencias:** `pip install -r requirements.txt`
2. **Encender Broker MQTT:** Iniciar Mosquitto de forma local (Puerto 1883).
3. **Levantar Servidor:** `uvicorn app.main:app --reload`
4. **Documentación Interactiva:** Visitar `http://127.0.0.1:8000/docs`

## 📡 Contrato de Interfaces (Manual de API)

### 1. Frontend <-> Backend (HTTP REST)
* **`POST /ordenar_paquete`**: 
  * Recibe un payload JSON con `sku` y `peso`.
  * Calcula la primera celda vacía (FIFO), genera la ruta A* y envía la orden al AGV correspondiente vía MQTT.
* **`GET /inventario`**: 
  * Retorna la lista de paquetes almacenados y su timestamp exacto.

### 2. Backend <-> Firmware (MQTT)
* **Recepción de Telemetría (El Backend escucha):** `wms/agv/+/telemetry`
* **Envío de Comandos (El AGV escucha):** `wms/agv/{agv_id}/commands`