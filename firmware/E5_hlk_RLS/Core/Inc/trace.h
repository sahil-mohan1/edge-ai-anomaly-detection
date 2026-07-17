/*
 * trace.h
 *
 *  Created on: Sep 11, 2025
 *      Author: zero
 */

#ifndef APPLICATION_CORE_INC_TRACE_H_
#define APPLICATION_CORE_INC_TRACE_H_

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"
#include <stdint.h>
#include <string.h>
#include <stdbool.h>
#include <stdarg.h>

extern DMA_HandleTypeDef hdma_lpuart1_rx;
extern DMA_HandleTypeDef hdma_lpuart1_tx;
extern DMA_HandleTypeDef hdma_usart1_rx;
extern DMA_HandleTypeDef hdma_usart1_tx;
extern DMA_HandleTypeDef hdma_usart2_rx;
extern DMA_HandleTypeDef hdma_usart2_tx;
extern UART_HandleTypeDef hlpuart1;
extern UART_HandleTypeDef huart1;
extern UART_HandleTypeDef huart2;

typedef enum {
    OWNER_NONE,
    OWNER_VCOM,
    OWNER_APP_TRACE
} Transmission_Owner_t;

/* Transmission modes */
enum {
    TRACE_TX_MODE_POLLING = 0,
    TRACE_TX_MODE_INTERRUPT,
    TRACE_TX_MODE_DMA
};

/* Reception processing modes */
typedef enum {
    TRACE_RX_PROCESS_BYTE,    // Per-byte callback (interrupt or DMA)
    TRACE_RX_PROCESS_LINE,    // Accumulate until terminator, then line callback (interrupt or DMA)
    TRACE_RX_PROCESS_BUFFER,  // Chunk-based DMA mode (DMA normal)
    TRACE_RX_PROCESS_CUSTOM   // Custom callback (interrupt or DMA)
} Trace_RxProcessMode_t;

/* Internal reception hardware modes */
typedef enum {
    TRACE_HW_MODE_POLLING = 0,
    TRACE_HW_MODE_INTERRUPT,
    TRACE_HW_MODE_DMA
} Trace_HwMode_t;

/* Error codes for the TRACE API */
typedef enum {
    TRACE_SUCCESS = 0,
    TRACE_ERROR_UNSUPPORTED_INSTANCE = -1,
    TRACE_ERROR_CONFIG = -2,
    TRACE_ERROR_INIT = -3,
    TRACE_ERROR_DMA_INIT = -4,
    TRACE_ERROR_INVALID_DMA_MODE = -5,
    TRACE_ERROR_INVALID_PARAMETER = -6,
	TRACE_ERROR_TIMEOUT = -7,
    TRACE_ERROR_HARDWARE_FAILURE = -8,
    TRACE_ERROR_BUSY = -9,
    TRACE_ERROR_INVALID_MODE = -10,
	TRACE_ERROR_QUEUE_FULL = -11,
    TRACE_ERROR_NO_DATA = -12,
    TRACE_ERROR_NOT_READY = -13,
    TRACE_ERROR_TRANSMISSION_FAILED = -14,
    TRACE_ERROR_RX_BUFFER_OVERRUN = -15, // Software ring buffer overrun
    TRACE_ERROR_HW_OVERRUN = -16,        // Hardware overrun (ORE flag)
    TRACE_ERROR_SET_TX_FIFO = -17,
    TRACE_ERROR_SET_RX_FIFO = -18,
    TRACE_ERROR_FIFO_Config = -19

} Trace_Error_t;

/* DMA configuration modes */
typedef enum {
    TRACE_DMA_MODE_NONE = 0,
    TRACE_DMA_MODE_RX,
    TRACE_DMA_MODE_TX,
    TRACE_DMA_MODE_RX_TX,
} Trace_DMA_Mode_t;

/* Advanced UART initialization structure */
typedef struct {
    USART_TypeDef *Instance;
    uint32_t BaudRate;
    uint32_t WordLength;
    uint32_t StopBits;
    uint32_t Parity;
    uint32_t Mode;
    uint32_t HwFlowCtl;
    uint32_t OverSampling;
    uint32_t OneBitSampling;
    uint32_t AdvFeatureInit;
    uint32_t ClockPrescaler;
    uint8_t DMA_Mode;
} USART_AdvInit_t;

/* Callback signatures */
typedef void (*Trace_RxByteCallback_t)(uint8_t byte);
typedef void (*Trace_RxLineCallback_t)(const uint8_t* data, uint16_t length);
typedef void (*Trace_RxBufferCallback_t)(uint8_t* buffer, uint16_t len);
typedef void (*Trace_RxCustomCallback_t)(UART_HandleTypeDef *huart, uint8_t* buffer, uint16_t len);
typedef void (*Trace_ErrorCallback_t)(UART_HandleTypeDef *huart, Trace_Error_t error);

/**
  * @brief  RX configuration structure for the TRACE driver.
  */
typedef struct {
    uint8_t *buffer;
    uint16_t buffer_size;
    uint8_t terminator;
    Trace_RxProcessMode_t process_mode;
    Trace_HwMode_t custom_hw_mode;
    union {
        Trace_RxByteCallback_t  byte_cb;
        Trace_RxLineCallback_t  line_cb;
        Trace_RxBufferCallback_t buffer_cb;
        Trace_RxCustomCallback_t custom_cb;
    };
    bool enable_wakeup;
    Trace_ErrorCallback_t error_cb; /**< Optional: Called on hardware or software errors. */
} Trace_RxConfig_t;

/** @name Initialization and Deinitialization
  * @{
  */
Trace_Error_t trace_Init(USART_TypeDef *uart_instance, uint32_t baudRate);
Trace_Error_t trace_InitAdv(USART_AdvInit_t *advConfig);
Trace_Error_t trace_Resume(UART_HandleTypeDef *huart);
Trace_Error_t trace_Deinit(UART_HandleTypeDef *huart);
/**
  * @}
  */

/** @name Transmission
  * @{
  */
Trace_Error_t trace_Printf(UART_HandleTypeDef *huart, const char *format, ...);
Trace_Error_t trace_WriteRaw(UART_HandleTypeDef *huart, const uint8_t *data, uint16_t length, Transmission_Owner_t owner);
Trace_Error_t trace_WriteRawChunked(UART_HandleTypeDef *huart, const uint8_t *data, uint32_t length, Transmission_Owner_t owner, uint32_t timeout_ms);
Trace_Error_t trace_SetTxMode(UART_HandleTypeDef *huart, uint8_t mode);
bool is_uart_transmission_ongoing(UART_HandleTypeDef *huart);
Trace_Error_t trace_FlushTx(UART_HandleTypeDef *huart, uint32_t timeout);
/**
  * @}
  */

/** @name Reception
  * @{
  */
Trace_Error_t trace_StartRx(UART_HandleTypeDef *huart, const Trace_RxConfig_t *config);
Trace_Error_t trace_StopRx(UART_HandleTypeDef *huart);
uint16_t trace_Available(UART_HandleTypeDef *huart);
void trace_FlushRx(UART_HandleTypeDef *huart);
uint16_t trace_RxRead(UART_HandleTypeDef *huart, uint8_t *dest, uint16_t length);
Trace_Error_t trace_PollData(UART_HandleTypeDef *huart);
/**
  * @}
  */

/* ============================== */
/* CALLBACKS FOR HAL DRIVER      */
/* ============================== */
/** @name HAL Callback Handlers
  * @brief These functions must be called from the corresponding HAL callbacks
  * in stm32l0xx_it.c or other relevant files.
  * @{
  */
void trace_TxCpltCallback(UART_HandleTypeDef *huart);
void trace_RxCpltCallback(UART_HandleTypeDef *huart);
void trace_RxEventCallback(UART_HandleTypeDef *huart, uint16_t size);
void trace_ErrorCallback(UART_HandleTypeDef *huart);
/**
  * @}
  */

typedef void (*Trace_TxCpltHook_t)(UART_HandleTypeDef *huart, Transmission_Owner_t owner);
void trace_RegisterTxCpltHook(Trace_TxCpltHook_t hook);

#ifdef __cplusplus
}
#endif

#endif /* APPLICATION_CORE_INC_TRACE_H_ */
