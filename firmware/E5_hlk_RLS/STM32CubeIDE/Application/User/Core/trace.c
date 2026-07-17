#include "trace.h"
#include "stm32_tiny_vsnprintf.h"
#include "trace_conf.h"
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

#define TX_QUEUE_SIZE 8
#define RX_LINE_BUFFER_SIZE 256

#ifndef TRACE_CHUNK_WAIT_MS
#define TRACE_CHUNK_WAIT_MS 50
#endif
#ifndef TRACE_CHUNK_RETRY_DELAY_MS
#define TRACE_CHUNK_RETRY_DELAY_MS 1
#endif


/**
 * @brief Array of pre-defined UART configurations for supported instances.
 */
const Trace_UART_Config uart_configs[] = {
    [0] = {
        .tx_pin = GPIO_PIN_6,
        .rx_pin = GPIO_PIN_7,
        .alternate_function = GPIO_AF7_USART1,
        .irqn = USART1_IRQn,
        .usart_priority = 5,
        .tx_dma_channel = DMA1_Channel5,
        .rx_dma_channel = DMA1_Channel4,
        .dma_tx_request = DMA_REQUEST_USART1_TX,
        .dma_rx_request = DMA_REQUEST_USART1_RX,
		.dma_priority = 5,
		.dma_tx_irqn = DMA1_Channel5_IRQn,
		.dma_rx_irqn = DMA1_Channel4_IRQn
    },
    [1] = {
            .tx_pin = GPIO_PIN_2,
            .rx_pin = GPIO_PIN_3,
            .alternate_function = GPIO_AF7_USART2,
            .irqn = USART2_IRQn,
            .usart_priority = 5,  // Lower than LoRaWAN radio
            .tx_dma_channel = DMA1_Channel2,
            .rx_dma_channel = DMA1_Channel1,
            .dma_tx_request = DMA_REQUEST_USART2_TX,
            .dma_rx_request = DMA_REQUEST_USART2_RX,
    		.dma_priority = 5,  // Lower than LoRaWAN radio
    		.dma_tx_irqn = DMA1_Channel2_IRQn,
    		.dma_rx_irqn = DMA1_Channel1_IRQn
    },
    [2] = {
            .tx_pin = GPIO_PIN_1,
            .rx_pin = GPIO_PIN_0,
            .alternate_function = GPIO_AF8_LPUART1,
            .irqn = LPUART1_IRQn,
            .usart_priority = 5,  // Lower than LoRaWAN radio
            .tx_dma_channel = DMA1_Channel7,
            .rx_dma_channel = DMA1_Channel6,
            .dma_tx_request = DMA_REQUEST_LPUART1_TX,
            .dma_rx_request = DMA_REQUEST_LPUART1_RX,
    		.dma_priority = 5,  // Lower than LoRaWAN radio
    		.dma_tx_irqn = DMA1_Channel7_IRQn,
    		.dma_rx_irqn = DMA1_Channel6_IRQn
    }
};

/**
 * @brief Structure to hold a single lightweight transmission request in the queue.
 * @note  This version does not hold the data itself, only a reference to the
 * data's location in the shared circular buffer.
 */
typedef struct {
    uint16_t offset;    // Start offset in the shared circular buffer
    uint16_t length;    // Length of the data to send
    Transmission_Owner_t owner;
    uint8_t mode;
} TxRequest_t;


/**
 * @brief Manages the state of the transmission scheduler for a single UART.
 */
typedef struct {
    volatile bool tx_busy;
    volatile uint8_t head;
    volatile uint8_t tail;
    TxRequest_t queue[TX_QUEUE_SIZE];
    uint8_t current_tx_mode;
    bool is_sending_wrapped_part_one; // State for handling wrapped transmissions
} TxScheduler_t;

/**
 * @brief Holds the state and configuration for an ongoing reception.
 */
typedef struct {
    volatile bool rx_busy;
    volatile uint16_t rx_head; // For interrupt mode ring buffer
    volatile uint16_t rx_tail; // For interrupt mode ring buffer
    uint8_t *buffer;
    uint16_t buffer_size;
    uint8_t terminator;
    Trace_RxProcessMode_t process_mode;
    Trace_HwMode_t hw_mode;
    union {
        Trace_RxByteCallback_t   byte_cb;
        Trace_RxLineCallback_t   line_cb;
        Trace_RxBufferCallback_t buffer_cb;
        Trace_RxCustomCallback_t custom_cb;
    };
    Trace_ErrorCallback_t error_cb;
    volatile uint16_t dma_last_pos; // Used to track circular DMA progress
} RxState_t;

static USART_AdvInit_t g_saved_adv_config[3];

// --- NEW: Shared circular buffer for all TX data ---
static uint8_t shared_tx_buffer[TRACE_SHARED_TX_BUFFER_SIZE];
static volatile uint32_t shared_tx_head = 0; // Write position
static volatile uint32_t shared_tx_tail = 0; // Read position (start of oldest unsent data)

static TxScheduler_t tx_schedulers[3] = {0};
static RxState_t rx_states[3] = {0};

// Buffer for trace_Printf formatting
static char tx_print_buffer[TRACE_PRINTF_BUFFER_SIZE];

// Static buffer for safe line assembly in ISR/callbacks to avoid stack allocation
static uint8_t line_assembly_buffer[128];
static uint16_t line_assembly_idx = 0;
static Trace_TxCpltHook_t tx_cplt_hook = NULL;

/* --- Static Function Prototypes --- */

static RxState_t* get_rx_state(UART_HandleTypeDef *huart);
static TxScheduler_t* get_tx_scheduler(UART_HandleTypeDef *huart);
static uint8_t get_uart_index(UART_HandleTypeDef *huart);
static void process_tx_queue(UART_HandleTypeDef *huart);
static Trace_Error_t enable_DMA_TX(UART_HandleTypeDef *huart, const Trace_UART_Config *config);
static Trace_Error_t enable_DMA_RX(UART_HandleTypeDef *huart, const Trace_UART_Config *config);
static void recover_from_error(UART_HandleTypeDef *huart);

Trace_Error_t trace_Init(USART_TypeDef *uart_instance, uint32_t baudRate) {
    if (baudRate < 300 || baudRate > 2000000) {
        return TRACE_ERROR_INVALID_PARAMETER;
    }

    USART_AdvInit_t advConfig = {
        .Instance = uart_instance,
        .BaudRate = baudRate,
        .WordLength = UART_WORDLENGTH_8B,
        .StopBits = UART_STOPBITS_1,
        .Parity = UART_PARITY_NONE,
        .Mode = UART_MODE_TX_RX,
        .HwFlowCtl = UART_HWCONTROL_NONE,
        .OverSampling = UART_OVERSAMPLING_16,
        .OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE,
        .AdvFeatureInit = UART_ADVFEATURE_NO_INIT,
		.ClockPrescaler = UART_PRESCALER_DIV1,
        .DMA_Mode = TRACE_DMA_MODE_NONE
    };

    return trace_InitAdv(&advConfig);
}

Trace_Error_t trace_InitAdv(USART_AdvInit_t *advConfig) {
    UART_HandleTypeDef *huart = NULL;
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    const Trace_UART_Config *config = NULL;

    if (advConfig == NULL || advConfig->Instance == NULL) {
        return TRACE_ERROR_INVALID_PARAMETER;
    }


    if (advConfig->Instance == USART1) {
        config = &uart_configs[0];
        huart = &huart1;
        
        /* Configure peripheral clock source */
        RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};
        PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_USART1;
        PeriphClkInit.Usart1ClockSelection = RCC_USART1CLKSOURCE_SYSCLK;
        if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK) {
            return TRACE_ERROR_HARDWARE_FAILURE;
        }
        
        __HAL_RCC_USART1_CLK_ENABLE();
        __HAL_RCC_GPIOB_CLK_ENABLE();
        GPIO_InitStruct.Pin = config->tx_pin | config->rx_pin;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
        GPIO_InitStruct.Pull = GPIO_NOPULL;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
        GPIO_InitStruct.Alternate = config->alternate_function;
        HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

    } else if (advConfig->Instance == USART2) {
        config = &uart_configs[1];
        huart = &huart2;
        __HAL_RCC_USART2_CLK_ENABLE();
        __HAL_RCC_GPIOA_CLK_ENABLE();
        GPIO_InitStruct.Pin = config->tx_pin | config->rx_pin;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
        GPIO_InitStruct.Pull = GPIO_NOPULL;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
        GPIO_InitStruct.Alternate = config->alternate_function;
        HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);
    }
    else if (advConfig->Instance == LPUART1) {
            config = &uart_configs[2];
            huart = &hlpuart1;
            __HAL_RCC_LPUART1_CLK_ENABLE();
            __HAL_RCC_GPIOC_CLK_ENABLE();
            GPIO_InitStruct.Pin = config->tx_pin | config->rx_pin;
            GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
            GPIO_InitStruct.Pull = GPIO_NOPULL;
            GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
            GPIO_InitStruct.Alternate = config->alternate_function;
            HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);
        }
    else {
        return TRACE_ERROR_UNSUPPORTED_INSTANCE;
    }


    // UART Configuration
    huart->Instance = advConfig->Instance;
    huart->Init = (UART_InitTypeDef){
        .BaudRate = advConfig->BaudRate,
        .WordLength = advConfig->WordLength,
        .StopBits = advConfig->StopBits,
        .Parity = advConfig->Parity,
        .Mode = advConfig->Mode,
        .HwFlowCtl = advConfig->HwFlowCtl,
        .OverSampling = advConfig->OverSampling,
        .OneBitSampling = advConfig->OneBitSampling
    };
    huart->AdvancedInit.AdvFeatureInit = advConfig->AdvFeatureInit;

    if (HAL_UART_Init(huart) != HAL_OK) {
        return TRACE_ERROR_HARDWARE_FAILURE;
    }
    if (HAL_UARTEx_SetTxFifoThreshold(huart, UART_TXFIFO_THRESHOLD_1_8) != HAL_OK) return TRACE_ERROR_SET_TX_FIFO;
    if (HAL_UARTEx_SetRxFifoThreshold(huart, UART_RXFIFO_THRESHOLD_1_8) != HAL_OK) return TRACE_ERROR_SET_RX_FIFO;
    if (HAL_UARTEx_EnableFifoMode(huart) != HAL_OK) return TRACE_ERROR_FIFO_Config;
    // Interrupt Configuration
    HAL_NVIC_SetPriority(config->irqn, config->usart_priority, 0);
    HAL_NVIC_EnableIRQ(config->irqn);

    // DMA Configuration
    if (advConfig->DMA_Mode == TRACE_DMA_MODE_TX || advConfig->DMA_Mode == TRACE_DMA_MODE_RX_TX) {
        if (enable_DMA_TX(huart, config) != TRACE_SUCCESS) return TRACE_ERROR_DMA_INIT;
    }
    if (advConfig->DMA_Mode == TRACE_DMA_MODE_RX || advConfig->DMA_Mode == TRACE_DMA_MODE_RX_TX) {
        if (enable_DMA_RX(huart, config) != TRACE_SUCCESS) return TRACE_ERROR_DMA_INIT;
    }
    uint8_t index = get_uart_index(huart);
    if (index != 0xFF)
    {
        memcpy(&g_saved_adv_config[index], advConfig, sizeof(USART_AdvInit_t));
    }
    return TRACE_SUCCESS;
}

static Trace_Error_t enable_DMA_TX(UART_HandleTypeDef *huart, const Trace_UART_Config *config) {
	DMA_HandleTypeDef *hdma_tx = NULL;
    if(huart->Instance == USART1)  hdma_tx = &hdma_usart1_tx;
    else if (huart->Instance == USART2)  hdma_tx = &hdma_usart2_tx;
    else if (huart->Instance == LPUART1)  hdma_tx = &hdma_lpuart1_tx;

    __DMA1_CLK_ENABLE();
    __HAL_RCC_DMAMUX1_CLK_ENABLE();

    hdma_tx->Instance = config->tx_dma_channel;
    hdma_tx->Init = (DMA_InitTypeDef){
        .Request = config->dma_tx_request,
        .Direction = DMA_MEMORY_TO_PERIPH,
        .PeriphInc = DMA_PINC_DISABLE,
        .MemInc = DMA_MINC_ENABLE,
        .PeriphDataAlignment = DMA_PDATAALIGN_BYTE,
        .MemDataAlignment = DMA_MDATAALIGN_BYTE,
        .Mode = DMA_NORMAL,
        .Priority = config->dma_priority
    };

    if (HAL_DMA_Init(hdma_tx) != HAL_OK) return TRACE_ERROR_DMA_INIT;

    __HAL_LINKDMA(huart, hdmatx, *hdma_tx);
    HAL_NVIC_SetPriority(config->dma_tx_irqn, config->dma_priority, 0);
    HAL_NVIC_EnableIRQ(config->dma_tx_irqn);
    return TRACE_SUCCESS;
}

static Trace_Error_t enable_DMA_RX(UART_HandleTypeDef *huart, const Trace_UART_Config *config) {
	DMA_HandleTypeDef *hdma_rx = NULL;
    if(huart->Instance == USART1)  hdma_rx = &hdma_usart1_rx;
    else if (huart->Instance == USART2)  hdma_rx = &hdma_usart2_rx;
    else if (huart->Instance == LPUART1)  hdma_rx = &hdma_lpuart1_rx;

	__DMA1_CLK_ENABLE();
    __HAL_RCC_DMAMUX1_CLK_ENABLE();

    hdma_rx->Instance = config->rx_dma_channel;
    hdma_rx->Init = (DMA_InitTypeDef){
        .Request = config->dma_rx_request,
        .Direction = DMA_PERIPH_TO_MEMORY,
        .PeriphInc = DMA_PINC_DISABLE,
        .MemInc = DMA_MINC_ENABLE,
        .PeriphDataAlignment = DMA_PDATAALIGN_BYTE,
        .MemDataAlignment = DMA_MDATAALIGN_BYTE,
        .Mode = DMA_CIRCULAR, // Default to circular for robust streaming with ReceiveToIdle
        .Priority = config->dma_priority
    };

    if (HAL_DMA_Init(hdma_rx) != HAL_OK) return TRACE_ERROR_DMA_INIT;

    __HAL_LINKDMA(huart, hdmarx, *hdma_rx);

    HAL_NVIC_SetPriority(config->dma_rx_irqn, config->dma_priority, 0);
    HAL_NVIC_EnableIRQ(config->dma_rx_irqn);
    return TRACE_SUCCESS;
}

Trace_Error_t trace_Deinit(UART_HandleTypeDef *huart) {
    const Trace_UART_Config *config = NULL;

    if (huart == NULL) {
        return TRACE_ERROR_INVALID_PARAMETER;
    }

    // Wait for any ongoing transmission to finish, with a timeout
    uint32_t timeout = HAL_GetTick() + 1000;
    while (is_uart_transmission_ongoing(huart)) {
        if (HAL_GetTick() > timeout) {
            HAL_UART_AbortTransmit(huart);
            break;
        }
    }

    if (huart->Instance == USART1) {
        config = &uart_configs[0];
    } else if (huart->Instance == USART2) {
        config = &uart_configs[1];
    } else if (huart->Instance == LPUART1) {
        config = &uart_configs[2];
    } else {
        return TRACE_ERROR_UNSUPPORTED_INSTANCE;
    }

    // De-initialize peripherals
    HAL_UART_DeInit(huart);

    // Disable clocks
    if (huart->Instance == USART1) {
        __HAL_RCC_USART1_CLK_DISABLE();
        HAL_GPIO_DeInit(GPIOB, config->tx_pin | config->rx_pin);
        HAL_NVIC_DisableIRQ(config->irqn);
    } else if (huart->Instance == USART2) {
        __HAL_RCC_USART2_CLK_DISABLE();
        HAL_GPIO_DeInit(GPIOA, config->tx_pin | config->rx_pin);
        HAL_NVIC_DisableIRQ(config->irqn);
    }
    else if (huart->Instance == LPUART1) {
    	__HAL_RCC_LPUART1_CLK_DISABLE();
            HAL_GPIO_DeInit(GPIOC, config->tx_pin | config->rx_pin);
            HAL_NVIC_DisableIRQ(config->irqn);
        }

    return TRACE_SUCCESS;
}

Trace_Error_t trace_Resume(UART_HandleTypeDef *huart)
{
    if (!huart || !huart->Instance)
    {
        return TRACE_ERROR_INVALID_PARAMETER;
    }

    // --- FIX: Use the saved advanced configuration to re-initialize ---
    uint8_t index = get_uart_index(huart);
    if (index != 0xFF)
    {
        // Re-initializing with the saved advanced parameters is the safest
        // way to fully restore the peripheral state, including DMA.
        return trace_InitAdv(&g_saved_adv_config[index]);
    }

    return TRACE_ERROR_UNSUPPORTED_INSTANCE;
}

void trace_RegisterTxCpltHook(Trace_TxCpltHook_t hook)
{
    tx_cplt_hook = hook;
}


/* ============================================================================ */
/* TRANSMISSION                                  */
/* ============================================================================ */

Trace_Error_t trace_Printf(UART_HandleTypeDef *huart, const char *format, ...)
{
    if (!huart || !format) return TRACE_ERROR_INVALID_PARAMETER;

    va_list args;
    va_start(args, format);
    int len = tiny_vsnprintf_like(tx_print_buffer, sizeof(tx_print_buffer), format, args);
    va_end(args);

    if (len < 0) return TRACE_ERROR_INVALID_PARAMETER;

    if (len < (int)sizeof(tx_print_buffer)) {
        return trace_WriteRaw(huart, (const uint8_t *)tx_print_buffer, (uint16_t)len, OWNER_APP_TRACE);
    }

    /* Fallback: allocate full buffer and do chunked send */
    char *bigbuf = (char *)malloc((size_t)len + 1);
    if (!bigbuf) {
        /* allocation failed: send truncated fast-path */
        int tlen = sizeof(tx_print_buffer) - 1;
        return trace_WriteRaw(huart, (const uint8_t *)tx_print_buffer, (uint16_t)tlen, OWNER_APP_TRACE);
    }

    va_start(args, format);
    tiny_vsnprintf_like(bigbuf, (size_t)len + 1, format, args);
    va_end(args);

    Trace_Error_t err = trace_WriteRawChunked(huart, (const uint8_t *)bigbuf, (uint32_t)len, OWNER_APP_TRACE, 500 /*overall timeout ms*/);
    free(bigbuf);
    return err;
}


Trace_Error_t trace_WriteRawChunked(UART_HandleTypeDef *huart, const uint8_t *data, uint32_t length, Transmission_Owner_t owner, uint32_t timeout_ms)
{
    if (!huart || (!data && length != 0)) return TRACE_ERROR_INVALID_PARAMETER;
    if (length == 0) return TRACE_SUCCESS;

    uint32_t offset = 0;
    uint32_t start_ms = HAL_GetTick();

    while (offset < length) {
        // Use a reasonable chunk size that won't monopolize the shared buffer
        uint16_t chunk_len = (uint16_t)((length - offset) > 256 ? 256 : (length - offset));

        uint32_t chunk_start = HAL_GetTick();
        Trace_Error_t err;
        while (1) {
            err = trace_WriteRaw(huart, &data[offset], chunk_len, owner);
            if (err == TRACE_SUCCESS) break;

            // Unrecoverable error from the write function (e.g., invalid param, or timeout from blocking policy)
            if (err != TRACE_ERROR_BUSY) return err;

            if (timeout_ms == 0) return TRACE_ERROR_BUSY;
            if ((HAL_GetTick() - chunk_start) >= TRACE_CHUNK_WAIT_MS) return TRACE_ERROR_BUSY;

            process_tx_queue(huart);
            HAL_Delay(TRACE_CHUNK_RETRY_DELAY_MS);
        }
        offset += chunk_len;
        if (timeout_ms > 0 && (HAL_GetTick() - start_ms) >= timeout_ms) return TRACE_ERROR_TIMEOUT;
    }
    return TRACE_SUCCESS;
}

Trace_Error_t trace_WriteRaw(UART_HandleTypeDef *huart, const uint8_t *data, uint16_t length, Transmission_Owner_t owner)
{
    if (!huart || !data || length == 0) return TRACE_ERROR_INVALID_PARAMETER;
    if (length >= TRACE_SHARED_TX_BUFFER_SIZE) return TRACE_ERROR_INVALID_PARAMETER; // Message must be smaller than the buffer

    TxScheduler_t *scheduler = get_tx_scheduler(huart);
    if (!scheduler) return TRACE_ERROR_UNSUPPORTED_INSTANCE;

#if TRACE_BUSY_BEHAVIOR == TRACE_BUSY_POLICY_BLOCK
    uint32_t start_tick = HAL_GetTick();
    // Blocking wait for space in both the metadata queue AND the shared data buffer
    while (1) {
        __disable_irq();
        uint32_t head = shared_tx_head;
        uint32_t tail = shared_tx_tail;
        __enable_irq();

        // Robust free space calculation. We leave 1 byte free to distinguish empty/full conditions.
        uint32_t used_space = (head - tail + TRACE_SHARED_TX_BUFFER_SIZE) % TRACE_SHARED_TX_BUFFER_SIZE;
        uint32_t free_space = TRACE_SHARED_TX_BUFFER_SIZE - used_space - 1;

        uint8_t next_head_sched = (scheduler->head + 1) % TX_QUEUE_SIZE;

        // Check if there is space in both queues
        if (next_head_sched != scheduler->tail && free_space >= length) {
            break; // Exit loop, space is available
        }

        // Check for timeout
        if ((HAL_GetTick() - start_tick) > TRACE_BLOCKING_TIMEOUT_MS) {
            return TRACE_ERROR_TIMEOUT;
        }
    }
#else
    // Non-blocking check
    __disable_irq();
    uint32_t head = shared_tx_head;
    uint32_t tail = shared_tx_tail;
    __enable_irq();

    uint32_t used_space = (head - tail + TRACE_SHARED_TX_BUFFER_SIZE) % TRACE_SHARED_TX_BUFFER_SIZE;
    uint32_t free_space = TRACE_SHARED_TX_BUFFER_SIZE - used_space - 1;

    uint8_t next_head_sched = (scheduler->head + 1) % TX_QUEUE_SIZE;
    if (next_head_sched == scheduler->tail || free_space < length) {
        return TRACE_ERROR_BUSY; // Queue or buffer is full
    }
#endif

    // --- At this point, we are guaranteed to have space ---
    __disable_irq();

    // Copy data into the shared circular buffer
    uint32_t write_offset = shared_tx_head;
    if (write_offset + length > TRACE_SHARED_TX_BUFFER_SIZE) {
        // Data wraps around the buffer end, requires two copies
        uint16_t first_chunk_len = TRACE_SHARED_TX_BUFFER_SIZE - write_offset;
        memcpy(&shared_tx_buffer[write_offset], data, first_chunk_len);
        memcpy(&shared_tx_buffer[0], data + first_chunk_len, length - first_chunk_len);
        shared_tx_head = length - first_chunk_len;
    } else {
        // Data fits in a contiguous block
        memcpy(&shared_tx_buffer[write_offset], data, length);
        shared_tx_head = (write_offset + length);
        // Handle case where it perfectly fills to the end
        if (shared_tx_head == TRACE_SHARED_TX_BUFFER_SIZE) {
            shared_tx_head = 0;
        }
    }

    // Enqueue the lightweight metadata
    TxRequest_t *req = &scheduler->queue[scheduler->head];
    req->offset = (uint16_t)write_offset;
    req->length = length;
    req->owner  = owner;
    req->mode   = scheduler->current_tx_mode;

    scheduler->head = (scheduler->head + 1) % TX_QUEUE_SIZE;

    __enable_irq();

    process_tx_queue(huart);

    return TRACE_SUCCESS;
}


static void process_tx_queue(UART_HandleTypeDef *huart)
{
    TxScheduler_t *scheduler = get_tx_scheduler(huart);
    if (!scheduler) return;
    __disable_irq();
    // Check if a transmission is already in progress or if the queue is empty
    if (scheduler->tx_busy || (scheduler->head == scheduler->tail)) {
    	__enable_irq();
        return;
    }

    // Mark the scheduler as busy and get the next request
    scheduler->tx_busy = true;
    TxRequest_t *request = &scheduler->queue[scheduler->tail];
    __enable_irq();

    HAL_StatusTypeDef status = HAL_OK;

    // --- FIX: Handle wrapped transmissions by splitting them ---
    if (request->offset + request->length > TRACE_SHARED_TX_BUFFER_SIZE) {
        // Transmission wraps the circular buffer boundary. Send in two parts.
        uint16_t first_chunk_len = TRACE_SHARED_TX_BUFFER_SIZE - request->offset;
        scheduler->is_sending_wrapped_part_one = true;

        switch (request->mode) {
            case TRACE_TX_MODE_DMA:       status = HAL_UART_Transmit_DMA(huart, &shared_tx_buffer[request->offset], first_chunk_len); break;
            case TRACE_TX_MODE_INTERRUPT: status = HAL_UART_Transmit_IT(huart, &shared_tx_buffer[request->offset], first_chunk_len); break;
            default:                      status = HAL_UART_Transmit(huart, &shared_tx_buffer[request->offset], first_chunk_len, HAL_MAX_DELAY); break;
        }
    } else {
        // Transmission is in a single contiguous block.
        scheduler->is_sending_wrapped_part_one = false;
        switch (request->mode) {
            case TRACE_TX_MODE_DMA:       status = HAL_UART_Transmit_DMA(huart, &shared_tx_buffer[request->offset], request->length); break;
            case TRACE_TX_MODE_INTERRUPT: status = HAL_UART_Transmit_IT(huart, &shared_tx_buffer[request->offset], request->length); break;
            default:                      status = HAL_UART_Transmit(huart, &shared_tx_buffer[request->offset], request->length, HAL_MAX_DELAY);
                                          if (status == HAL_OK) trace_TxCpltCallback(huart); // Manual call for polling mode
                                          break;
        }
    }

    if (status != HAL_OK) {
    	__disable_irq();
        scheduler->tx_busy = false; // Transmission failed to start
        scheduler->is_sending_wrapped_part_one = false;
        __enable_irq();
    }
}

Trace_Error_t trace_SetTxMode(UART_HandleTypeDef *huart, uint8_t mode)
{
    TxScheduler_t *scheduler = get_tx_scheduler(huart);
    if (!scheduler) return TRACE_ERROR_UNSUPPORTED_INSTANCE;
    if (mode > TRACE_TX_MODE_DMA) return TRACE_ERROR_INVALID_MODE;

    scheduler->current_tx_mode = mode;
    return TRACE_SUCCESS;
}

bool is_uart_transmission_ongoing(UART_HandleTypeDef *huart)
{
    TxScheduler_t *scheduler = get_tx_scheduler(huart);
    if (!scheduler) return false;
    // The system is busy if the tx_busy flag is set OR if the queue is not empty.
    return scheduler->tx_busy || (scheduler->head != scheduler->tail);
}

void trace_TxCpltCallback(UART_HandleTypeDef *huart)
{
    TxScheduler_t *scheduler = get_tx_scheduler(huart);
    if (!scheduler || !scheduler->tx_busy) return;

    // --- FIX: State machine for handling wrapped transmissions ---
    if (scheduler->is_sending_wrapped_part_one) {
        // First part of a wrapped transfer is complete. Now send the second part.
        scheduler->is_sending_wrapped_part_one = false;

        TxRequest_t *request = &scheduler->queue[scheduler->tail];
        uint16_t first_chunk_len = TRACE_SHARED_TX_BUFFER_SIZE - request->offset;
        uint16_t second_chunk_len = request->length - first_chunk_len;

        // tx_busy remains true because we are still processing the same request.
        // We do NOT advance the tail yet.
        HAL_StatusTypeDef status = HAL_OK;
        switch (request->mode) {
             case TRACE_TX_MODE_DMA:       status = HAL_UART_Transmit_DMA(huart, &shared_tx_buffer[0], second_chunk_len); break;
             case TRACE_TX_MODE_INTERRUPT: status = HAL_UART_Transmit_IT(huart, &shared_tx_buffer[0], second_chunk_len); break;
             default:                      status = HAL_UART_Transmit(huart, &shared_tx_buffer[0], second_chunk_len, HAL_MAX_DELAY);
                                           if (status == HAL_OK) trace_TxCpltCallback(huart); // Manual call for polling mode
                                           break;
        }
        if (status != HAL_OK) {
             // If the second part fails to start, we're in a tricky state.
             // Forcing the queue to advance is the safest recovery.
             __disable_irq();
             shared_tx_tail = (shared_tx_tail + request->length) % TRACE_SHARED_TX_BUFFER_SIZE;
             scheduler->tail = (scheduler->tail + 1) % TX_QUEUE_SIZE;
             scheduler->tx_busy = false;
             __enable_irq();
             process_tx_queue(huart); // Try to start the next item
        }
        return; // Important: exit here, do not process the queue further yet.
    }

    // A complete (or the second part of a wrapped) transmission finished.
    __disable_irq();
    TxRequest_t *completed_request = &scheduler->queue[scheduler->tail];

    if (tx_cplt_hook) {
        tx_cplt_hook(huart, completed_request->owner);
    }

    // Advance the shared buffer tail and the scheduler queue tail atomically
    shared_tx_tail = (shared_tx_tail + completed_request->length) % TRACE_SHARED_TX_BUFFER_SIZE;
    scheduler->tail = (scheduler->tail + 1) % TX_QUEUE_SIZE;
    scheduler->tx_busy = false;
    __enable_irq();

    /* Start next send if any */
    process_tx_queue(huart);
}

Trace_Error_t trace_FlushTx(UART_HandleTypeDef *huart, uint32_t timeout)
{
    uint32_t start_tick = HAL_GetTick();

    // Wait while the hardware is busy or the software queue has pending items.
    while (is_uart_transmission_ongoing(huart))
    {
        // Check for timeout
        if ((HAL_GetTick() - start_tick) > timeout)
        {
            return TRACE_ERROR_TIMEOUT;
        }
        // Yield to the OS or sleep briefly if in a bare-metal RTOS environment
        // For simple bare-metal, this will be a busy-wait loop.
    }
    return TRACE_SUCCESS;
}

/* ============================================================================ */
/* RECEPTION                                    */
/* ============================================================================ */

Trace_Error_t trace_StartRx(UART_HandleTypeDef *huart, const Trace_RxConfig_t *config) {
    if (!huart || !config || !config->buffer || config->buffer_size == 0)
        return TRACE_ERROR_INVALID_PARAMETER;

    RxState_t *state = get_rx_state(huart);
    if (!state) return TRACE_ERROR_UNSUPPORTED_INSTANCE;

    trace_StopRx(huart);

    // Configure state from user config
    *state = (RxState_t){0}; // Clear previous state
    state->buffer = config->buffer;
    state->buffer_size = config->buffer_size;
    state->terminator = config->terminator;
    state->process_mode = config->process_mode;
    state->error_cb = config->error_cb;

    // Assign callbacks
    switch(config->process_mode) {
        case TRACE_RX_PROCESS_BYTE:   state->byte_cb = config->byte_cb;   break;
        case TRACE_RX_PROCESS_LINE:   state->line_cb = config->line_cb;   break;
        case TRACE_RX_PROCESS_BUFFER: state->buffer_cb = config->buffer_cb; break;
        case TRACE_RX_PROCESS_CUSTOM: state->custom_cb = config->custom_cb; break;
    }

    // Determine hardware mode
    if (config->process_mode == TRACE_RX_PROCESS_BUFFER) {
        state->hw_mode = TRACE_HW_MODE_DMA;
    } else if (config->process_mode == TRACE_RX_PROCESS_CUSTOM) {
        state->hw_mode = config->custom_hw_mode;
    } else {
        // For line and byte processing, allow user to specify DMA, otherwise default to Interrupt
        state->hw_mode = (config->custom_hw_mode == TRACE_HW_MODE_DMA) ? TRACE_HW_MODE_DMA : TRACE_HW_MODE_INTERRUPT;
    }

    state->rx_busy = true;

    // Start hardware reception
    if (state->hw_mode == TRACE_HW_MODE_DMA) {
        if (state->process_mode == TRACE_RX_PROCESS_BUFFER) {
            // Use DMA Normal mode for a single buffer transfer
            if (HAL_UART_Receive_DMA(huart, state->buffer, state->buffer_size) != HAL_OK) {
                state->rx_busy = false;
                return TRACE_ERROR_HARDWARE_FAILURE;
            }
        } else {
            // Use DMA Circular with Idle Line detection for continuous streaming
            state->dma_last_pos = 0;
            if (HAL_UARTEx_ReceiveToIdle_DMA(huart, state->buffer, state->buffer_size) != HAL_OK) {
                state->rx_busy = false;
                return TRACE_ERROR_HARDWARE_FAILURE;
            }
            __HAL_DMA_DISABLE_IT(huart->hdmarx, DMA_IT_HT); // Disable half-transfer interrupt
        }
    } else { // INTERRUPT or POLLING
        // For interrupt mode, start by receiving a single byte. The ISR will re-arm it.
        if (HAL_UART_Receive_IT(huart, &state->buffer[state->rx_head], 1) != HAL_OK) {
            state->rx_busy = false;
            return TRACE_ERROR_HARDWARE_FAILURE;
        }
    }

    return TRACE_SUCCESS;
}

Trace_Error_t trace_StopRx(UART_HandleTypeDef *huart) {
    if (!huart) return TRACE_ERROR_INVALID_PARAMETER;
    RxState_t *state = get_rx_state(huart);
    if (!state) return TRACE_ERROR_UNSUPPORTED_INSTANCE;

    if (state->rx_busy) {
        HAL_UART_AbortReceive(huart);
        state->rx_busy = false;
    }
    return TRACE_SUCCESS;
}

uint16_t trace_Available(UART_HandleTypeDef *huart) {
    RxState_t *state = get_rx_state(huart);
    if (!state || !state->rx_busy) return 0;

    if (state->hw_mode == TRACE_HW_MODE_DMA) {
        uint16_t dma_head = state->buffer_size - __HAL_DMA_GET_COUNTER(huart->hdmarx);
        return (dma_head >= state->rx_tail) ? (dma_head - state->rx_tail) : (state->buffer_size - state->rx_tail + dma_head);
    } else { // Interrupt mode
        return (state->rx_head >= state->rx_tail) ? (state->rx_head - state->rx_tail) : (state->buffer_size - state->rx_tail + state->rx_head);
    }
}

void trace_FlushRx(UART_HandleTypeDef *huart) {
    RxState_t *state = get_rx_state(huart);
    if (!state) return;
    __disable_irq();
    state->rx_head = 0;
    state->rx_tail = 0;
    state->dma_last_pos = 0;
    line_assembly_idx = 0; // Also reset line assembly buffer index
    __enable_irq();
}

uint16_t trace_RxRead(UART_HandleTypeDef *huart, uint8_t *dest, uint16_t length) {
    if (!huart || !dest) return 0;
    RxState_t *state = get_rx_state(huart);
    if (!state) return 0;

    uint16_t available = trace_Available(huart);
    uint16_t to_read = (length < available) ? length : available;

    for (uint16_t i = 0; i < to_read; i++) {
        dest[i] = state->buffer[state->rx_tail];
        state->rx_tail = (state->rx_tail + 1) % state->buffer_size;
    }
    return to_read;
}

Trace_Error_t trace_PollData(UART_HandleTypeDef *huart) {
    // Note: Polling is generally not recommended for robust reception.
    // This function is provided for simple, non-critical use cases.
    if (!huart) return TRACE_ERROR_INVALID_PARAMETER;
    RxState_t *state = get_rx_state(huart);
    if (!state || !state->rx_busy) return TRACE_ERROR_NOT_READY;

    uint8_t byte;
    if (HAL_UART_Receive(huart, &byte, 1, 0) == HAL_OK) {
        uint16_t next_head = (state->rx_head + 1) % state->buffer_size;
        if (next_head == state->rx_tail) {
            if(state->error_cb) state->error_cb(huart, TRACE_ERROR_RX_BUFFER_OVERRUN);
            return TRACE_ERROR_RX_BUFFER_OVERRUN;
        }
        state->buffer[state->rx_head] = byte;
        state->rx_head = next_head;
        return TRACE_SUCCESS;
    }
    return TRACE_ERROR_NO_DATA;
}

/* ============================================================================ */
/* HAL CALLBACK HANDLERS                            */
/* ============================================================================ */

void trace_RxCpltCallback(UART_HandleTypeDef *huart) {
    RxState_t *state = get_rx_state(huart);
    if (!state || !state->rx_busy) return;

    if (state->hw_mode == TRACE_HW_MODE_DMA) {
        if (state->process_mode == TRACE_RX_PROCESS_BUFFER && state->buffer_cb) {
            state->buffer_cb(state->buffer, state->buffer_size);
            state->rx_busy = false;
        }
    }
    else if (state->hw_mode == TRACE_HW_MODE_INTERRUPT) {
        uint8_t received_byte = state->buffer[state->rx_head];
        uint16_t next_head = (state->rx_head + 1) % state->buffer_size;

        if (next_head == state->rx_tail) {
            // Software ring buffer overrun. The new byte will be dropped.
            if(state->error_cb) state->error_cb(huart, TRACE_ERROR_RX_BUFFER_OVERRUN);
            // By not advancing rx_head, we effectively drop the byte.
        } else {
            // Process the received byte because there is space in the buffer.
            if (state->process_mode == TRACE_RX_PROCESS_BYTE && state->byte_cb) {
                state->byte_cb(received_byte);
            }
            else if (state->process_mode == TRACE_RX_PROCESS_LINE && state->line_cb) {
                line_assembly_buffer[line_assembly_idx++] = received_byte;
                if (received_byte == state->terminator || line_assembly_idx >= sizeof(line_assembly_buffer)) {
                    state->line_cb(line_assembly_buffer, line_assembly_idx);
                    line_assembly_idx = 0;
                }
            }
            else if (state->process_mode == TRACE_RX_PROCESS_CUSTOM && state->custom_cb) {
            	state->custom_cb(huart, &received_byte, 1);
            }

            state->rx_head = next_head;
        }

        // Re-arm the interrupt to receive the next byte.
        if (HAL_UART_Receive_IT(huart, &state->buffer[state->rx_head], 1) != HAL_OK) {
             state->rx_busy = false;
             if(state->error_cb) state->error_cb(huart, TRACE_ERROR_HARDWARE_FAILURE);
        }
    }
}

void trace_RxEventCallback(UART_HandleTypeDef *huart, uint16_t size) {
    RxState_t *state = get_rx_state(huart);
    if (!state || !state->rx_busy) return;

    // The 'size' parameter from HAL_UARTEx_ReceiveToIdle_DMA indicates the end position.
    uint16_t current_pos = size;
    uint16_t old_pos = state->dma_last_pos;

    // Process all bytes received since the last event
    if (current_pos != old_pos) {
        const uint8_t *start_ptr;
        uint16_t len;

        if (current_pos > old_pos) {
            // Continuous block of data
            start_ptr = &state->buffer[old_pos];
            len = current_pos - old_pos;
        } else {
            // Data wrapped around the buffer, process the first part
            start_ptr = &state->buffer[old_pos];
            len = state->buffer_size - old_pos;
        }

        // Process the first (or only) block of data
        for(uint16_t i = 0; i < len; ++i) {
            uint8_t byte = start_ptr[i];
            if (state->process_mode == TRACE_RX_PROCESS_BYTE && state->byte_cb) {
                state->byte_cb(byte);
            }
            else if (state->process_mode == TRACE_RX_PROCESS_LINE && state->line_cb) {
                 line_assembly_buffer[line_assembly_idx++] = byte;
                 if(byte == state->terminator || line_assembly_idx >= sizeof(line_assembly_buffer)) {
                     state->line_cb(line_assembly_buffer, line_assembly_idx);
                     line_assembly_idx = 0;
                 }
            }
        }

        // If the data wrapped, process the second part
        if (current_pos < old_pos) {
            start_ptr = state->buffer;
            len = current_pos;
            for(uint16_t i = 0; i < len; ++i) {
                uint8_t byte = start_ptr[i];
                if (state->process_mode == TRACE_RX_PROCESS_BYTE && state->byte_cb) {
                    state->byte_cb(byte);
                }
                else if (state->process_mode == TRACE_RX_PROCESS_LINE && state->line_cb) {
                     line_assembly_buffer[line_assembly_idx++] = byte;
                     if(byte == state->terminator || line_assembly_idx >= sizeof(line_assembly_buffer)) {
                         state->line_cb(line_assembly_buffer, line_assembly_idx);
                         line_assembly_idx = 0;
                     }
                }
            }
        }
    }

    state->dma_last_pos = current_pos;
}

void trace_ErrorCallback(UART_HandleTypeDef *huart) {
    RxState_t *state = get_rx_state(huart);
    if (!state) return;

    if (huart->ErrorCode & HAL_UART_ERROR_ORE) {
        if(state->error_cb) state->error_cb(huart, TRACE_ERROR_HW_OVERRUN);
        // --- RECOVERY MECHANISM ---
        // A hardware overrun is critical. The UART receiver is disabled.
        // We must restart it to continue receiving data.
        recover_from_error(huart);
    }
    else if (huart->ErrorCode & (HAL_UART_ERROR_PE | HAL_UART_ERROR_FE | HAL_UART_ERROR_NE)) {
        if(state->error_cb) state->error_cb(huart, TRACE_ERROR_HARDWARE_FAILURE);
        // For other errors, we can also attempt a recovery.
        recover_from_error(huart);
    }
}

/**
 * @brief  Restarts UART reception after a critical error.
 * @note   This is the core recovery function. It re-uses the existing
 * configuration to restart the reception seamlessly.
 * @param  huart: Pointer to the UART handle.
 */
static void recover_from_error(UART_HandleTypeDef *huart) {
    RxState_t *state = get_rx_state(huart);
    if (!state || !state->rx_busy) return;

    // Abort any ongoing HAL operation to clear flags
    HAL_UART_AbortReceive(huart);

    // Flush software buffers to ensure no corrupt data is processed
    trace_FlushRx(huart);

    // Restart reception using the original mode
    if (state->hw_mode == TRACE_HW_MODE_DMA) {
        if (state->process_mode == TRACE_RX_PROCESS_BUFFER) {
            HAL_UART_Receive_DMA(huart, state->buffer, state->buffer_size);
        } else {
            HAL_UARTEx_ReceiveToIdle_DMA(huart, state->buffer, state->buffer_size);
        }
    } else { // Interrupt mode
        HAL_UART_Receive_IT(huart, &state->buffer[state->rx_head], 1);
    }
}

static TxScheduler_t* get_tx_scheduler(UART_HandleTypeDef *huart)
{
    uint8_t index = get_uart_index(huart);
    return (index != 0xFF) ? &tx_schedulers[index] : NULL;
}

static RxState_t* get_rx_state(UART_HandleTypeDef *huart)
{
    uint8_t index = get_uart_index(huart);
    return (index != 0xFF) ? &rx_states[index] : NULL;
}

static uint8_t get_uart_index(UART_HandleTypeDef *huart) {
    if (huart->Instance == USART1) return 0;
    if (huart->Instance == USART2) return 1;
    if (huart->Instance == LPUART1) return 2;
    return 0xFF; // Invalid index
}

