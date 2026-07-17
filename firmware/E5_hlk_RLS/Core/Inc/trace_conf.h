/*
 * trace_conf.h
 *
 *  Created on: Sep 11, 2025
 *      Author: zero
 */

#ifndef APPLICATION_USER_CORE_INC_TRACE_CONF_H_
#define APPLICATION_USER_CORE_INC_TRACE_CONF_H_

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"

/* --- MASTER SWITCH & CONFIGURATION --- */
#define USE_ADV_TRACE 1
#define TRACE_UART_HANDLE (&huart1)
#define TRACE_ADV_INSTANCE USART1

#if (USE_ADV_TRACE == 1)
    #include "stm32_adv_trace.h"
    #define APP_TRACE_PRINTF(...) UTIL_ADV_TRACE_FSend(__VA_ARGS__)
#else
    #define APP_TRACE_PRINTF(...) trace_Printf(TRACE_UART_HANDLE, __VA_ARGS__)
#endif


/** @brief Size of the shared TX buffer for all UART instances. */
#define TRACE_SHARED_TX_BUFFER_SIZE 2048

/** @brief Size of the temporary buffer for a single formatted print. Should be smaller than the shared buffer. */
#define TRACE_PRINTF_BUFFER_SIZE 256

/** @brief When the TX buffer is full, the driver can either block and wait, or return an error immediately. */
#define TRACE_BUSY_POLICY_RETURN_ERROR 0
#define TRACE_BUSY_POLICY_BLOCK        1

/** @brief Select the desired behavior for handling a full transmit buffer. */
#define TRACE_BUSY_BEHAVIOR TRACE_BUSY_POLICY_BLOCK

/** @brief If using the blocking policy, this is the max time in ms the driver will wait before returning a timeout error. */
#define TRACE_BLOCKING_TIMEOUT_MS 100


///** @brief Size of the TX buffer for formatted prints. */
//#define TX_BUFFER_SIZE 512
//
///** @brief Maximum chunk size for one transmission call. */
//#define CHUNK_SIZE 128
//
///** @brief Maximum number of retries for chunked transmissions. */
//#define MAX_RETRIES 3

/**
 * @brief Configuration structure describing a particular UART instance.
 */

typedef struct {
    uint32_t tx_pin;              /**< TX GPIO pin. */
    uint32_t rx_pin;              /**< RX GPIO pin. */
    uint32_t alternate_function;  /**< GPIO alternate function setting. */
    IRQn_Type irqn;               /**< USART IRQ number. */
    uint8_t usart_priority;       /**< USART interrupt priority. */
    uint8_t dma_priority;         /**< DMA interrupt priority. */

    DMA_Channel_TypeDef *tx_dma_channel; /**< DMA channel for TX. */
    DMA_Channel_TypeDef *rx_dma_channel; /**< DMA channel for RX. */
    uint32_t dma_tx_request;               /**< DMA request mapping. */
    uint32_t dma_rx_request;               /**< DMA request mapping. */
    IRQn_Type dma_tx_irqn;                 /**< DMA IRQ number. */
    IRQn_Type dma_rx_irqn;                 /**< DMA IRQ number. */
} Trace_UART_Config;

extern const Trace_UART_Config uart_configs[];

#ifdef __cplusplus
}
#endif

#endif /* APPLICATION_USER_CORE_INC_TRACE_CONF_H_ */
