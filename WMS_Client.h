#ifndef WMS_CLIENT_H
#define WMS_CLIENT_H

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// Definición de tipos de dispositivos en el sistema
enum TipoDispositivo { AGV_SOFTWARE, INFRAESTRUCTURA, VISION_ARTIFICIAL };

class WMSClient {
  private:
    const char* client_id;
    TipoDispositivo tipo;
    WiFiClient espClient;
    PubSubClient mqtt;
    const char* broker_ip;

  public:
    // Constructor: Recibe el ID único del dispositivo y qué rol cumple
    WMSClient(const char* id, TipoDispositivo t) : client_id(id), tipo(t), mqtt(espClient) {}

    // Configuración de red y conexión al Broker
    void begin(const char* ssid, const char* password, const char* broker) {
      this->broker_ip = broker;
      Serial.print("🌐 Conectando a red WiFi: ");
      Serial.println(ssid);
      
      WiFi.begin(ssid, password);
      while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
      }
      Serial.println("\n✅ WiFi Conectado de forma exitosa!");

      mqtt.setServer(broker_ip, 1883);
    }

    // Mantiene el bucle de comunicación activo (Debe ir en el loop principal)
    void loop() {
      if (!mqtt.connected()) {
        reconnect();
      }
      mqtt.loop();
    }

    // =========================================================================
    // 🤖 FUNCIONES PARA EL EQUIPO DE AGV (SOFTWARE)
    // =========================================================================
    void enviarEstadoAGV(float velocidad, const char* estado_mecanico) {
      if (tipo != AGV_SOFTWARE) {
        Serial.println("❌ Error: Este dispositivo no está configurado como AGV");
        return;
      }
      if (!mqtt.connected()) return;

      StaticJsonDocument<128> doc;
      doc["velocidad"] = velocidad;
      doc["estado"] = estado_mecanico;

      String payload;
      serializeJson(doc, payload);
      
      String topico = String("wms/agv/") + client_id + "/telemetry";
      mqtt.publish(topico.c_str(), payload.c_str());
    }

    // =========================================================================
    // 🏗️ FUNCIONES PARA EL EQUIPO DE INFRAESTRUCTURA (RACKS Y QR)
    // =========================================================================
    
    // Alerta cuando los sensores de proximidad/peso detectan o liberan un espacio
    void actualizarSensorEstanteria(int pos_x, int pos_y, const char* estado_fisico) {
      if (tipo != INFRAESTRUCTURA) {
        Serial.println("❌ Error: Este dispositivo no es de Infraestructura");
        return;
      }
      if (!mqtt.connected()) return;

      StaticJsonDocument<128> doc;
      doc["pos_x"] = pos_x;
      doc["pos_y"] = pos_y;
      doc["estado_fisico"] = estado_fisico; // "ocupado" o "vacio"

      String payload;
      serializeJson(doc, payload);
      
      mqtt.publish("wms/infra/sensores/eventos", payload.c_str());
    }

    // Reporta la lectura del QR cuando ingresa una caja al almacén
    void reportarLecturaQR(const char* codigo_qr) {
      if (tipo != INFRAESTRUCTURA) {
        Serial.println("❌ Error: Este dispositivo no es de Infraestructura");
        return;
      }
      if (!mqtt.connected()) return;

      StaticJsonDocument<128> doc;
      doc["codigo"] = codigo_qr;

      String payload;
      serializeJson(doc, payload);
      
      mqtt.publish("wms/infra/qr/lecturas", payload.c_str());
    }

    // =========================================================================
    // 👁️ FUNCIONES PARA EL EQUIPO DE VISIÓN ARTIFICIAL (CÁMARA)
    // =========================================================================
    void reportarPosicionVehiculo(const char* target_agv_id, int x, int y) {
      if (tipo != VISION_ARTIFICIAL) {
        Serial.println("❌ Error: Este dispositivo no es el sistema de Visión");
        return;
      }
      if (!mqtt.connected()) return;

      StaticJsonDocument<128> doc;
      doc["x"] = x;
      doc["y"] = y;

      String payload;
      serializeJson(doc, payload);
      
      // Publica directamente en el tópico del carro rastreado
      String topico = String("wms/agv/") + target_agv_id + "/position";
      mqtt.publish(topico.c_str(), payload.c_str());
    }

  private:
    void reconnect() {
      while (!mqtt.connected()) {
        Serial.print("🔄 Intentando conectar al nodo WMS MQTT...");
        
        // Creamos un ID único de conexión MQTT basado en su rol
        String clientIdMqtt = String("WMS_Node_") + client_id;
        
        if (mqtt.connect(clientIdMqtt.c_str())) {
          Serial.println(" ¡Conectado con éxito!");
          // Aquí nos suscribiremos a comandos si el AGV lo requiere
        } else {
          Serial.print(" falló, rc=");
          Serial.print(mqtt.state());
          Serial.println(" Reintentando en 5 segundos...");
          delay(5000);
        }
      }
    }
};

#endif