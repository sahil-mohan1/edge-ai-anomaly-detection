/*
 * hlk_ld2413.c
 *
 *  Created on: Feb 24, 2026
 *      Author: icfoss
 */
#include "stm32_seq.h"
#include "stm32_timer.h"
#include <string.h>
#include "trace.h"
#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#include <hlk_ld2413.h>
#include "sys_app.h"
#include "adc_if.h"


volatile uint8_t error_code=0;
uint32_t global_radar_distance[SAMPLING_DATA];
uint32_t current_distance = 0;
uint8_t qlobal_Data_Count=0;
static volatile bool rec_Flag = false;

static volatile bool battery_timer_flag = false;
static volatile bool cc_data_ready_flag = false;

#define FIFO_SIZE 14  //
//------------------------------
volatile uint8_t kalman_error_code=0;

uint32_t global_kalman_distance[SAMPLING_DATA];

uint32_t kalman_distance = 0;

uint8_t kalman_count=0;



Kalman2D_t radar_kf = {
    .x = 0.0f,
    .v = 0.0f,
    .P = {{1.0f, 0.0f}, {0.0f, 1.0f}},
    .Q = {{0.001f, 0.0f}, {0.0f, 0.001f}},
    .R = 1.0f
};

Kalman2D_t radar_kf_predict = {
    .x = 0.0f,
    .v = 0.0f,
    .P = {{1.0f, 0.0f}, {0.0f, 1.0f}},
    .Q = {{0.001f, 0.0f}, {0.0f, 0.001f}},
    .R = 0.05f
};
//------------------------------


// Ring Buffer Variables
volatile uint8_t radar_fifo[FIFO_SIZE];
volatile uint16_t fifo_head = 0;
volatile uint16_t fifo_tail = 0;

// Frame Constants
const uint8_t RADAR_HEADER[4] = {0xF4, 0xF3, 0xF2, 0xF1};
const uint8_t RADAR_FOOTER[4] = {0xF8, 0xF7, 0xF6, 0xF5};
const uint8_t RADAR_DATA_LEN[2] = {0x40, 0x00};

static uint8_t frame_buf[14];

UTIL_TIMER_Object_t battery_voltage_timer = { 0 };


Trace_Error_t status = TRACE_SUCCESS;
uint8_t trace_rx_buffer[28];
Trace_RxConfig_t radar_rx_config;

#define CC_MAX_READ_TIME                    30000
#define TIMER_RELOAD_VALUE                  0xFFFFFFFF

void Kalman2D_Correct(Kalman2D_t *kf, float measurement);
void Kalman2D_Predict(Kalman2D_t *kf);

void Radar_Process_Pending_Data(void)
{
    uint8_t stability_count = 0; // Counts consecutive valid readings
    current_distance = 0;
    uint8_t unstable_count = 0; // Counts consecutive unstable readings
    uint8_t i = 1;
  if (qlobal_Data_Count>0)
  {
  while (i < qlobal_Data_Count)
  {

    if (fabs(global_radar_distance[i] - global_radar_distance[i-1]) < STABILITY_THRESHOLD)
    {
      if (global_radar_distance[i] > 0)
      {
        current_distance += global_radar_distance[i];
  	    global_kalman_distance[i] = global_radar_distance[i];
  	    kalman_count++;
        stability_count++;
        error_code = 0; // Error code for stable reading
      }
    }
    else
    {
      unstable_count++;
      if (unstable_count >= 5)
      { // If we have 5 consecutive unstable readings, we can consider the data unreliable
         error_code = 5; // Error code for unstable reading
      }
    }
    i++;
  }
  }
  if (stability_count > 0){
  current_distance /= stability_count;
  stability_count = 0;
  }
  else{
	 if (error_code != 2 && error_code != 1 && error_code != 4 && error_code != 3) error_code = 5;
  }
  qlobal_Data_Count=0;
}



void radar_uart_init(void){

    cc_data_ready_flag = false;
    battery_timer_flag = false;

UTIL_TIMER_Start(&battery_voltage_timer);
status = trace_Init(USART2, 115200);
  if ( status != TRACE_SUCCESS) {
      Error_Handler(); // Initialization failed
  }


  radar_rx_config.buffer = trace_rx_buffer;
  radar_rx_config.buffer_size = sizeof(trace_rx_buffer);
  radar_rx_config.terminator = 0;
  radar_rx_config.process_mode = TRACE_RX_PROCESS_BYTE;
  radar_rx_config.byte_cb = Radar_Byte_Callback;
  status = trace_StartRx(&huart2, &radar_rx_config);
  error_code=2;


  if ( status != TRACE_SUCCESS) {
      Error_Handler(); // Starting RX failed
  }
  while (!cc_data_ready_flag) {
while (qlobal_Data_Count < SAMPLING_DATA)
{
	  Recieved_Byte_Filtering();
      if (battery_timer_flag) {
          trace_StopRx(&huart2);
          trace_Deinit(&huart2);

          break;
      }
}

      if (battery_timer_flag) {
    		 if (error_code != 1 && error_code != 4 && error_code != 3) error_code = 2;
          battery_timer_flag = false;
          break;
      }
  }
  if (!battery_timer_flag) {
      UTIL_TIMER_Stop(&battery_voltage_timer);
  }

}

void radar_uarttimer_init(void){
	  UTIL_TIMER_Create(&battery_voltage_timer, TIMER_RELOAD_VALUE, UTIL_TIMER_ONESHOT, batteryReadError, NULL);
	  UTIL_TIMER_SetPeriod(&battery_voltage_timer, CC_MAX_READ_TIME);

}

void batteryReadError(void *argument) {
    UTIL_TIMER_Stop(&battery_voltage_timer);
    battery_timer_flag = true;
}

void Radar_Byte_Callback(uint8_t byte)
{

    // Store byte at current head position
    radar_fifo[fifo_head] = byte;

    uint16_t next_head = (fifo_head + 1) % FIFO_SIZE;

    if (next_head != fifo_tail) {
        fifo_head = next_head;

    }
}

void Recieved_Byte_Filtering(void)
{
static uint8_t idx = 0;
if (qlobal_Data_Count < 30){

    trace_StopRx(&huart2);

    while (fifo_tail != fifo_head)
    {
        uint8_t byte;
        byte = radar_fifo[fifo_tail];
        fifo_tail = (fifo_tail + 1) % FIFO_SIZE;

        // --- Header Detection ---
        if (idx < 4)
        {
            if (byte == RADAR_HEADER[idx]) {
                frame_buf[idx++] = byte;
            } else {
                idx = (byte == RADAR_HEADER[0]) ? 1 : 0;
                if (idx == 1) frame_buf[0] = byte;
            }
        }
        // --- Payload & Footer ---
        else
        {
            frame_buf[idx++] = byte;

            if (idx >= 14)
            {
                // Validate data len & Footer
                if (frame_buf[4] == 0x04 && frame_buf[5] == 0x00 && frame_buf[10] == 0xF8 && frame_buf[11] == 0xF7 &&
                    frame_buf[12] == 0xF6 && frame_buf[13] == 0xF5 )
                {
                    float temp_distance = 0;
                    memcpy(&temp_distance, &frame_buf[6], 4);

                    // 1. Basic Range Filter
                    if (temp_distance <= MAX_LIMIT  && temp_distance > 0 )
                    {
                    	if (current_distance>0)
                    	{
                              if (fabs(current_distance - temp_distance) < JUMP_THRESHOLD)
                               {

                                 global_radar_distance[qlobal_Data_Count] = (uint32_t)temp_distance;
                                   cc_data_ready_flag = true;
                                    qlobal_Data_Count++;

                                } else {
                                      error_code = 3; // Error code for large jump
                                      APP_LOG(TS_ON, VLEVEL_L, "large jump detected , error_code : %d \r\n", error_code);
//                                    sample_flush = true ;
                                 }
                    	 } else {
                             global_radar_distance[qlobal_Data_Count] = (uint32_t)temp_distance;
                             cc_data_ready_flag = true;
                             qlobal_Data_Count++;
                    	 }
                    }else if(temp_distance >= MAX_LIMIT)
                    {
                        error_code = 4; // Error code for exceed limit
                        APP_LOG(TS_ON, VLEVEL_L, "exceed limit detected , error_code : %d \r\n", error_code);


                    }else
                    {
                        error_code = 1; // Error code for 0mm distance
                        APP_LOG(TS_ON, VLEVEL_L, "0mm distance detected , error_code : %d \r\n", error_code);

                    }
                }
             idx = 0; // Reset for next packet  (correction)

            }
        }


    }

    status = trace_StartRx(&huart2, &radar_rx_config);

    if ( status != TRACE_SUCCESS)
    {
      Error_Handler(); // Starting RX failed
    }


}

}
//----------------------------------kalman old-------------------------------

//void Kalman2D_Update(Kalman2D_t *kf, float measurement) {
//    // 1. Predict (A matrix: [1 1; 0 1] assuming dt = 1 cycle)
//    float x_p = kf->x + kf->v;
//    float v_p = kf->v;
//
//    // P_p = A*P*A' + Q
//    float P_p[2][2];
//    P_p[0][0] = kf->P[0][0] + kf->P[0][1] + kf->P[1][0] + kf->P[1][1] + kf->Q[0][0];
//    P_p[0][1] = kf->P[0][1] + kf->P[1][1] + kf->Q[0][1];
//    P_p[1][0] = kf->P[1][0] + kf->P[1][1] + kf->Q[1][0];
//    P_p[1][1] = kf->P[1][1] + kf->Q[1][1];
//
//    // 2. Update (H matrix: [1 0] because we only measure distance)
//    // Innovation (Residual)
//    float y = measurement - x_p;
//
//    // Innovation Covariance S = H*P_p*H' + R
//    float S = P_p[0][0] + kf->R;
//
//    // Kalman Gain K = P_p*H' * inv(S)
//    float K[2];
//    K[0] = P_p[0][0] / S;
//    K[1] = P_p[1][0] / S;
//
//    // New Estimate
//    kf->x = x_p + K[0] * y;
//    kf->v = v_p + K[1] * y;
//
//    // New Covariance P = (I - K*H) * P_p
//    float P_new[2][2];
//    P_new[0][0] = (1.0f - K[0]) * P_p[0][0];
//    P_new[0][1] = (1.0f - K[0]) * P_p[0][1];
//    P_new[1][0] = -K[1] * P_p[0][0] + P_p[1][0];
//    P_new[1][1] = -K[1] * P_p[0][1] + P_p[1][1];
//
//    kf->P[0][0] = P_new[0][0];
//    kf->P[0][1] = P_new[0][1];
//    kf->P[1][0] = P_new[1][0];
//    kf->P[1][1] = P_new[1][1];
//}



//void Kalman_Process(void)
//{
//	kalman_distance = 0;
////    if (qlobal_Data_Count == 0) {
////        // Only set timeout error if we haven't received data in this cycle
////        if (kalman_error_code != 3 && kalman_error_code != 4) kalman_error_code = 2;
////        return;
////    }
//
//
//    for (uint8_t i = 0; i < kalman_count; i++) {
////    for (uint8_t i = 0; i < qlobal_Data_Count; i++) {
//
////    	        if (fabs(global_radar_distance[i] - global_radar_distance[i-1]) < STABILITY_THRESHOLD)
////    	        {
//    	          float val = (float)global_kalman_distance[i];
////    	          float val = (float)global_radar_distance[i];
//
//    	          // Seed the filter if it's the very first valid reading
//    	          if (radar_kf.x == 0.0f && val > 0) {
//    	              radar_kf.x = val;
//    	          }
//    	          else if (val > 0) {
//    	            // Apply the 2D Kalman Filter
//    	              Kalman2D_Update(&radar_kf, val);
////    	          }
//    	        }
//    }
//
//    // Set the final distance from the filter state
//    kalman_distance = (uint32_t)radar_kf.x;
//    // Clean up for next LoRa cycle
//    kalman_error_code=0;
////    qlobal_Data_Count = 0;
//    kalman_count=0;
//
//}

//-----------------------------------------kalman old---------------------------------------------

//void Kalman_Process(void)
//{
//    // CASE A: No new UART data (Coast based on trend)
//    if (kalman_count == 0) {
//        Kalman2D_Predict(&radar_kf_predict);
//        kalman_distance = (uint32_t)radar_kf_predict.x;
//        kalman_error_code = 2; // Timeout/No data warning
//        return ;
//    }
//
//    // CASE B: Data available (Predict then Correct)
//    for (uint8_t i = 0; i < kalman_count; i++) {
//        float val = (float)global_kalman_distance[i];
//
//        if (val > 0) {
//            if (radar_kf.x == 0.0f) {
//                radar_kf.x = val; // Initialize if first time
//            } else {
//                Kalman2D_Predict(&radar_kf);   // Move based on trend
//                Kalman2D_Correct(&radar_kf, val); // Adjust based on sensor
//            }
//        }
//
//
//    }
//
//    float val_prediction = (float)current_distance;
//
//    if (val_prediction > 0) {
//        if (radar_kf_predict.x == 0.0f) {
//        	radar_kf_predict.x = val_prediction; // Initialize if first time
//        } else {
//            Kalman2D_Predict(&radar_kf_predict);   // Move based on trend
//            Kalman2D_Correct(&radar_kf_predict, val_prediction); // Adjust based on sensor
//        }
//    }
//	radar_kf_predict.x = radar_kf.x;
//    kalman_distance = (uint32_t)radar_kf.x;
//    kalman_error_code = 0;
//    kalman_count = 0;
//}

/**
  * @brief Predicts the next state based on velocity (Trend Following)
  */
//void Kalman2D_Predict(Kalman2D_t *kf) {
//    // x = x + v (Prediction)
//    kf->x = kf->x + kf->v;
//
//    // Update Error Covariance: P = A*P*A' + Q
//    float P_p[2][2];
//    P_p[0][0] = kf->P[0][0] + kf->P[0][1] + kf->P[1][0] + kf->P[1][1] + kf->Q[0][0];
//    P_p[0][1] = kf->P[0][1] + kf->P[1][1] + kf->Q[0][1];
//    P_p[1][0] = kf->P[1][0] + kf->P[1][1] + kf->Q[1][0];
//    P_p[1][1] = kf->P[1][1] + kf->Q[1][1];
//
//    kf->P[0][0] = P_p[0][0];
//    kf->P[0][1] = P_p[0][1];
//    kf->P[1][0] = P_p[1][0];
//    kf->P[1][1] = P_p[1][1];
//}

/**
  * @brief Corrects the prediction using a real sensor measurement
  */
//void Kalman2D_Correct(Kalman2D_t *kf, float measurement) {
//    // Innovation (Residual)
//    float y = measurement - kf->x;
//
//    // Innovation Covariance S = H*P*H' + R
//    float S = kf->P[0][0] + kf->R;
//
//    // Kalman Gain K = P*H' * inv(S)
//    float K[2];
//    K[0] = kf->P[0][0] / S;
//    K[1] = kf->P[1][0] / S;
//
//    // New Estimate (Update state with sensor data)
//    kf->x = kf->x + K[0] * y;
//    kf->v = kf->v + K[1] * y;
//
//    // New Covariance P = (I - K*H) * P
//    float P_new[2][2];
//    P_new[0][0] = (1.0f - K[0]) * kf->P[0][0];
//    P_new[0][1] = (1.0f - K[0]) * kf->P[0][1];
//    P_new[1][0] = -K[1] * kf->P[0][0] + kf->P[1][0];
//    P_new[1][1] = -K[1] * kf->P[0][1] + kf->P[1][1];
//
//    kf->P[0][0] = P_new[0][0];
//    kf->P[0][1] = P_new[0][1];
//    kf->P[1][0] = P_new[1][0];
//    kf->P[1][1] = P_new[1][1];
//}


uint16_t readBatteryLevel(void) {
	int analogValue = 0; /*   adc reading for battery is stored in the variable  */
	float batteryVoltage = 0;
	uint16_t batteryLevel = 0; /*    battery voltage   */

	/* enable battery voltage reading */
	enable(BATT_POWER);
	HAL_Delay(10000);

	/* Read battery voltage reading */
	analogValue = ADC_ReadChannels(BATTERY_CHANNEL);

	/* disable battery voltage reading */
	disable(BATT_POWER);

	/*battery voltage = ADC value*Vref*2/4096   --12 bit ADC with voltage divider factor of 2 */
	batteryVoltage = (float)(analogValue * 3.3 * ((R1 + R2) / R2)) / 4096;

	/*multiplication factor of 100 to convert to int from float*/
	batteryLevel = (uint16_t) (batteryVoltage * 100);

	return batteryLevel;
}





void enable(uint8_t pin) {

	switch (pin) {
		case 1:
		    APP_LOG(TS_ON, VLEVEL_L, "battery reading\r\n");

			HAL_GPIO_WritePin(BATT_ENABLE_PORT, BATT_ENABLE_PIN, GPIO_PIN_RESET); //for battery
			break;
}
}

void disable(uint8_t pin) {

	switch (pin) {
		case 1:
			HAL_GPIO_WritePin(BATT_ENABLE_PORT, BATT_ENABLE_PIN, GPIO_PIN_SET); //for battery
			break;

}
}

