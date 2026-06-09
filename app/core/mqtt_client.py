import json
import asyncio
import paho.mqtt.client as mqtt
import logging

# Configuración de logs para que la terminal se vea profesional
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MQTT_WMS")

class MQTTManager:
    def __init__(self):
        self.broker_address = "localhost"
        self.port = 1883
        
        # ÁRBOL DE TÓPICOS (El contrato de interfaces para los AGVs)
        self.telemetry_topic = "wms/agv/+/telemetry" # Escucha a TODOS los agv (+ es comodín)
        self.qr_topic = "wms/infra/qr/lecturas"      # Tópico del lector físico
        self.alert_topic = "wms/sistema/alerta"      # Para notificar errores
        self.command_topic = "wms/agv/{}/commands"   # Para enviar rutas
        
        # Puente para WebSockets
        self._event_loop = None
        self._broadcast_fn = None

        # Paho MQTT v2.0+ exige declarar la versión de la API internamente
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        
        # Conectar los eventos (cuando se conecte y cuando reciba mensaje)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def set_ws_bridge(self, loop, broadcast_fn):
        self._event_loop = loop
        self._broadcast_fn = broadcast_fn

    def _emit_ws(self, data: dict):
        if self._broadcast_fn and self._event_loop:
            asyncio.run_coroutine_threadsafe(
                self._broadcast_fn(data), self._event_loop
            )

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info("✅ Conectado exitosamente al Broker MQTT local")
            self.client.subscribe(self.telemetry_topic)
            self.client.subscribe(self.qr_topic)
            logger.info(f"📡 Suscrito a telemetría: {self.telemetry_topic}")
            logger.info(f"📡 Suscrito a lecturas QR: {self.qr_topic}")
        else:
            logger.error(f"❌ Error al conectar MQTT. Código: {reason_code}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            
            if msg.topic == self.qr_topic:
                self._handle_qr_scan(payload)
            elif "telemetry" in msg.topic:
                agv_id = msg.topic.split("/")[2]
                self._handle_agv_telemetry(agv_id, payload)
            else:
                logger.info(f"📩 Mensaje recibido de [{msg.topic}]: {payload}")
            
        except json.JSONDecodeError:
            logger.warning(f"⚠️ Mensaje no-JSON ignorado en {msg.topic}")

    def _handle_agv_telemetry(self, agv_id: str, payload: dict):
        from app.database.database import SessionLocal
        from app.database.models import Vehicle
        
        db = SessionLocal()
        try:
            vehicle = db.query(Vehicle).filter(Vehicle.id == agv_id).first()
            if not vehicle:
                vehicle = Vehicle(id=agv_id)
                db.add(vehicle)
            
            vehicle.battery_level = payload.get("bateria", vehicle.battery_level)
            vehicle.status = payload.get("estado", vehicle.status)
            vehicle.pos_x = payload.get("x", vehicle.pos_x)
            vehicle.pos_y = payload.get("y", vehicle.pos_y)
            db.commit()

            # Retransmitir al frontend vía WebSocket
            self._emit_ws({"event": "telemetry", "agv_id": agv_id, "data": payload})
        except Exception as e:
            logger.error(f"Error actualizando telemetría para {agv_id}: {e}")
        finally:
            db.close()

    def _handle_qr_scan(self, payload: dict):
        """Procesa el ingreso de un paquete detectado por QR"""
        from app.database.database import SessionLocal
        from app.database.models import Inventory, Vehicle
        from app.services import algorithms

        sku = payload.get("codigo")
        if not sku:
            return

        db = SessionLocal()
        try:
            # 1. Verificar si el producto existe en el catálogo maestro
            producto = db.query(Inventory).filter(Inventory.sku == sku, Inventory.status == "registrado").first()

            if not producto:
                logger.error(f"🚨 ALARMA: SKU {sku} no reconocido o ya almacenado.")
                self.client.publish(self.alert_topic, json.dumps({
                    "error": "Producto no registrado",
                    "sku": sku,
                    "timestamp": "now"
                }))
                self._emit_ws({
                    "event": "alarma",
                    "tipo": "alarma",
                    "mensaje": f"Producto no registrado: {sku}",
                    "sku": sku
                })
                return

            # 2. Asignar espacio mediante FIFO
            occupied = db.query(Inventory.pos_x, Inventory.pos_y).filter(Inventory.status != "removed").all()
            occupied_list = [{"x": o.pos_x, "y": o.pos_y} for o in occupied]
            
            target_pos = algorithms.find_first_empty_slot_fifo(occupied_list)
            if not target_pos:
                logger.warning("📦 Almacén lleno, no hay espacio para el nuevo paquete.")
                return

            # 3. Seleccionar AGV disponible (agv1 por defecto para este prototipo)
            agv = db.query(Vehicle).filter(Vehicle.status == "idle").first()
            agv_id = agv.id if agv else "agv1"

            # 4. Calcular ruta A* (Suponiendo que el QR está en el origen 0,0)
            route = algorithms.calculate_a_star_route({"x": 0, "y": 0}, target_pos)

            # 5. Publicar comando al AGV
            command = {
                "action": "store",
                "sku": sku,
                "target": target_pos,
                "path": route
            }
            self.publish_command(agv_id, command)

            # 6. Actualizar Base de Datos
            producto.status = "in_transit"
            producto.pos_x = target_pos["x"]
            producto.pos_y = target_pos["y"]
            db.commit()
            logger.info(f"✅ Paquete {sku} asignado a {target_pos} vía {agv_id}")

        except Exception as e:
            logger.error(f"❌ Error procesando QR: {e}")
        finally:
            db.close()

    def start(self):
        """Inicia el cliente en un hilo fantasma para no congelar FastAPI"""
        try:
            self.client.connect(self.broker_address, self.port, 60)
            self.client.loop_start() 
        except ConnectionRefusedError:
            logger.error("❌ No se pudo conectar a Mosquitto. ¿Seguro que está encendido?")

    def stop(self):
        """Desconecta de forma segura cuando el servidor se apaga"""
        logger.info("🔌 Desconectando MQTT...")
        self.client.loop_stop()
        self.client.disconnect()

    def publish_command(self, agv_id: str, command_data: dict):
        """Función que usaremos después para enviar el algoritmo A* al robot"""
        topic = self.command_topic.format(agv_id)
        payload = json.dumps(command_data)
        self.client.publish(topic, payload)
        logger.info(f"📤 Comando enviado a [{topic}]: {payload}")

# Instancia global lista para ser importada por el main.py
mqtt_client = MQTTManager()