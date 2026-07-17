

/*
 * hlk_ld2413.h
 *
 *  Created on: Feb 24, 2026
 *      Author: icfoss
 */

#ifndef APPLICATION_USER_HLK_LD2413_HLK_LD2413_H_
#define APPLICATION_USER_HLK_LD2413_HLK_LD2413_H_

#include <stdint.h>
#define BATT_POWER    				1

#define R1 	100		/*100 K resistor R1 in voltage divider*/
#define R2 	100		/*100 K resistor R2 in voltage divider*/

#define BATT_ENABLE_PORT		GPIOA
#define BATT_ENABLE_PIN			GPIO_PIN_0
#define BATTERY_CHANNEL			ADC_CHANNEL_3

typedef struct {
    float x;      // Estimated distance (mm)
    float v;      // Estimated velocity (mm/cycle)
    float P[2][2]; // Error covariance matrix
    float Q[2][2]; // Process noise covariance
    float R;       // Measurement noise covariance
} Kalman2D_t;

#define CC_MAX_READ_TIME                    30000
#define TIMER_RELOAD_VALUE                  0xFFFFFFFF
#define MAX_LIMIT                           6000
#define JUMP_THRESHOLD                      500
#define SAMPLING_DATA                       30
#define STABILITY_THRESHOLD                 80
#define UNSTABLE_THRESHOLD                  15

// Initialize with reasonable defaults
// R: increase if sensor is "jumpy". Q: increase if the water level changes rapidly.


void radar_uarttimer_init(void);
void Radar_Byte_Callback(uint8_t byte);
void Recieved_Byte_Filtering(void);
void Radar_Byte_Callback(uint8_t byte);
void radar_uart_init(void);
void batteryReadError(void *argument);
void Radar_Process_Pending_Data(void);
void Kalman_Process(void);
uint32_t kalman_with_transmitted_distance(void);

uint16_t readBatteryLevel(void);
void enable(uint8_t pin);
void disable(uint8_t pin);

#endif /* APPLICATION_USER_HLK_LD2413_HLK_LD2413_H_ */
