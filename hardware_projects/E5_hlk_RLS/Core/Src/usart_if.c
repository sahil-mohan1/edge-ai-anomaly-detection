/**
  ******************************************************************************
  * @file    usart_if.c
  * @author  MCD Application Team
  * @brief   Configuration of UART MX driver interface for hyperterminal communication
  ******************************************************************************
  * @attention
  *
  * <h2><center>&copy; Copyright (c) 2020 STMicroelectronics.
  * All rights reserved.</center></h2>
  *
  * This software component is licensed by ST under Ultimate Liberty license
  * SLA0044, the "License"; You may not use this file except in compliance with
  * the License. You may obtain a copy of the License at:
  *                             www.st.com/SLA0044
  *
  ******************************************************************************
  */
/* Includes ------------------------------------------------------------------*/
#include "usart_if.h"
#include "trace.h"
#include "trace_conf.h"

/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* External variables ---------------------------------------------------------*/
/**
  * @brief DMA handle
  */
extern DMA_HandleTypeDef hdma_usart1_tx;

/**
  * @brief UART handle
  */
extern UART_HandleTypeDef huart1;

/**
  * @brief buffer to receive 1 character
  */
uint8_t charRx;

/* USER CODE BEGIN EV */

/* USER CODE END EV */

/* Private typedef -----------------------------------------------------------*/
#if !defined(USE_ADV_TRACE) || (USE_ADV_TRACE == 0)
/**
  * @brief Trace driver callbacks handler
  */
const UTIL_ADV_TRACE_Driver_s UTIL_TraceDriver =
{
  vcom_Init,
  vcom_DeInit,
  vcom_ReceiveInit,
  vcom_Trace_DMA,
};
#endif
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
/**
  * @brief  TX complete callback
  * @return none
  */
static void (*TxCpltCallback)(void *);
/**
  * @brief  RX complete callback
  * @param  rxChar ptr of chars buffer sent by user
  * @param  size buffer size
  * @param  error errorcode
  * @return none
  */
static void (*RxCpltCallback)(uint8_t *rxChar, uint16_t size, uint8_t error);

static uint8_t VcomRxBuffer[1];
static void Vcom_TxHook(UART_HandleTypeDef *huart, Transmission_Owner_t owner);
static void Vcom_RxByteCallback(uint8_t byte);
/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/

/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Exported functions --------------------------------------------------------*/

UTIL_ADV_TRACE_Status_t vcom_Init(void (*cb)(void *))
{
  /* USER CODE BEGIN vcom_Init_1 */

  /* USER CODE END vcom_Init_1 */
  TxCpltCallback = cb;
//  MX_DMA_Init();
//  MX_USART1_UART_Init();
  trace_RegisterTxCpltHook(Vcom_TxHook);
//  LL_EXTI_EnableIT_0_31(LL_EXTI_LINE_27);
  return UTIL_ADV_TRACE_OK;
  /* USER CODE BEGIN vcom_Init_2 */

  /* USER CODE END vcom_Init_2 */
}

UTIL_ADV_TRACE_Status_t vcom_DeInit(void)
{
  /* USER CODE BEGIN vcom_DeInit_1 */

  /* USER CODE END vcom_DeInit_1 */
  /* ##-1- Reset peripherals ################################################## */
	__HAL_RCC_LPUART1_FORCE_RESET();
  __HAL_RCC_LPUART1_RELEASE_RESET();

  /* ##-2- MspDeInit ################################################## */
//  HAL_UART_MspDeInit(&huart1);
//
//  /* ##-3- Disable the NVIC for DMA ########################################### */
//  /* temporary while waiting CR 50840: MX implementation of  MX_DMA_DeInit() */
//  /* For the time being user should change manually the channel according to the MX settings */
//  /* USER CODE BEGIN 1 */
//  HAL_NVIC_DisableIRQ(DMA1_Channel5_IRQn);
  trace_Deinit(TRACE_UART_HANDLE);
  return UTIL_ADV_TRACE_OK;
  /* USER CODE END 1 */
  /* USER CODE BEGIN vcom_DeInit_2 */

  /* USER CODE END vcom_DeInit_2 */
}

void vcom_Trace(uint8_t *p_data, uint16_t size)
{
  /* USER CODE BEGIN vcom_Trace_1 */

  /* USER CODE END vcom_Trace_1 */
//  HAL_UART_Transmit(&huart1, p_data, size, 1000);
    trace_SetTxMode(TRACE_UART_HANDLE, TRACE_TX_MODE_POLLING);
    trace_WriteRaw(TRACE_UART_HANDLE, p_data, size, OWNER_VCOM);
  /* USER CODE BEGIN vcom_Trace_2 */

  /* USER CODE END vcom_Trace_2 */
}

UTIL_ADV_TRACE_Status_t vcom_Trace_DMA(uint8_t *p_data, uint16_t size)
{
  /* USER CODE BEGIN vcom_Trace_DMA_1 */

  /* USER CODE END vcom_Trace_DMA_1 */
//  HAL_UART_Transmit_DMA(&huart1, p_data, size);
//  return UTIL_ADV_TRACE_OK;
    trace_SetTxMode(TRACE_UART_HANDLE, TRACE_TX_MODE_DMA);
    if (trace_WriteRaw(TRACE_UART_HANDLE, p_data, size, OWNER_VCOM) == TRACE_SUCCESS) {
        return UTIL_ADV_TRACE_OK;
    }
    return UTIL_ADV_TRACE_MEM_FULL;
  /* USER CODE BEGIN vcom_Trace_DMA_2 */

  /* USER CODE END vcom_Trace_DMA_2 */
}

UTIL_ADV_TRACE_Status_t vcom_ReceiveInit(void (*RxCb)(uint8_t *rxChar, uint16_t size, uint8_t error))
{
  /* USER CODE BEGIN vcom_ReceiveInit_1 */

  /* USER CODE END vcom_ReceiveInit_1 */
//  UART_WakeUpTypeDef WakeUpSelection;

  /*record call back*/
  RxCpltCallback = RxCb;

//  /*Set wakeUp event on start bit*/
//  WakeUpSelection.WakeUpEvent = UART_WAKEUP_ON_STARTBIT;
//
//  HAL_UARTEx_StopModeWakeUpSourceConfig(&huart1, WakeUpSelection);
//
//  /* Make sure that no UART transfer is on-going */
//  while (__HAL_UART_GET_FLAG(&huart1, USART_ISR_BUSY) == SET);
//
//  /* Make sure that UART is ready to receive)   */
//  while (__HAL_UART_GET_FLAG(&huart1, USART_ISR_REACK) == RESET);
//
//  /* Enable USART interrupt */
//  __HAL_UART_ENABLE_IT(&huart1, UART_IT_WUF);
//
//  /*Enable wakeup from stop mode*/
//  HAL_UARTEx_EnableStopMode(&huart1);
//
//  /*Start LPUART receive on IT*/
//  HAL_UART_Receive_IT(&huart1, &charRx, 1);
//
//  return UTIL_ADV_TRACE_OK;
  /* USER CODE BEGIN vcom_ReceiveInit_2 */
  Trace_RxConfig_t rx_config = {
      .buffer = VcomRxBuffer,
      .buffer_size = sizeof(VcomRxBuffer),
      .process_mode = TRACE_RX_PROCESS_BYTE,
      .custom_hw_mode = TRACE_HW_MODE_INTERRUPT,
      .byte_cb = Vcom_RxByteCallback,
      .error_cb = NULL,
      .enable_wakeup = true /* NEW: Request wakeup from stop mode feature */
  };

  if (trace_StartRx(TRACE_UART_HANDLE, &rx_config) == TRACE_SUCCESS) {
      return UTIL_ADV_TRACE_OK;
  }
  return UTIL_ADV_TRACE_HW_ERROR;
  /* USER CODE END vcom_ReceiveInit_2 */
}

void vcom_Resume(void)
{
  /* USER CODE BEGIN vcom_Resume_1 */

  /* USER CODE END vcom_Resume_1 */
  /*to re-enable lost UART settings*/
//  if (HAL_UART_Init(&huart1) != HAL_OK)
//  {
//    Error_Handler();
//  }
//
//  /*to re-enable lost DMA settings*/
//  if (HAL_DMA_Init(&hdma_usart1_tx) != HAL_OK)
//  {
//    Error_Handler();
//  }

	trace_Resume(TRACE_UART_HANDLE);
  /* USER CODE BEGIN vcom_Resume_2 */

  /* USER CODE END vcom_Resume_2 */
}
static void Vcom_TxHook(UART_HandleTypeDef *huart, Transmission_Owner_t owner) {
    if (owner == OWNER_VCOM && TxCpltCallback != NULL) {
        TxCpltCallback(NULL);
    }
}

static void Vcom_RxByteCallback(uint8_t byte) {
    if (RxCpltCallback != NULL) {
        // The VCOM framework expects a pointer, size, and error code.
        RxCpltCallback(&byte, 1, 0);
    }
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
  /* USER CODE BEGIN HAL_UART_TxCpltCallback_1 */
	  if (huart->Instance == USART1 || huart->Instance == USART2 || huart->Instance == LPUART1)
	  {
	trace_TxCpltCallback(huart);
	  }
  /* USER CODE END HAL_UART_TxCpltCallback_1 */

  /* USER CODE BEGIN HAL_UART_TxCpltCallback_2 */

  /* USER CODE END HAL_UART_TxCpltCallback_2 */
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
  /* USER CODE BEGIN HAL_UART_RxCpltCallback_1 */

  /* USER CODE END HAL_UART_RxCpltCallback_1 */

//  if ((NULL != RxCpltCallback) && (HAL_UART_ERROR_NONE == huart1->ErrorCode))
//  {
//    RxCpltCallback(&charRx, 1, 0);
//  }
//  HAL_UART_Receive_IT(huart1, &charRx, 1);

	  if (huart->Instance == USART1 || huart->Instance == USART2 || huart->Instance == LPUART1)
	  {
	trace_RxCpltCallback(huart);
	  }
  /* USER CODE BEGIN HAL_UART_RxCpltCallback_2 */

  /* USER CODE END HAL_UART_RxCpltCallback_2 */
}

/* USER CODE BEGIN EF */
void HAL_UART_RxHalfCpltCallback(UART_HandleTypeDef *huart) {
	  if (huart->Instance == USART1 || huart->Instance == USART2 || huart->Instance == LPUART1)
	  {
	trace_RxCpltCallback(huart);
	  }
}

void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t size)
{
  if (huart->Instance == USART1 || huart->Instance == USART2 || huart->Instance == LPUART1)
  {
    trace_RxEventCallback(huart, size);
  }
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
  if (huart->Instance == USART1 || huart->Instance == USART2 || huart->Instance == LPUART1)
  {
    trace_ErrorCallback(huart);
  }
}
/* USER CODE END EF */

/* Private Functions Definition -----------------------------------------------*/

/* USER CODE BEGIN PrFD */

/* USER CODE END PrFD */

/************************ (C) COPYRIGHT STMicroelectronics *****END OF FILE****/
