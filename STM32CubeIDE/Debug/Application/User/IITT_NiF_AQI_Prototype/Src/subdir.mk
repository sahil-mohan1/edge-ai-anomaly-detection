################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (13.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../Application/User/IITT_NiF_AQI_Prototype/Src/AQI_Prototype_v2.c \
../Application/User/IITT_NiF_AQI_Prototype/Src/aqi_datalogger.c 

OBJS += \
./Application/User/IITT_NiF_AQI_Prototype/Src/AQI_Prototype_v2.o \
./Application/User/IITT_NiF_AQI_Prototype/Src/aqi_datalogger.o 

C_DEPS += \
./Application/User/IITT_NiF_AQI_Prototype/Src/AQI_Prototype_v2.d \
./Application/User/IITT_NiF_AQI_Prototype/Src/aqi_datalogger.d 


# Each subdirectory must supply rules for building sources it contributes
Application/User/IITT_NiF_AQI_Prototype/Src/%.o Application/User/IITT_NiF_AQI_Prototype/Src/%.su Application/User/IITT_NiF_AQI_Prototype/Src/%.cyclo: ../Application/User/IITT_NiF_AQI_Prototype/Src/%.c Application/User/IITT_NiF_AQI_Prototype/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DCORE_CM4 -DSTM32WLE5xx -DUSE_HAL_DRIVER -c -I../../Core/Inc -I../../LoRaWAN/App -I../../LoRaWAN/Target -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Utilities/trace/adv_trace -I../../Utilities/misc -I../../Utilities/sequencer -I../../Utilities/timer -I../../Utilities/lpm/tiny_lpm -I../../Middlewares/Third_Party/LoRaWAN/LmHandler/Packages -I../../Middlewares/Third_Party/SubGHz_Phy -I../../Middlewares/Third_Party/SubGHz_Phy/stm32_radio_driver -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Middlewares/Third_Party/LoRaWAN/Crypto -I../../Middlewares/Third_Party/LoRaWAN/Mac/Region -I../../Middlewares/Third_Party/LoRaWAN/Mac -I../../Middlewares/Third_Party/LoRaWAN/LmHandler -I../../Middlewares/Third_Party/LoRaWAN/Utilities -I../../Drivers/CMSIS/Include -I../../Drivers/BSP/STM32WLxx_LoRa_E5_mini -I"/home/zero/Projects/E5-Mini/Experiments/e5_mini_AQI_v2/Firmware/STM32CubeIDE/Application/User/IITT_NiF_AQI_Prototype/Inc" -I"/home/zero/Projects/E5-Mini/Experiments/e5_mini_AQI_v2/Firmware/STM32CubeIDE/Drivers/AQI_Drivers_Common/Examples/Inc" -I"/home/zero/Projects/E5-Mini/Experiments/e5_mini_AQI_v2/Firmware/STM32CubeIDE/Drivers/AQI_Drivers_Common/Inc" -I"/home/zero/Projects/E5-Mini/Experiments/e5_mini_AQI_v2/Firmware/STM32CubeIDE/Drivers/BSP/STM32WLxx_LoRa_E5_mini" -Og -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"

clean: clean-Application-2f-User-2f-IITT_NiF_AQI_Prototype-2f-Src

clean-Application-2f-User-2f-IITT_NiF_AQI_Prototype-2f-Src:
	-$(RM) ./Application/User/IITT_NiF_AQI_Prototype/Src/AQI_Prototype_v2.cyclo ./Application/User/IITT_NiF_AQI_Prototype/Src/AQI_Prototype_v2.d ./Application/User/IITT_NiF_AQI_Prototype/Src/AQI_Prototype_v2.o ./Application/User/IITT_NiF_AQI_Prototype/Src/AQI_Prototype_v2.su ./Application/User/IITT_NiF_AQI_Prototype/Src/aqi_datalogger.cyclo ./Application/User/IITT_NiF_AQI_Prototype/Src/aqi_datalogger.d ./Application/User/IITT_NiF_AQI_Prototype/Src/aqi_datalogger.o ./Application/User/IITT_NiF_AQI_Prototype/Src/aqi_datalogger.su

.PHONY: clean-Application-2f-User-2f-IITT_NiF_AQI_Prototype-2f-Src

