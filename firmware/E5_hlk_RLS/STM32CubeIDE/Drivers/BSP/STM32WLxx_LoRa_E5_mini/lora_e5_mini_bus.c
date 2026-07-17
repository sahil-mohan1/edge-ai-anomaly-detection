/**
  ******************************************************************************
  * @file           : lora_e5_mini_bus.c
  * @brief          : Source file for the BSP BUS IO driver for LoRa-E5 mini.
  ******************************************************************************
  */
#include "lora_e5_mini_bus.h"
#include "main.h"

#define TIMEOUT_DURATION 1000

SPI_HandleTypeDef hspi2;
I2C_HandleTypeDef hi2c2;
TIM_HandleTypeDef htim16;

#if (USE_HAL_SPI_REGISTER_CALLBACKS == 1)
static uint32_t IsSPI2MspCbValid = 0;
#endif
#if (USE_HAL_I2C_REGISTER_CALLBACKS == 1U)
static uint32_t IsI2C2MspCbValid = 0;
#endif

static void SPI2_MspInit(SPI_HandleTypeDef *spiHandle);
static void SPI2_MspDeInit(SPI_HandleTypeDef *spiHandle);
static __attribute__((unused)) uint32_t SPI_GetPrescaler(uint32_t clock_src_hz, uint32_t baudrate_mbps);
static void I2C2_MspInit(I2C_HandleTypeDef *i2cHandle);
static void I2C2_MspDeInit(I2C_HandleTypeDef *i2cHandle);

__weak HAL_StatusTypeDef MX_SPI2_Init(SPI_HandleTypeDef* hspi, uint32_t baudrate_prescaler);
__weak HAL_StatusTypeDef MX_I2C2_Init(I2C_HandleTypeDef* hi2c);

/******************************* SPI2 Bus Functions ***************************/
int32_t BSP_SPI2_Init(uint32_t baudrate_prescaler) {
  hspi2.Instance  = BUS_SPI2_INSTANCE;
  if (HAL_SPI_GetState(&hspi2) == HAL_SPI_STATE_RESET) {
#if (USE_HAL_SPI_REGISTER_CALLBACKS == 0)
    SPI2_MspInit(&hspi2);
#else
    if (IsSPI2MspCbValid == 0U) {
      if (BSP_SPI2_RegisterDefaultMspCallbacks() != BSP_ERROR_NONE) return BSP_ERROR_MSP_FAILURE;
    }
#endif
    if (MX_SPI2_Init(&hspi2, baudrate_prescaler) != HAL_OK) return BSP_ERROR_BUS_FAILURE;
  }
  return BSP_ERROR_NONE;
}

int32_t BSP_SPI2_DeInit(void) {
#if (USE_HAL_SPI_REGISTER_CALLBACKS == 0)
  SPI2_MspDeInit(&hspi2);
#endif
  if (HAL_SPI_DeInit(&hspi2) != HAL_OK) return BSP_ERROR_BUS_FAILURE;
  return BSP_ERROR_NONE;
}

int32_t BSP_SPI2_Send(uint8_t *pData, uint16_t len) {
  if(HAL_SPI_Transmit(&hspi2, pData, len, TIMEOUT_DURATION) != HAL_OK) return BSP_ERROR_BUS_FAILURE;
  return len;
}

int32_t  BSP_SPI2_Recv(uint8_t *pData, uint16_t len) {
  if(HAL_SPI_Receive(&hspi2, pData, len, TIMEOUT_DURATION) != HAL_OK) return BSP_ERROR_BUS_FAILURE;
  return len;
}

int32_t BSP_SPI2_SendRecv(uint8_t *pTxData, uint8_t *pRxData, uint16_t len) {
  if(HAL_SPI_TransmitReceive(&hspi2, pTxData, pRxData, len, TIMEOUT_DURATION) != HAL_OK) return BSP_ERROR_BUS_FAILURE;
  return len;
}

#if (USE_HAL_SPI_REGISTER_CALLBACKS == 1)
int32_t BSP_SPI2_RegisterDefaultMspCallbacks(void) {
  __HAL_SPI_RESET_HANDLE_STATE(&hspi2);
  if (HAL_SPI_RegisterCallback(&hspi2, HAL_SPI_MSPINIT_CB_ID, SPI2_MspInit) != HAL_OK) return BSP_ERROR_PERIPH_FAILURE;
  if (HAL_SPI_RegisterCallback(&hspi2, HAL_SPI_MSPDEINIT_CB_ID, SPI2_MspDeInit) != HAL_OK) return BSP_ERROR_PERIPH_FAILURE;
  IsSPI2MspCbValid = 1;
  return BSP_ERROR_NONE;
}

int32_t BSP_SPI2_RegisterMspCallbacks(BSP_SPI_Cb_t *Callbacks) {
  __HAL_SPI_RESET_HANDLE_STATE(&hspi2);
  if (HAL_SPI_RegisterCallback(&hspi2, HAL_SPI_MSPINIT_CB_ID, Callbacks->pMspSpiInitCb) != HAL_OK) return BSP_ERROR_PERIPH_FAILURE;
  if (HAL_SPI_RegisterCallback(&hspi2, HAL_SPI_MSPDEINIT_CB_ID, Callbacks->pMspSpiDeInitCb) != HAL_OK) return BSP_ERROR_PERIPH_FAILURE;
  IsSPI2MspCbValid = 1;
  return BSP_ERROR_NONE;
}
#endif

/******************************* I2C2 Bus Functions ***************************/
int32_t BSP_I2C2_Init(void) {
  hi2c2.Instance = BUS_I2C2_INSTANCE;
  if (HAL_I2C_GetState(&hi2c2) == HAL_I2C_STATE_RESET) {
#if (USE_HAL_I2C_REGISTER_CALLBACKS == 0U)
    I2C2_MspInit(&hi2c2);
#else
    if (IsI2C2MspCbValid == 0U) {
      if (BSP_I2C2_RegisterDefaultMspCallbacks() != BSP_ERROR_NONE) return BSP_ERROR_MSP_FAILURE;
    }
#endif
    if(MX_I2C2_Init(&hi2c2) != HAL_OK) return BSP_ERROR_BUS_FAILURE;
  }
  return BSP_ERROR_NONE;
}

int32_t BSP_I2C2_DeInit(void) {
#if (USE_HAL_I2C_REGISTER_CALLBACKS == 0U)
  I2C2_MspDeInit(&hi2c2);
#endif
  if (HAL_I2C_DeInit(&hi2c2) != HAL_OK) return BSP_ERROR_BUS_FAILURE;
  return BSP_ERROR_NONE;
}

int32_t BSP_I2C2_IsReady(uint16_t DevAddr, uint32_t Trials) {
    if (HAL_I2C_IsDeviceReady(&hi2c2, DevAddr, Trials, TIMEOUT_DURATION) != HAL_OK) {
        return BSP_ERROR_BUSY;
    }
    return BSP_ERROR_NONE;
}

int32_t BSP_I2C2_WriteReg(uint16_t DevAddr, uint16_t Reg, uint8_t *pData, uint16_t Length) {
  if (HAL_I2C_Mem_Write(&hi2c2, DevAddr, Reg, I2C_MEMADD_SIZE_8BIT, pData, Length, BUS_I2C2_POLL_TIMEOUT) != HAL_OK) {
    if (HAL_I2C_GetError(&hi2c2) == HAL_I2C_ERROR_AF) return BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    return BSP_ERROR_PERIPH_FAILURE;
  }
  return BSP_ERROR_NONE;
}

int32_t BSP_I2C2_ReadReg(uint16_t DevAddr, uint16_t Reg, uint8_t *pData, uint16_t Length) {
  if (HAL_I2C_Mem_Read(&hi2c2, DevAddr, Reg, I2C_MEMADD_SIZE_8BIT, pData, Length, BUS_I2C2_POLL_TIMEOUT) != HAL_OK) {
    if (HAL_I2C_GetError(&hi2c2) == HAL_I2C_ERROR_AF) return BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    return BSP_ERROR_PERIPH_FAILURE;
  }
  return BSP_ERROR_NONE;
}


int32_t BSP_I2C2_WriteReg16(uint16_t DevAddr, uint16_t Reg, uint8_t *pData, uint16_t Length) {
  if (HAL_I2C_Mem_Write(&hi2c2, DevAddr, Reg, I2C_MEMADD_SIZE_16BIT, pData, Length, BUS_I2C2_POLL_TIMEOUT) != HAL_OK) {
    if (HAL_I2C_GetError(&hi2c2) == HAL_I2C_ERROR_AF) return BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    return BSP_ERROR_PERIPH_FAILURE;
  }
  return BSP_ERROR_NONE;
}

int32_t BSP_I2C2_ReadReg16(uint16_t DevAddr, uint16_t Reg, uint8_t *pData, uint16_t Length) {
  if (HAL_I2C_Mem_Read(&hi2c2, DevAddr, Reg, I2C_MEMADD_SIZE_16BIT, pData, Length, BUS_I2C2_POLL_TIMEOUT) != HAL_OK) {
    if (HAL_I2C_GetError(&hi2c2) == HAL_I2C_ERROR_AF) return BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE;
    return BSP_ERROR_PERIPH_FAILURE;
  }
  return BSP_ERROR_NONE;
}

#if (USE_HAL_I2C_REGISTER_CALLBACKS == 1U)
int32_t BSP_I2C2_RegisterDefaultMspCallbacks(void) {
  __HAL_I2C_RESET_HANDLE_STATE(&hi2c2);
  if (HAL_I2C_RegisterCallback(&hi2c2, HAL_I2C_MSPINIT_CB_ID, I2C2_MspInit) != HAL_OK) return BSP_ERROR_PERIPH_FAILURE;
  if (HAL_I2C_RegisterCallback(&hi2c2, HAL_I2C_MSPDEINIT_CB_ID, I2C2_MspDeInit) != HAL_OK) return BSP_ERROR_PERIPH_FAILURE;
  IsI2C2MspCbValid = 1;
  return BSP_ERROR_NONE;
}

int32_t BSP_I2C2_RegisterMspCallbacks(BSP_I2C_Cb_t *Callbacks) {
  __HAL_I2C_RESET_HANDLE_STATE(&hi2c2);
  if (HAL_I2C_RegisterCallback(&hi2c2, HAL_I2C_MSPINIT_CB_ID, Callbacks->pMspInitCb) != HAL_OK) return BSP_ERROR_PERIPH_FAILURE;
  if (HAL_I2C_RegisterCallback(&hi2c2, HAL_I2C_MSPDEINIT_CB_ID, Callbacks->pMspDeInitCb) != HAL_OK) return BSP_ERROR_PERIPH_FAILURE;
  IsI2C2MspCbValid = 1;
  return BSP_ERROR_NONE;
}
#endif

/***************************** Common BSP Functions ***************************/
int32_t BSP_GetTick(void) {
  return HAL_GetTick();
}

/**
 * @brief Provides a delay in microseconds.
 * @param microseconds Delay duration in microseconds.
 */
void BSP_DelayUs(uint32_t microseconds)
{
    /* Check if timer is already initialized */
    if (htim16.State == HAL_TIM_STATE_RESET)
    {
        if (MX_TIM16_Init() != HAL_OK)
        {
            /* If timer init fails, we cannot provide an accurate delay. */
            /* This could be replaced with a less accurate HAL_Delay fallback if needed. */
            return;
        }
    }

    __HAL_TIM_SET_COUNTER(&htim16, 0); // Reset counter
    HAL_TIM_Base_Start(&htim16);
    while(__HAL_TIM_GET_COUNTER(&htim16) < microseconds);
    HAL_TIM_Base_Stop(&htim16);
}


/************************** Weak Implementation of Init ***********************/
__weak HAL_StatusTypeDef MX_SPI2_Init(SPI_HandleTypeDef* hspi, uint32_t baudrate_prescaler) {
  hspi->Instance = BUS_SPI2_INSTANCE;
  hspi->Init.Mode = SPI_MODE_MASTER;
  hspi->Init.Direction = SPI_DIRECTION_2LINES;
  hspi->Init.DataSize = SPI_DATASIZE_8BIT;
  hspi->Init.CLKPolarity = SPI_POLARITY_LOW;
  hspi->Init.CLKPhase = SPI_PHASE_1EDGE;
  hspi->Init.NSS = SPI_NSS_SOFT;
  hspi->Init.BaudRatePrescaler = baudrate_prescaler;
  hspi->Init.FirstBit = SPI_FIRSTBIT_MSB;
  hspi->Init.TIMode = SPI_TIMODE_DISABLE;
  hspi->Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
  hspi->Init.CRCPolynomial = 7;
  hspi->Init.CRCLength = SPI_CRC_LENGTH_DATASIZE;
  hspi->Init.NSSPMode = SPI_NSS_PULSE_ENABLE;
  if (HAL_SPI_Init(hspi) != HAL_OK) return HAL_ERROR;
  return HAL_OK;
}

__weak HAL_StatusTypeDef MX_I2C2_Init(I2C_HandleTypeDef* hi2c) {
  HAL_StatusTypeDef ret = HAL_OK;
  hi2c->Instance = I2C2;
  hi2c->Init.Timing = 0x00100D14; //Standard Mode
  hi2c->Init.OwnAddress1 = 0;
  hi2c->Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hi2c->Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c->Init.OwnAddress2 = 0;
  hi2c->Init.OwnAddress2Masks = I2C_OA2_NOMASK;
  hi2c->Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c->Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
  if (HAL_I2C_Init(hi2c) != HAL_OK) {
    ret = HAL_ERROR;
  }
  // Add Analog and Digital Filter config from working driver
  if (HAL_I2CEx_ConfigAnalogFilter(hi2c, I2C_ANALOGFILTER_ENABLE) != HAL_OK) {
    ret = HAL_ERROR;
  }
  if (HAL_I2CEx_ConfigDigitalFilter(hi2c, 0) != HAL_OK) {
    ret = HAL_ERROR;
  }
  return (ret);
}

/********************************** MSP Callbacks *****************************/
static void SPI2_MspInit(SPI_HandleTypeDef* spiHandle) {
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  BUS_SPI2_CLK_ENABLE();
  BUS_SPI2_SCK_GPIO_CLK_ENABLE();
  BUS_SPI2_MISO_GPIO_CLK_ENABLE();
  BUS_SPI2_MOSI_GPIO_CLK_ENABLE();
  GPIO_InitStruct.Pin = BUS_SPI2_SCK_GPIO_PIN;
  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStruct.Alternate = BUS_SPI2_SCK_GPIO_AF;
  HAL_GPIO_Init(BUS_SPI2_SCK_GPIO_PORT, &GPIO_InitStruct);
  GPIO_InitStruct.Pin = BUS_SPI2_MISO_GPIO_PIN;
  GPIO_InitStruct.Alternate = BUS_SPI2_MISO_GPIO_AF;
  HAL_GPIO_Init(BUS_SPI2_MISO_GPIO_PORT, &GPIO_InitStruct);
  GPIO_InitStruct.Pin = BUS_SPI2_MOSI_GPIO_PIN;
  GPIO_InitStruct.Alternate = BUS_SPI2_MOSI_GPIO_AF;
  HAL_GPIO_Init(BUS_SPI2_MOSI_GPIO_PORT, &GPIO_InitStruct);
}

static void SPI2_MspDeInit(SPI_HandleTypeDef* spiHandle) {
  BUS_SPI2_CLK_DISABLE();
  HAL_GPIO_DeInit(BUS_SPI2_SCK_GPIO_PORT, BUS_SPI2_SCK_GPIO_PIN);
  HAL_GPIO_DeInit(BUS_SPI2_MISO_GPIO_PORT, BUS_SPI2_MISO_GPIO_PIN);
  HAL_GPIO_DeInit(BUS_SPI2_MOSI_GPIO_PORT, BUS_SPI2_MOSI_GPIO_PIN);
}

static void I2C2_MspInit(I2C_HandleTypeDef* i2cHandle) {
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  // Add peripheral clock config from working driver
  RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};
  PeriphClkInitStruct.PeriphClockSelection = RCC_PERIPHCLK_I2C2;
  PeriphClkInitStruct.I2c2ClockSelection = RCC_I2C2CLKSOURCE_PCLK1;
  HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct);

  BUS_I2C2_SCL_GPIO_CLK_ENABLE();
  BUS_I2C2_SDA_GPIO_CLK_ENABLE();
  BUS_I2C2_CLK_ENABLE();
  GPIO_InitStruct.Pin = BUS_I2C2_SCL_GPIO_PIN;
  GPIO_InitStruct.Mode = GPIO_MODE_AF_OD;
  GPIO_InitStruct.Pull = GPIO_PULLUP;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStruct.Alternate = BUS_I2C2_SCL_GPIO_AF;
  HAL_GPIO_Init(BUS_I2C2_SCL_GPIO_PORT, &GPIO_InitStruct);
  GPIO_InitStruct.Pin = BUS_I2C2_SDA_GPIO_PIN;
  GPIO_InitStruct.Alternate = BUS_I2C2_SDA_GPIO_AF;
  HAL_GPIO_Init(BUS_I2C2_SDA_GPIO_PORT, &GPIO_InitStruct);
}

static void I2C2_MspDeInit(I2C_HandleTypeDef* i2cHandle) {
  BUS_I2C2_CLK_DISABLE();
  HAL_GPIO_DeInit(BUS_I2C2_SCL_GPIO_PORT, BUS_I2C2_SCL_GPIO_PIN);
  HAL_GPIO_DeInit(BUS_I2C2_SDA_GPIO_PORT, BUS_I2C2_SDA_GPIO_PIN);
}

static __attribute__((unused)) uint32_t SPI_GetPrescaler(uint32_t clock_src_hz, uint32_t baudrate_mbps) {
  uint32_t divisor = 0;
  uint32_t spi_clk = clock_src_hz;
  uint32_t presc = 0;
  static const uint32_t baudrate[] = {
    SPI_BAUDRATEPRESCALER_2, SPI_BAUDRATEPRESCALER_4, SPI_BAUDRATEPRESCALER_8,
    SPI_BAUDRATEPRESCALER_16, SPI_BAUDRATEPRESCALER_32, SPI_BAUDRATEPRESCALER_64,
    SPI_BAUDRATEPRESCALER_128, SPI_BAUDRATEPRESCALER_256,
  };
  while (spi_clk > baudrate_mbps) {
    presc = baudrate[divisor];
    if (++divisor > 7) break;
    spi_clk = (spi_clk >> 1);
  }
  return presc;
}

/**
  * @brief TIM16 Initialization Function
  * @param None
  * @retval HAL_StatusTypeDef
  */
HAL_StatusTypeDef MX_TIM16_Init(void)
{
  htim16.Instance = TIM16;
  // Prescaler calculation ensures a 1MHz (1us) timer clock
  htim16.Init.Prescaler = (HAL_RCC_GetPCLK2Freq() / 1000000) - 1;
  htim16.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim16.Init.Period = 65535; // Max period
  htim16.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim16.Init.RepetitionCounter = 0;
  htim16.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim16) != HAL_OK)
  {
    return HAL_ERROR;
  }
  return HAL_OK;
}

/**
* @brief TIM_Base MSP Initialization
* This function configures the hardware resources needed for TIM16:
* clock source.
* @param htim_base: TIM_Base handle pointer
* @retval None
*/
void HAL_TIM_Base_MspInit(TIM_HandleTypeDef* htim_base)
{
  if(htim_base->Instance==TIM16)
  {
    /* TIM16 clock enable */
    __HAL_RCC_TIM16_CLK_ENABLE();
  }
}

/**
* @brief TIM_Base MSP De-Initialization
* This function freeze the hardware resources needed for TIM16:
* clock source.
* @param htim_base: TIM_Base handle pointer
* @retval None
*/
void HAL_TIM_Base_MspDeInit(TIM_HandleTypeDef* htim_base)
{
  if(htim_base->Instance==TIM16)
  {
    /* TIM16 clock disable */
    __HAL_RCC_TIM16_CLK_DISABLE();
  }
}

