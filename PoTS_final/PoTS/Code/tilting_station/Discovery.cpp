#include "Discovery.h"

#include <WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>

extern WiFiUDP udp;

extern const uint16_t DISCOVERY_PORT=4210;

void startDiscovery()
{
    udp.begin(DISCOVERY_PORT);

    Serial.print("UDP Discovery started on port ");
    Serial.println(DISCOVERY_PORT);
}

void handleDiscovery()
{
    int packetSize = udp.parsePacket();
    if (packetSize > 0)
    {
        Serial.print("UDP packet received. Size: ");
        Serial.println(packetSize);
    }
    if (packetSize <= 0)
        return;
    Serial.print("[DISCOVERY] UDP packet received. Size = ");
    Serial.println(packetSize);
    char buffer[64];

    int len = udp.read(buffer, sizeof(buffer)-1);

    if(len <= 0)
        return;

    buffer[len] = '\0';
    Serial.print("[DISCOVERY] Message = ");
    Serial.println(buffer);

    if(strcmp(buffer, "DISCOVER_POTS") != 0)
        return;

    StaticJsonDocument<256> doc;

    doc["device"] = "POTS";
    doc["name"] = "Powder Tilting Station";
    doc["version"] = "1.0";
    doc["tcp_port"] = 80;

    char reply[256];

    serializeJson(doc, reply);

    udp.beginPacket(
        udp.remoteIP(),
        udp.remotePort());

    udp.print(reply);

    udp.endPacket();

    Serial.println("Discovery response sent.");
}
