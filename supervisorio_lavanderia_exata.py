// ============================================================================
// RESERVATORIO LAVANDERIA EXATA - ESP32
// Sensor hidrostatico 4-20mA + LCD 4x20 (I2C) no quadro + Firebase Realtime DB
// ============================================================================
//
// BIBLIOTECAS NECESSARIAS (instalar via Gerenciador de Bibliotecas do Arduino IDE):
//   - "Firebase ESP Client" por mobizt
//   - "LiquidCrystal I2C" (ex: por Frank de Brabander, ou "LiquidCrystal_I2C")
//
// LIGACOES:
//   - Sensor 4-20mA -> resistor shunt 150 ohms -> pino 35 (ADC) + capacitor
//     de 1uF a 2.2uF entre pino 35 e GND (filtro RC, ver historico de testes).
//   - GND do ESP32 ligado ao negativo da fonte de 24V do loop (OBRIGATORIO).
//   - LCD 4x20 I2C: SDA -> GPIO21, SCL -> GPIO22 (pinos padrao do ESP32).
//     Confirme o endereco I2C do seu modulo (0x27 ou 0x3F sao os mais comuns)
//     rodando um "I2C Scanner" se o display nao acender.
//
// ============================================================================

#include <WiFi.h>
#include <Firebase_ESP_Client.h>
#include <addons/TokenHelper.h>
#include <addons/RTDBHelper.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include "time.h"

// --- CREDENCIAIS - PREENCHER ANTES DE GRAVAR ---
#define WIFI_SSID     "PASTOR ALDO"
#define WIFI_PASSWORD "aldo120586"

#define API_KEY      "AIzaSyBVEUdE5E3LHDpqOrVSOcO9PsVRRPE9rU4"
#define DATABASE_URL "https://lavanderia-exata-default-rtdb.firebaseio.com/" // confirmado
#define USER_EMAIL    "esp32-lavanderia@dispositivo.com"
#define USER_PASSWORD "Res3rvat0rio2026"

FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

// LCD 4x20 via I2C - ajuste o endereco (0x27 ou 0x3F) conforme seu modulo
LiquidCrystal_I2C lcd(0x27, 20, 4);

// --- PINO DO SENSOR ---
const int pinoSensor = 35;

// --- CALIBRACAO DA ESCALA (valores validados em bancada) ---
const float tensaoMin = 0.57;    // tensao no repouso (4mA). Medido na pratica ~0.53V
const float tensaoMax = 3.00;    // tensao em escala cheia (20mA)

// >>> ATENCAO: TROCAR ESTE VALOR NA INSTALACAO FINAL NO CLIENTE <<<
// Sensor atual de BANCADA mede ate 2,00m (usado nos testes de bancada/copo).
// O sensor que sera instalado no cliente mede ate 4,00m (coluna real do
// reservatorio). Antes de instalar de vez, trocar o valor abaixo para 4.00.
const float alturaMaxima = 2.00; // metros - ALTERAR PARA 4.00 na instalacao final

const float capacidadeLitros = 30000.0; // capacidade total do reservatorio do cliente
// Nota: o volume calculated so fara sentido de verdade apos trocar alturaMaxima
// para 4.00 e instalar o sensor definitivo no reservatorio real. Durante os
// testes de bancada com o sensor de 2m, use os valores de "Nivel (m)" para
// validar o funcionamento, e ignore o volume em litros exibido.

// --- Deteccao de falha (cabo rompido / sem alimentacao) ---
const float limitePerdaSinal = 0.20;

// --- Parametros de amostragem (herdados do diagnostico de ruido em bancada) ---
const int nAmostras = 30;
const int intervaloAmostraUs = 1000;

// --- Filtro exponencial (EMA) entre ciclos ---
const float alfaFiltro = 0.4;
float alturaFiltrada = -1.0;

// --- Limites do modo automatico da bomba (ajustar conforme a operacao) ---
const float nivelBaixoPct = 15.0;  // liga a bomba abaixo disso
const float nivelCheioPct = 95.0;  // desliga a bomba acima disso
bool modoAutomaticoBomba = true;   // true = ESP32 decide sozinho; false = so obedece comando web

unsigned long ultimoEnvio = 0;
const unsigned long intervaloCiclo = 5000; // ms entre leituras/envios

// ============================================================================
// SETUP
// ============================================================================
void setup() {
  Serial.begin(115200);

  Wire.begin(); // SDA=21, SCL=22 (padrao ESP32)
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("LAVANDERIA EXATA");
  lcd.setCursor(0, 1);
  lcd.print("Reservatorio 30.000L");
  lcd.setCursor(0, 2);
  lcd.print("Iniciando sistema...");

  pinMode(pinoSensor, INPUT);
  analogSetAttenuation(ADC_11db);

  conectarWiFi();
  configurarHoraNTP();
  conectarFirebase();

  lcd.clear();
}

// Sincroniza o relogio interno do ESP32 via internet (NTP). Isso e OBRIGATORIO
// antes de conectar no Firebase: certificados SSL sao validados por data/hora,
// e o ESP32 sempre liga com o relogio zerado (1970). Sem essa sincronizacao,
// o handshake SSL falha repetidamente (erro "Failed to initialize the SSL layer").
void configurarHoraNTP() {
  configTime(-3 * 3600, 0, "pool.ntp.org", "time.nist.gov"); // -3h = horario de Brasilia
  struct tm timeinfo;
  Serial.print("Sincronizando hora via NTP");
  int tentativas = 0;
  while (!getLocalTime(&timeinfo) && tentativas < 20) {
    Serial.print(".");
    delay(500);
    tentativas++;
  }
  if (tentativas >= 20) {
    Serial.println("\nFalha ao sincronizar hora via NTP - verifique a conexao com a internet.");
  } else {
    Serial.println("\nHora sincronizada com sucesso!");
  }
}

void conectarWiFi() {
  lcd.setCursor(0, 3);
  lcd.print("Conectando WiFi...  ");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado.");
  lcd.setCursor(0, 3);
  lcd.print("WiFi conectado!     ");
  delay(800);
}

void conectarFirebase() {
  config.api_key = API_KEY;
  config.database_url = DATABASE_URL;
  auth.user.email = USER_EMAIL;
  auth.user.password = USER_PASSWORD;
  config.token_status_callback = tokenStatusCallback;
  
  // Limite de tempo de conexao para evitar travamento SSL
  config.timeout.serverResponse = 10000;
  
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
}

// ============================================================================
// LEITURA DO SENSOR (media com descarte de outliers)
// ============================================================================
float leituraFiltrada(int pino, int n, int intervaloUs) {
  int minVal = 4095;
  int maxVal = 0;
  long soma = 0;

  for (int i = 0; i < n; i++) {
    int leitura = analogRead(pino);
    soma += leitura;
    if (leitura < minVal) minVal = leitura;
    if (leitura > maxVal) maxVal = leitura;
    delayMicroseconds(intervaloUs);
  }

  soma -= minVal;
  soma -= maxVal;
  int mediaADC = soma / (n - 2);

  return (mediaADC * 3.3) / 4095.0;
}

// ============================================================================
// ATUALIZACAO DO LCD 4x20
// ============================================================================
void atualizarLCD(float altura, float litros, float pct, bool falha, const String &statusBomba) {
  char linha[21];

  lcd.setCursor(0, 0);
  lcd.print("LAVANDERIA EXATA    ");

  if (falha) {
    lcd.setCursor(0, 1);
    lcd.print("** FALHA SENSOR **  ");
    lcd.setCursor(0, 2);
    lcd.print("Verif. cabo/fonte   ");
    lcd.setCursor(0, 3);
    lcd.print("                    ");
    return;
  }

  snprintf(linha, 21, "Nivel: %5.2f m      ", altura);
  lcd.setCursor(0, 1);
  lcd.print(linha);

  snprintf(linha, 21, "Volume: %6.0f L    ", litros);
  lcd.setCursor(0, 2);
  lcd.print(linha);

  snprintf(linha, 21, "%3.0f%%  Bomba: %-7s", pct, statusBomba.c_str());
  lcd.setCursor(0, 3);
  lcd.print(linha);
}

// ============================================================================
// LOOP PRINCIPAL
// ============================================================================
void loop() {
  unsigned long agora = millis();

  if (agora - ultimoEnvio >= intervaloCiclo) {
    ultimoEnvio = agora;

    float voltagemAtual = leituraFiltrada(pinoSensor, nAmostras, intervaloAmostraUs);
    bool falha = voltagemAtual < limitePerdaSinal;

    float alturaBruta = 0.0, litros = 0.0, pct = 0.0;

    if (!falha) {
      alturaBruta = ((voltagemAtual - tensaoMin) / (tensaoMax - tensaoMin)) * alturaMaxima;
      if (alturaBruta < 0.0) alturaBruta = 0.0;
      if (alturaBruta > alturaMaxima) alturaBruta = alturaMaxima;

      if (alturaFiltrada < 0.0) {
        alturaFiltrada = alturaBruta;
      } else {
        alturaFiltrada = alfaFiltro * alturaBruta + (1.0 - alfaFiltro) * alturaFiltrada;
      }

      litros = (alturaFiltrada / alturaMaxima) * capacidadeLitros;
      pct = (alturaFiltrada / alturaMaxima) * 100.0;
    }

    // --- Logica do modo automatico da bomba (opcional) ---
    String statusBomba = "OFF";
    if (Firebase.ready()) {
      if (Firebase.RTDB.getString(&fbdo, "controle/bomba")) {
        statusBomba = fbdo.stringData();
      }

      if (modoAutomaticoBomba && !falha) {
        if (pct <= nivelBaixoPct && statusBomba != "ON") {
          Firebase.RTDB.setString(&fbdo, "controle/bomba", "ON");
          statusBomba = "ON";
        } else if (pct >= nivelCheioPct && statusBomba != "OFF") {
          Firebase.RTDB.setString(&fbdo, "controle/bomba", "OFF");
          statusBomba = "OFF";
        }
      }
    }

    // --- Atualiza o LCD no quadro ---
    atualizarLCD(alturaFiltrada, litros, pct, falha, statusBomba);

    // --- Envia para o Firebase (alimenta o supervisorio web) ---
    if (Firebase.ready()) {
      FirebaseJson json;
      json.set("nivel_metros", alturaFiltrada);
      json.set("volume_litros", litros);
      json.set("percentual", pct);
      json.set("falha_sensor", falha);
      json.set("ultimo_pulso/.sv", "timestamp");

      if (!Firebase.RTDB.updateNode(&fbdo, "reservatorio", &json)) {
        Serial.print("[Firebase Erro] Falha ao atualizar: ");
        Serial.println(fbdo.errorReason().c_str());
      } else {
        Serial.println("[Firebase OK] Dados enviados com sucesso.");
      }
    } else {
      Serial.print("[Firebase Aguardando] Estado do token: ");
      Serial.println(Firebase.authenticated() ? "Autenticado, aguardando ready" : "Nao autenticado");
    }

    // --- Log serial para debug em bancada ---
    if (falha) {
      Serial.print("[Tensao: ");
      Serial.print(voltagemAtual, 3);
      Serial.println(" V] -> FALHA_SENSOR (SINAL PERDIDO / CABO ROMPIDO)");
    } else {
      Serial.print("[Tensao: ");
      Serial.print(voltagemAtual, 3);
      Serial.print(" V] -> Nivel: ");
      Serial.print(alturaFiltrada, 2);
      Serial.print(" m -> Volume: ");
      Serial.print(litros, 0);
      Serial.print(" L -> ");
      Serial.print(pct, 0);
      Serial.print("% -> Bomba: ");
      Serial.println(statusBomba);
    }
  }
}

// v1.3 - LAVANDERIA EXATA: Estabilizacao do envio Firebase em lote + Compatibilidade total de Timestamp com Streamlit
