#include <SimpleFOC.h>

// ================================================================
// MT6701 ABZ encoder — 1024 PPR
// ================================================================
#define ENC_A_PIN  19
#define ENC_B_PIN  18
#define ENC_Z_PIN   5

Encoder encoder = Encoder(ENC_A_PIN, ENC_B_PIN, 1024, ENC_Z_PIN);

void IRAM_ATTR doA() { encoder.handleA(); }
void IRAM_ATTR doB() { encoder.handleB(); }
void IRAM_ATTR doZ() { encoder.handleIndex(); }

// ================================================================
// Motor + driver — SimpleFOCMini / DRV8313
// ================================================================
#define IN1_PIN    25
#define IN2_PIN    26
#define IN3_PIN    27
#define EN_PIN     14
#define FAULT_PIN   4   // GPIO4 supports INPUT_PULLUP (GPIO35 does not)

// 2804 motor — 12N14P = 7 pole pairs
BLDCMotor  motor  = BLDCMotor(7);
BLDCDriver3PWM driver = BLDCDriver3PWM(IN1_PIN, IN2_PIN, IN3_PIN, EN_PIN);

// ================================================================
// Commander
// ================================================================
Commander command = Commander(Serial);
void onMotor(char* cmd) { command.motor(&motor, cmd); }

// ================================================================
// Setup
// ================================================================
void setup() {
  Serial.begin(115200);
  delay(500);
  SimpleFOCDebug::enable(&Serial);
  Serial.println("=== SimpleFOC ESP32 + MT6701 ABZ ===");

  // --- Encoder ---
  encoder.init();
  encoder.enableInterrupts(doA, doB, doZ);
  motor.linkSensor(&encoder);

  // --- Driver ---
  driver.voltage_power_supply = 12.0;
  driver.voltage_limit        = 4.0;   // Rs=2.55Ω — keep conservative
  driver.pwm_frequency        = 32000;
  driver.init();
  motor.linkDriver(&driver);

  // --- Fault pin ---
  pinMode(FAULT_PIN, INPUT_PULLUP);

  // --- Motor limits ---
  motor.voltage_sensor_align  = 4.0;
  motor.voltage_limit         = 4.0;
  motor.velocity_limit        = 50.0;

  // --- Closed-loop velocity ---
  motor.controller = MotionControlType::velocity;

  // --- Velocity PID (conservative starting values) ---
  motor.PID_velocity.P           = 0.1;
  motor.PID_velocity.I           = 2.0;
  motor.PID_velocity.D           = 0.0;
  motor.PID_velocity.output_ramp = 300.0;
  motor.PID_velocity.limit       = 3.5;

  // --- Velocity LPF ---
  motor.LPF_velocity.Tf = 0.02;

  motor.useMonitoring(Serial);
  motor.init();

  // Aligns sensor zero — motor will briefly twitch, watch for "PP check: OK!"
  motor.initFOC();

  command.add('M', onMotor, "motor");

  Serial.println("Ready — M5 = 5 rad/s | M0 = stop | M-5 = reverse");
  Serial.println("Tuning: MVP0.2  MVI3  MVD0  ML4 (voltage limit)");
}

// ================================================================
// Loop
// ================================================================
void loop() {
  // --- Fault check ---
  if (digitalRead(FAULT_PIN) == LOW) {
    Serial.println("DRV8313 FAULT — disabling motor.");
    motor.disable();
    while (true) {
      delay(1000);
      Serial.println("FAULT — reset ESP32 to restart.");
    }
  }

  motor.loopFOC();
  motor.move(motor.target);  // motor.target is set by Commander
  command.run();
}
