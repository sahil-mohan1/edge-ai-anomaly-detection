
/**
  ******************************************************************************
  * @file    app_x-cube-ai.c
  * @author  X-CUBE-AI C code generator
  * @brief   AI program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */

  /**
    * Description
    * v1.0: Minimum template to show how to use the Embedded Client API ST-AI 
    *
        */

#ifdef __cplusplus
 extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/

#if defined ( __ICCARM__ )
#define AI_SRAM   _Pragma("location=\"AI_SRAM\"")
#elif defined ( __CC_ARM ) || ( __GNUC__ )
#define AI_SRAM   __attribute__((section(".AI_SRAM")))
#endif

/* System headers */
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <inttypes.h>
#include <string.h>
#include "app_x-cube-ai.h"
#include "stai.h"



/* USER CODE BEGIN includes */
#include "main.h"
#include <time.h>
#include <math.h>
#include <stdio.h>

#define BASE_THRESH 0.5f
#define MAX_THRESH 1.5f

extern UART_HandleTypeDef huart1;
/* USER CODE END includes */

/* IO buffers ----------------------------------------------------------------*/


/* Input defs ----------------------------------------------------------------*/
#include "aiTestUtility.h"
/**
STAI_ALIGNED(32) static uint8_t data_in_1[STAI_NETWORK_IN_1_SIZE_BYTES];

// Array to store the data of the input tensor
stai_ptr data_ins[] = {
  data_in_1
}; 
*/

/* Output defs ----------------------------------------------------------------*/

/**
STAI_ALIGNED(32) 
static uint8_t data_out_1[STAI_NETWORK_OUT_1_SIZE_BYTES];

// c-array to store the data of the output tensor
stai_ptr data_outs[] = {
  data_out_1
}; 
*/




/* Global byte buffer to save instantiated C-model network context */
STAI_NETWORK_CONTEXT_DECLARE(network_context, STAI_NETWORK_CONTEXT_SIZE)

/* Activations buffers -------------------------------------------------------*/
STAI_ALIGNED(32) 
AI_SRAM 
static uint8_t SRAM[STAI_NETWORK_ACTIVATION_1_SIZE_BYTES];


/* Global c-array to handle the activations buffer */
stai_ptr data_activations[] = { SRAM };

STAI_ALIGNED(32) static uint8_t states_1[4];
stai_ptr data_states[] = {
    states_1
};




/* Entry points --------------------------------------------------------------*/

/* Array of pointer to manage the model's input/output tensors */
static stai_size in_length, out_length;
static stai_ptr stai_input[STAI_NETWORK_IN_NUM];
static stai_ptr stai_output[STAI_NETWORK_OUT_NUM];


/* 
 * Bootstrap
 */
int aiInit(void) {
  stai_return_code ret_code;
  
  /* 1: Initialize runtime library */
  ret_code = stai_runtime_init();
  
  /* 2: Initialize network model context */
  ret_code = user_stai_network_init(network_context);
  /* 3: Set network activations buffers */
  ret_code = stai_network_set_activations(network_context, data_activations, STAI_NETWORK_ACTIVATIONS_NUM);
  

  /* 4: Update the AI input/output buffers */
  /** Set network input/output buffers 
    * If the model uses no-inputs-allocation or no-outputs-allocation, the addresses of the input/output buffers
    * must be set before running the inference.
    * See https://stedgeai-dc.com/assets/embedded-docs/embedded_client_stai_api.html#ref_api_set_io
    * for more details
    */

  // current model uses allocate-inputs, use this part to overwrite the addresses of the input buffers
  /**
  ret_code = stai_network_set_inputs(network_context, data_ins, STAI_NETWORK_IN_NUM);
   */
  // current model uses allocate-outputs, use this part to overwrite the addresses of the output buffers
  /** 
  ret_code = stai_network_set_outputs(network_context, data_outs, STAI_NETWORK_OUT_NUM);
   */

  ret_code = stai_network_get_inputs(network_context, stai_input, &in_length);
  
  ret_code = stai_network_get_outputs(network_context, stai_output, &out_length);
  
  (void)ret_code;
  return 0;
}

int aiDeinit(void) {
  stai_return_code ret_code;

  /* 1: Deinitialize network model context */
  ret_code = stai_network_deinit(network_context);
  
  /* 2: Deinitialize runtime library */
  ret_code = stai_runtime_deinit();

  (void)ret_code;
  return 0;
}

/* 
 * Run inference
 */
stai_return_code aiRun() {
  stai_return_code ret_code;

  /** Profiling code to calculate the inference time of the model. You can remove it if not needed */
  static uint32_t inference_nb = 0;
  static uint32_t total_cycles = 0;
  uint32_t start_tick, end_tick, end_dwt = 0;
  struct dwtTime t;
  cyclesCounterInit();

  LC_PRINT("---- Inference number %" PRIu32 " ----\r\n", inference_nb);
  LC_PRINT("Results for network \"%s\"\r\nRunning...\r\n", STAI_NETWORK_MODEL_NAME);
  cyclesCounterStart();
  start_tick = HAL_GetTick();


  /* Perform the inference */
  ret_code = stai_network_run(network_context, STAI_MODE_SYNC);
  if (ret_code != STAI_SUCCESS) {
      ret_code = stai_network_get_error(network_context);
      LC_PRINT("Inference failed with error code %s\r\n", stai_get_return_code_name(ret_code));
  };
  /** End of inference */
  
  /** Continue profiling */
  end_dwt = cyclesCounterEnd();
  total_cycles += end_dwt;
  end_tick = HAL_GetTick();
  dwtCyclesToTime(end_dwt, &t);

  LC_PRINT(" duration DWT    : %d.%03d ms\r\n", t.s * 1000 + t.ms, t.us);
  LC_PRINT(" duration SysTick: %" PRIu32" ms\r\n", end_tick - start_tick);
  LC_PRINT(" CPU cycles      : %" PRIu32 "\r\n", end_dwt);
  LC_PRINT(" CPU cycles (avg): %" PRIu32 "\r\n", total_cycles / ++inference_nb);
  // HAL_Delay(5000); Removed delay from aiRun so main_loop controls printing pace

  return ret_code;
}


int acquire_and_process_data()
{
  /* USER CODE BEGIN acquire_and_process_data */
  return 0;
  /* USER CODE END acquire_and_process_data */
}

int post_process()
{
  /* USER CODE BEGIN post_process */
  return 0;
  /* USER CODE END post_process */
}



/* 
 * Example of main loop function
 */
void read_line(char* out_buf, int max_len) {
    int idx = 0;
    while(idx < max_len - 1) {
        uint8_t c;
        if (HAL_UART_Receive(&huart1, &c, 1, HAL_MAX_DELAY) == HAL_OK) {
            if (c == '\n' || c == '\r') {
                if (idx > 0) {
                    break;
                }
                else continue;
            }
            // Handle backspace (ASCII 8 or 127)
            if (c == '\b' || c == 0x7F) {
                if (idx > 0) idx--;
                continue;
            }
            
            // Only accept printable ASCII characters to prevent null bytes or garbage
            if (c >= 32 && c <= 126) {
                out_buf[idx++] = (char)c;
            }
        } else {
            // Clear hardware overrun and error flags
            __HAL_UART_CLEAR_OREFLAG(&huart1);
            __HAL_UART_CLEAR_FLAG(&huart1, UART_CLEAR_NEF | UART_CLEAR_PEF | UART_CLEAR_FEF);
            huart1.ErrorCode = HAL_UART_ERROR_NONE;
            huart1.RxState = HAL_UART_STATE_READY;
            __HAL_UNLOCK(&huart1);
        }
    }
    out_buf[idx] = '\0';
}

void main_loop() {
  /* USER CODE BEGIN main_loop */
  char buf[64];
  char timestamp[64];
  float water_level;
  int error_code;

  static float lag_buffer[8] = {0};
  static int lag_head = 0;
  static int prev_errorcode = 0;
  static float dyn_thresh = BASE_THRESH;
  static int warmup_count = 0;

  LC_PRINT("Enter starting timestamp (dd-mm-yyyy HH:MM):\r\n");
  read_line(timestamp, sizeof(timestamp));
  LC_PRINT("Starting timestamp set to: %s\r\n", timestamp);

  struct tm t_info = {0};
  int day, month, year, hour, min;
  if (sscanf(timestamp, "%d-%d-%d_%d:%d", &day, &month, &year, &hour, &min) == 5 || 
      sscanf(timestamp, "%d-%d-%d %d:%d", &day, &month, &year, &hour, &min) == 5) {
      t_info.tm_mday = day;
      t_info.tm_mon = month - 1;
      t_info.tm_year = year - 1900;
      t_info.tm_hour = hour;
      t_info.tm_min = min;
  } else {
      // Safe fallback to prevent mktime from hanging on invalid date
      t_info.tm_mday = 1;
      t_info.tm_mon = 0;
      t_info.tm_year = 2026 - 1900;
      t_info.tm_hour = 0;
      t_info.tm_min = 0;
      LC_PRINT("Invalid format, defaulting to 01-01-2026 00:00\r\n");
  }
  time_t current_time = mktime(&t_info);

  int row_idx = 0;

  while (1) {
    if (warmup_count < 8) {
        LC_PRINT("Warmup [%d/8] - Enter raw water level and error code:\r\n", warmup_count + 1);
    } else {
        LC_PRINT("Enter raw water level and error code:\r\n");
    }
    read_line(buf, sizeof(buf));
    
    char* endptr;
    water_level = strtof(buf, &endptr);
    if (endptr == buf) {
        LC_PRINT("Invalid input format. Expected float.\r\n");
        continue;
    }
    
    // Skip spaces, tabs, and commas between the numbers
    while (*endptr == ' ' || *endptr == '\t' || *endptr == ',') {
        endptr++;
    }
    
    char* endptr2;
    error_code = (int)strtol(endptr, &endptr2, 10);
    if (endptr2 == endptr) {
        LC_PRINT("Invalid input format. Expected integer error code.\r\n");
        continue;
    }
    
    // Check for trailing garbage
    while (*endptr2 == ' ' || *endptr2 == '\t' || *endptr2 == '\r' || *endptr2 == '\n') {
        endptr2++;
    }
    if (*endptr2 != '\0') {
        LC_PRINT("Invalid input format. Unexpected characters found: %s\r\n", endptr2);
        continue;
    }
    
    row_idx++;

    // Warmup logic
    if (warmup_count < 8) {
        lag_buffer[lag_head] = water_level;
        lag_head = (lag_head + 1) % 8;
        prev_errorcode = error_code;
        warmup_count++;
        current_time += 15 * 60; // Increment by 15 mins
        continue;
    }

    // Build input features array
    float* input_features = (float*)stai_input[0];
    
    input_features[0] = (float)error_code / 5.0f;
    input_features[1] = water_level / 4.5f;

    // Load lags (reverse order as per Python)
    for(int i = 0; i < 8; i++) {
        int idx = (lag_head - 1 - i + 8) % 8;
        input_features[2 + i] = lag_buffer[idx];
    }

    // Time features
    struct tm* tm_info = localtime(&current_time);
    
    int mins_day = tm_info->tm_hour * 60 + tm_info->tm_min;
    float day_frac = (mins_day % 1440) / 1440.0f;
    float half_day_frac = (mins_day % 720) / 720.0f;
    float quarter_day_frac = (mins_day % 360) / 360.0f;
    float eighth_day_frac = (mins_day % 180) / 180.0f;
    
    int wday = (tm_info->tm_wday + 6) % 7; // Monday = 0
    int mins_week = wday * 1440 + mins_day;
    float week_frac = mins_week / 10080.0f;
    
    float PI = 3.141592653589793f;
    float* time_f = &input_features[10];
    
    time_f[0] = sin(2 * PI * week_frac);
    time_f[1] = cos(2 * PI * week_frac);
    time_f[2] = sin(2 * PI * day_frac);
    time_f[3] = cos(2 * PI * day_frac);
    time_f[4] = sin(2 * PI * half_day_frac);
    time_f[5] = cos(2 * PI * half_day_frac);
    time_f[6] = sin(2 * PI * quarter_day_frac);
    time_f[7] = cos(2 * PI * quarter_day_frac);
    time_f[8] = sin(2 * PI * eighth_day_frac);
    time_f[9] = cos(2 * PI * eighth_day_frac);
    time_f[10] = week_frac;
    time_f[11] = (float)wday / 6.0f;

    input_features[22] = (float)prev_errorcode / 5.0f;

    /* 2 - Call inference engine */
    aiRun();

    /* 3 - Post-process the predictions */
    float anomaly_prob = ((float*)stai_output[0])[0];
    float predicted_wl = ((float*)stai_output[0])[1];

    bool is_anomaly = false;
    float residual = fabs(water_level - predicted_wl);
    
    if (error_code == 0) {
        is_anomaly = false;
        dyn_thresh = BASE_THRESH;
    } else if (error_code == 5 || water_level < 0.05f || water_level >= 4.45f || residual > dyn_thresh) {
        is_anomaly = true;
        float new_thresh = dyn_thresh + 0.1f;
        dyn_thresh = new_thresh < MAX_THRESH ? new_thresh : MAX_THRESH;
    } else {
        dyn_thresh = BASE_THRESH;
    }
    
    float corrected_wl = is_anomaly ? predicted_wl : water_level;
    if (corrected_wl < 0.0f) corrected_wl = 0.0f;
    if (corrected_wl > 4.5f) corrected_wl = 4.5f;

    // Autoregressive lag update
    lag_buffer[lag_head] = corrected_wl;
    lag_head = (lag_head + 1) % 8;
    prev_errorcode = error_code;

    LC_PRINT("Row %d: WL_Raw: %.3f, Pred_WL: %.3f, Anomaly: %d (Prob: %.3f)\r\n", 
             row_idx, water_level, predicted_wl, is_anomaly, anomaly_prob);
             
    current_time += 15 * 60; // Increment by 15 mins for next loop
  }
  
  /* USER CODE END main_loop */
}


/* Entry points --------------------------------------------------------------*/


void STM32CubeAI_Studio_AI_Init(void)
{
    aiInit();  
    /* USER CODE BEGIN init */
    
    
    /* USER CODE END init */
}

void STM32CubeAI_Studio_AI_Process(void)
{
    main_loop();
} 

void STM32CubeAI_Studio_AI_Deinit(void)
{
    aiDeinit();
} 


#ifdef __cplusplus
}
#endif
