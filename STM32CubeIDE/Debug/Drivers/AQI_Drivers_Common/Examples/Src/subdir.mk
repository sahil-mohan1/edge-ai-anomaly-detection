################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (13.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../Drivers/AQI_Drivers_Common/Examples/Src/bme690_bsec_example.c \
../Drivers/AQI_Drivers_Common/Examples/Src/bme690_test.c \
../Drivers/AQI_Drivers_Common/Examples/Src/bmv080_example.c \
../Drivers/AQI_Drivers_Common/Examples/Src/sd_test.c \
../Drivers/AQI_Drivers_Common/Examples/Src/trace_test.c \
../Drivers/AQI_Drivers_Common/Examples/Src/user_diskio.c 

OBJS += \
./Drivers/AQI_Drivers_Common/Examples/Src/bme690_bsec_example.o \
./Drivers/AQI_Drivers_Common/Examples/Src/bme690_test.o \
./Drivers/AQI_Drivers_Common/Examples/Src/bmv080_example.o \
./Drivers/AQI_Drivers_Common/Examples/Src/sd_test.o \
./Drivers/AQI_Drivers_Common/Examples/Src/trace_test.o \
./Drivers/AQI_Drivers_Common/Examples/Src/user_diskio.o 

C_DEPS += \
./Drivers/AQI_Drivers_Common/Examples/Src/bme690_bsec_example.d \
./Drivers/AQI_Drivers_Common/Examples/Src/bme690_test.d \
./Drivers/AQI_Drivers_Common/Examples/Src/bmv080_example.d \
./Drivers/AQI_Drivers_Common/Examples/Src/sd_test.d \
./Drivers/AQI_Drivers_Common/Examples/Src/trace_test.d \
./Drivers/AQI_Drivers_Common/Examples/Src/user_diskio.d 


# Each subdirectory must supply rules for building sources it contributes
Drivers/AQI_Drivers_Common/Examples/Src/%.o Drivers/AQI_Drivers_Common/Examples/Src/%.su Drivers/AQI_Drivers_Common/Examples/Src/%.cyclo: ../Drivers/AQI_Drivers_Common/Examples/Src/%.c Drivers/AQI_Drivers_Common/Examples/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DCORE_CM4 -DSTM32WLE5xx -DUSE_HAL_DRIVER -c -I../../Core/Inc -I../../LoRaWAN/App -I../../LoRaWAN/Target -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Utilities/trace/adv_trace -I../../Utilities/misc -I../../Utilities/sequencer -I../../Utilities/timer -I../../Utilities/lpm/tiny_lpm -I../../Middlewares/Third_Party/LoRaWAN/LmHandler/Packages -I../../Middlewares/Third_Party/SubGHz_Phy -I../../Middlewares/Third_Party/SubGHz_Phy/stm32_radio_driver -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Middlewares/Third_Party/LoRaWAN/Crypto -I../../Middlewares/Third_Party/LoRaWAN/Mac/Region -I../../Middlewares/Third_Party/LoRaWAN/Mac -I../../Middlewares/Third_Party/LoRaWAN/LmHandler -I../../Middlewares/Third_Party/LoRaWAN/Utilities -I../../Drivers/CMSIS/Include -I../../Drivers/BSP/STM32WLxx_LoRa_E5_mini -I"/home/zero/Projects/E5-Mini/Experiments/E5_hlk_RLS/STM32CubeIDE/Drivers/AQI_Drivers_Common/Examples/Inc" -I"/home/zero/Projects/E5-Mini/Experiments/E5_hlk_RLS/STM32CubeIDE/Drivers/AQI_Drivers_Common/Inc" -I"/home/zero/Projects/E5-Mini/Experiments/E5_hlk_RLS/STM32CubeIDE/Drivers/BSP/STM32WLxx_LoRa_E5_mini" -I"/home/zero/Projects/E5-Mini/Experiments/E5_hlk_RLS/STM32CubeIDE/Application/User/hlk_ld2413" -Og -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"

clean: clean-Drivers-2f-AQI_Drivers_Common-2f-Examples-2f-Src

clean-Drivers-2f-AQI_Drivers_Common-2f-Examples-2f-Src:
	-$(RM) ./Drivers/AQI_Drivers_Common/Examples/Src/bme690_bsec_example.cyclo ./Drivers/AQI_Drivers_Common/Examples/Src/bme690_bsec_example.d ./Drivers/AQI_Drivers_Common/Examples/Src/bme690_bsec_example.o ./Drivers/AQI_Drivers_Common/Examples/Src/bme690_bsec_example.su ./Drivers/AQI_Drivers_Common/Examples/Src/bme690_test.cyclo ./Drivers/AQI_Drivers_Common/Examples/Src/bme690_test.d ./Drivers/AQI_Drivers_Common/Examples/Src/bme690_test.o ./Drivers/AQI_Drivers_Common/Examples/Src/bme690_test.su ./Drivers/AQI_Drivers_Common/Examples/Src/bmv080_example.cyclo ./Drivers/AQI_Drivers_Common/Examples/Src/bmv080_example.d ./Drivers/AQI_Drivers_Common/Examples/Src/bmv080_example.o ./Drivers/AQI_Drivers_Common/Examples/Src/bmv080_example.su ./Drivers/AQI_Drivers_Common/Examples/Src/sd_test.cyclo ./Drivers/AQI_Drivers_Common/Examples/Src/sd_test.d ./Drivers/AQI_Drivers_Common/Examples/Src/sd_test.o ./Drivers/AQI_Drivers_Common/Examples/Src/sd_test.su ./Drivers/AQI_Drivers_Common/Examples/Src/trace_test.cyclo ./Drivers/AQI_Drivers_Common/Examples/Src/trace_test.d ./Drivers/AQI_Drivers_Common/Examples/Src/trace_test.o ./Drivers/AQI_Drivers_Common/Examples/Src/trace_test.su ./Drivers/AQI_Drivers_Common/Examples/Src/user_diskio.cyclo ./Drivers/AQI_Drivers_Common/Examples/Src/user_diskio.d ./Drivers/AQI_Drivers_Common/Examples/Src/user_diskio.o ./Drivers/AQI_Drivers_Common/Examples/Src/user_diskio.su

.PHONY: clean-Drivers-2f-AQI_Drivers_Common-2f-Examples-2f-Src

