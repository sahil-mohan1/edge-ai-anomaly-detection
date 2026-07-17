/**
  ******************************************************************************
  * @file           : lora_e5_mini_bus.h
  * @brief          : Header for the Board Support Package BUS IO driver for the
  * Seeed Studio LoRa-E5 mini (STM32WL55JC).
  * @author         : Zero
  * @version        : 1.2.0
  * @date           : 2025-09-09
  * @brief          :
  *
  ******************************************************************************
  */

#ifndef __LORA_E5_MINI_BUS_H
#define __LORA_E5_MINI_BUS_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32wlxx_LoRa_E5_mini_conf.h"
#include "stm32wlxx_LoRa_E5_mini_errno.h"

/** @defgroup LoRa_E5_mini_BSP LoRa-E5 mini Board Support Package
  * @{
  */

/** @defgroup BSP_BUS_IO BUS IO
  * @brief    This section provides the BUS IO functions for the LoRa-E5 mini.
  * @{
  */

/* Exported Defines ----------------------------------------------------------*/

/** @defgroup BSP_BUS_IO_Exported_Defines Exported Defines
  * @{
  */
#ifndef USE_HAL_SPI_REGISTER_CALLBACKS
#define USE_HAL_SPI_REGISTER_CALLBACKS 0U
#endif
#ifndef USE_HAL_I2C_REGISTER_CALLBACKS
#define USE_HAL_I2C_REGISTER_CALLBACKS 0U
#endif

/* LoRa-E5 module Pinout (from datasheet V1.1, Table 1) */
/* I2C2 Pins: SCL @ PB15 (Pin 5), SDA @ PA15 (Pin 6) */
/* SPI2 Pins: SCK @ PB13 (Pin 24), MISO @ PB14 (Pin 26), MOSI @ PA10 (Pin 27) */

/* Bus SPI2 definitions */
#define BUS_SPI2_INSTANCE                       SPI2
#define BUS_SPI2_CLK_ENABLE()                   __HAL_RCC_SPI2_CLK_ENABLE()
#define BUS_SPI2_CLK_DISABLE()                  __HAL_RCC_SPI2_CLK_DISABLE()
#define BUS_SPI2_SCK_GPIO_PORT                  GPIOB
#define BUS_SPI2_SCK_GPIO_PIN                   GPIO_PIN_13
#define BUS_SPI2_SCK_GPIO_AF                    GPIO_AF5_SPI2
#define BUS_SPI2_SCK_GPIO_CLK_ENABLE()          __HAL_RCC_GPIOB_CLK_ENABLE()
#define BUS_SPI2_MISO_GPIO_PORT                 GPIOB
#define BUS_SPI2_MISO_GPIO_PIN                  GPIO_PIN_14
#define BUS_SPI2_MISO_GPIO_AF                   GPIO_AF5_SPI2
#define BUS_SPI2_MISO_GPIO_CLK_ENABLE()         __HAL_RCC_GPIOB_CLK_ENABLE()
#define BUS_SPI2_MOSI_GPIO_PORT                 GPIOA
#define BUS_SPI2_MOSI_GPIO_PIN                  GPIO_PIN_10
#define BUS_SPI2_MOSI_GPIO_AF                   GPIO_AF5_SPI2
#define BUS_SPI2_MOSI_GPIO_CLK_ENABLE()         __HAL_RCC_GPIOA_CLK_ENABLE()

/* Bus I2C2 definitions */
#define BUS_I2C2_INSTANCE                       I2C2
#define BUS_I2C2_CLK_ENABLE()					__HAL_RCC_I2C2_CLK_ENABLE()
#define BUS_I2C2_CLK_DISABLE()					__HAL_RCC_I2C2_CLK_DISABLE()
#define BUS_I2C2_SCL_GPIO_PORT                  GPIOB
#define BUS_I2C2_SCL_GPIO_PIN                   GPIO_PIN_15
#define BUS_I2C2_SCL_GPIO_AF                    GPIO_AF4_I2C2
#define BUS_I2C2_SCL_GPIO_CLK_ENABLE()          __HAL_RCC_GPIOB_CLK_ENABLE()
#define BUS_I2C2_SDA_GPIO_PORT                  GPIOA
#define BUS_I2C2_SDA_GPIO_PIN                   GPIO_PIN_15
#define BUS_I2C2_SDA_GPIO_AF                    GPIO_AF4_I2C2
#define BUS_I2C2_SDA_GPIO_CLK_ENABLE()          __HAL_RCC_GPIOA_CLK_ENABLE()
#ifndef BUS_I2C2_POLL_TIMEOUT
#define BUS_I2C2_POLL_TIMEOUT                   0x1000U
#endif
/**
  * @}
  */

/* Exported Types ------------------------------------------------------------*/

/** @defgroup BSP_BUS_IO_Exported_Types Exported Types
  * @{
  */
#if (USE_HAL_I2C_REGISTER_CALLBACKS == 1U)
typedef struct {
  pI2C_CallbackTypeDef  pMspInitCb;
  pI2C_CallbackTypeDef  pMspDeInitCb;
} BSP_I2C_Cb_t;
#endif

#if (USE_HAL_SPI_REGISTER_CALLBACKS == 1)
typedef struct {
  pSPI_CallbackTypeDef  pMspSpiInitCb;
  pSPI_CallbackTypeDef  pMspSpiDeInitCb;
} BSP_SPI_Cb_t;
#endif
/**
  * @}
  */

/* Exported Variables --------------------------------------------------------*/
extern I2C_HandleTypeDef hi2c2;
extern SPI_HandleTypeDef hspi2;

/* Exported Functions ------------------------------------------------------- */

/** @defgroup BSP_I2C_Functions I2C Functions
  * @{
  */
int32_t BSP_I2C2_Init(void);
int32_t BSP_I2C2_DeInit(void);
int32_t BSP_I2C2_IsReady(uint16_t DevAddr, uint32_t Trials);
int32_t BSP_I2C2_WriteReg(uint16_t Addr, uint16_t Reg, uint8_t *pData, uint16_t Length);
int32_t BSP_I2C2_ReadReg(uint16_t Addr, uint16_t Reg, uint8_t *pData, uint16_t Length);
int32_t BSP_I2C2_WriteReg16(uint16_t Addr, uint16_t Reg, uint8_t *pData, uint16_t Length);
int32_t BSP_I2C2_ReadReg16(uint16_t Addr, uint16_t Reg, uint8_t *pData, uint16_t Length);
int32_t BSP_I2C2_Send(uint16_t DevAddr, uint8_t *pData, uint16_t Length);
int32_t BSP_I2C2_Recv(uint16_t DevAddr, uint8_t *pData, uint16_t Length);
#if (USE_HAL_I2C_REGISTER_CALLBACKS == 1U)
int32_t BSP_I2C2_RegisterDefaultMspCallbacks (void);
int32_t BSP_I2C2_RegisterMspCallbacks (BSP_I2C_Cb_t *Callbacks);
#endif
/**
  * @}
  */

/** @defgroup BSP_SPI_Functions SPI Functions
  * @{
  */
int32_t BSP_SPI2_Init(uint32_t baudrate_prescaler);
int32_t BSP_SPI2_DeInit(void);
int32_t BSP_SPI2_SetBaudratePrescaler(uint32_t prescaler);
int32_t BSP_SPI2_Send(uint8_t *pData, uint16_t len);
int32_t BSP_SPI2_Recv(uint8_t *pData, uint16_t len);
int32_t BSP_SPI2_SendRecv(uint8_t *pTxData, uint8_t *pRxData, uint16_t len);
#if (USE_HAL_SPI_REGISTER_CALLBACKS == 1)
int32_t BSP_SPI2_RegisterDefaultMspCallbacks(void);
int32_t BSP_SPI2_RegisterMspCallbacks(BSP_SPI_Cb_t *Callbacks);
#endif
/**
  * @}
  */

/** @defgroup BSP_Common_Functions Common Functions
  * @{
  */
int32_t BSP_GetTick(void);

void BSP_DelayUs(uint32_t microseconds);

HAL_StatusTypeDef MX_TIM16_Init(void);

/**
  * @}
  */

/**
  * @}
  */

/**
  * @}
  */

#ifdef __cplusplus
}
#endif

#endif /* __LORA_E5_MINI_BUS_H */

