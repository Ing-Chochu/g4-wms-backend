import json
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
        self.command_topic = "wms/agv/{}/commands"   # Para enviar rutas
        
        # Paho MQTT v2.0+ exige declarar la versión de la API internamente
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        
        # Conectar los eventos (cuando se conecte y cuando reciba mensaje)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info("✅ Conectado exitosamente al Broker MQTT local")
            self.client.subscribe(self.telemetry_topic)
            logger.info(f"📡 Suscrito a telemetría: {self.telemetry_topic}")
        else:
            logger.error(f"❌ Error al conectar MQTT. Código: {reason_code}")

    def on_message(self, client, userdata, msg):
        try:
            # Todo lo que mande el robot (batería, coordenadas) se lee aquí
            payload = json.loads(msg.payload.decode("utf-8"))
            logger.info(f"📩 Telemetría recibida de [{msg.topic}]: {payload}")
            
            # Más adelante, aquí guardaremos estos datos en la Base de Datos
            
        except json.JSONDecodeError:
            logger.warning(f"⚠️ Mensaje no-JSON ignorado en {msg.topic}")

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