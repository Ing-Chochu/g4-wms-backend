import time
import requests
import asyncio
import websockets
import paho.mqtt.publish as publish
import json

# Configuraciones base
API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/alertas"
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

print("🚀 INICIANDO BATERÍA DE PRUEBAS END-TO-END WMS...\n")

def test_1_seguridad():
    print("⏳ Prueba 1: Blindaje de Rutas (Seguridad JWT)...")
    
    # 1.1 Intento sin token (Ruta corregida a /inventario)
    res_sin_token = requests.get(f"{API_URL}/inventario")
    if res_sin_token.status_code == 401:
        print("   ✅ Bloqueo exitoso: Ruta protegida contra accesos sin token.")
    else:
        print(f"   ❌ Fallo: La ruta devolvió {res_sin_token.status_code} en lugar de 401.")
        return False

    # 1.2 Obtener token (Ruta corregida a /login y envío como JSON)
    try:
        res_login = requests.post(f"{API_URL}/login", json={"username": "admin", "password": "Adm@2025!"})
        token = res_login.json().get("access_token")
        
        # 1.3 Intento con token
        headers = {"Authorization": f"Bearer {token}"}
        res_con_token = requests.get(f"{API_URL}/inventario", headers=headers)
        
        if res_con_token.status_code == 200:
            print("   ✅ Acceso exitoso: El token es válido y permite la consulta.")
        else:
            print(f"   ❌ Fallo: Autenticación fallida con token válido.")
            return False
            
        return token
    except Exception as e:
        print(f"   ❌ Fallo crítico en Login: {e}")
        return False

def test_2_lazo_cerrado_db(token):
    print("\n⏳ Prueba 2: Lazo Cerrado (Sensor físico a Base de Datos)...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Tópico alineado con mqtt_client.py
    topic_sensor = "wms/infra/sensores/eventos"
    payload = json.dumps({"pos_x": 1, "pos_y": 1, "estado_fisico": "ocupado"})
    
    try:
        publish.single(topic_sensor, payload, hostname=MQTT_BROKER, port=MQTT_PORT)
        print("   -> Mensaje MQTT de sensor inyectado.")
        
        # Margen para procesamiento asíncrono
        time.sleep(1.5)
        
        # Verificamos inventario general
        res = requests.get(f"{API_URL}/inventario", headers=headers)
        data = res.json().get("inventario", [])
        
        # Buscamos si algún item pasó a 'stored'
        if any(item['status'] == 'stored' for item in data):
            print("   ✅ Lazo cerrado exitoso: La base de datos detectó el cambio de sensor.")
        else:
            print(f"   ❌ Fallo: No se encontraron items con estado 'stored'.")
            
    except Exception as e:
        print(f"   ❌ Fallo en la prueba de lazo cerrado: {e}")

async def test_3_websockets():
    print("\n⏳ Prueba 3: Puente de Alertas en Tiempo Real (MQTT -> WebSocket)...")
    
    try:
        # Conectamos al WebSocket
        async with websockets.connect(WS_URL) as ws:
            print("   -> Cliente WebSocket conectado esperando alertas.")
            
            # Disparamos el error físico vía MQTT
            topic_agv = "wms/agv/agv1/telemetry"
            payload_error = json.dumps({"estado": "error", "bateria": 15, "x": 0, "y": 0})
            publish.single(topic_agv, payload_error, hostname=MQTT_BROKER, port=MQTT_PORT)
            print("   -> Mensaje MQTT de Colisión inyectado.")
            
            # Esperamos la respuesta en el WebSocket (timeout de 3 segundos)
            respuesta = await asyncio.wait_for(ws.recv(), timeout=3.0)
            
            if "alarma_critica" in respuesta:
                print("   ✅ Puente exitoso: El FrontEnd recibió la alerta en tiempo real.")
            else:
                print("   ❌ Fallo: Se recibió un mensaje, pero no es la alerta esperada.")
                
    except asyncio.TimeoutError:
        print("   ❌ Fallo de Latencia: El mensaje no llegó al WebSocket a tiempo.")
    except Exception as e:
        print(f"   ❌ Fallo en la conexión WebSocket: {e}")

def run_all():
    # Ejecutamos secuencialmente
    token = test_1_seguridad()
    if token:
        test_2_lazo_cerrado_db(token)
    
    # El test de websockets requiere el event loop asíncrono
    asyncio.run(test_3_websockets())
    
    print("\n🏁 BATERÍA DE PRUEBAS FINALIZADA.")

if __name__ == "__main__":
    run_all()