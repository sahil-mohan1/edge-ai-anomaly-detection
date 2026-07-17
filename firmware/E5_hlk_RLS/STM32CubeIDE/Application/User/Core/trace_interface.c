/**
 * @file      trace_interface.c
 * @author    MCD Application Team (Modified by Zero)
 * @version   1.0.0
 * @date      12-September-2025
 * @brief     Bridge between the stm32_adv_trace utility and the custom trace driver.
 *
 * @details   This file implements the UTIL_ADV_TRACE_Driver_s interface required
 * by the ST advanced trace utility. It acts as an adapter layer,
 * translating calls from the VCOM/adv_trace system into requests
 * for the master trace.c driver, which manages the hardware and a
 * unified transmission queue. All hardware control is abstracted
 * away from this file and handled exclusively by trace.c.
 */

/* Includes ------------------------------------------------------------------*/
#include "stm32_adv_trace.h"
#include "trace.h"
#include "trace_conf.h"

#if defined(USE_ADV_TRACE) && (USE_ADV_TRACE == 1)
/* Private function prototypes -----------------------------------------------*/

/**
 * @brief  Initializes the trace interface and registers the TX completion hook.
 * @param  cb  Pointer to the TX completion callback provided by stm32_adv_trace.
 * @retval UTIL_ADV_TRACE_Status_t Status of the operation.
 */
static UTIL_ADV_TRACE_Status_t AdvTrace_Init(void (*cb)(void *));

/**
 * @brief  De-initializes the underlying trace driver.
 * @retval UTIL_ADV_TRACE_Status_t Status of the operation.
 */
static UTIL_ADV_TRACE_Status_t AdvTrace_DeInit(void);

/**
 * @brief  Handles reception requests from the stm32_adv_trace utility.
 * @note   This implementation is a placeholder as VCOM reception is now handled
 * by the more advanced trace.c driver.
 * @param  cb  Callback for received data (not actively used in this bridge).
 * @retval UTIL_ADV_TRACE_Status_t Status of the operation.
 */
static UTIL_ADV_TRACE_Status_t AdvTrace_StartRx(void (*cb)(uint8_t *, uint16_t, uint8_t));

/**
 * @brief  Sends data from the stm32_adv_trace FIFO to the master trace driver's queue.
 * @param  p_data Pointer to the data buffer to send.
 * @param  size   Number of bytes to send.
 * @retval UTIL_ADV_TRACE_Status_t Status of the operation.
 */
static UTIL_ADV_TRACE_Status_t AdvTrace_Send(uint8_t *p_data, uint16_t size);

/**
 * @brief  Hook function called by the master trace driver upon TX completion.
 * @param  huart Pointer to the UART handle (not used).
 * @param  owner The owner of the completed transmission.
 */
static void AdvTrace_HookTxCplt(UART_HandleTypeDef *huart, Transmission_Owner_t owner);


/* Private variables ---------------------------------------------------------*/

/**
 * @brief  Stores the TX completion callback provided by stm32_adv_trace.
 */
static void (*TraceTxCpltCallback)(void *p_ptr);


/* Exported variables --------------------------------------------------------*/

/**
 * @brief  The driver interface structure exposed to the stm32_adv_trace utility.
 * @details This structure links the high-level trace utility to our low-level
 * driver implementation, acting as the primary integration point.
 */
const UTIL_ADV_TRACE_Driver_s UTIL_TraceDriver =
{
  .Init = AdvTrace_Init,
  .DeInit = AdvTrace_DeInit,
  .StartRx = AdvTrace_StartRx,
  .Send = AdvTrace_Send,
};


/* Function implementations --------------------------------------------------*/

static UTIL_ADV_TRACE_Status_t AdvTrace_Init(void (*cb)(void *))
{
    TraceTxCpltCallback = cb;
    trace_RegisterTxCpltHook(AdvTrace_HookTxCplt);
    return UTIL_ADV_TRACE_OK;
}

static UTIL_ADV_TRACE_Status_t AdvTrace_DeInit(void)
{
    trace_Deinit(TRACE_UART_HANDLE);
    return UTIL_ADV_TRACE_OK;
}

static UTIL_ADV_TRACE_Status_t AdvTrace_Send(uint8_t *p_data, uint16_t size)
{
    // Set the transmission mode for this request and submit it to the scheduler.
    trace_SetTxMode(TRACE_UART_HANDLE, TRACE_TX_MODE_DMA);
    if (trace_WriteRaw(TRACE_UART_HANDLE, p_data, size, OWNER_VCOM) == TRACE_SUCCESS)
    {
        return UTIL_ADV_TRACE_OK;
    }

    // The scheduler queue was full. stm32_adv_trace is designed to handle this
    // by retrying later. Returning OK prevents it from seeing a fatal error.
    return UTIL_ADV_TRACE_OK;
}

static UTIL_ADV_TRACE_Status_t AdvTrace_StartRx(void (*cb)(uint8_t *, uint16_t, uint8_t))
{
    // Reception is managed by the master trace.c driver and its clients,
    // so this function is a placeholder and does not need to take action.
    return UTIL_ADV_TRACE_OK;
}

static void AdvTrace_HookTxCplt(UART_HandleTypeDef *huart, Transmission_Owner_t owner)
{
    // This hook is called for EVERY completed transmission.
    // We must only notify the stm32_adv_trace FIFO if the transmission
    // belonged to it, otherwise we would corrupt its state.
    if (owner == OWNER_VCOM && TraceTxCpltCallback != NULL)
    {
        // This call signals the stm32_adv_trace utility that it is now safe
        // to send the next chunk of data from its internal buffer.
        TraceTxCpltCallback(NULL);
    }
}

#endif

