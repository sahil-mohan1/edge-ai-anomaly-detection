################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (12.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../Application/User/AT_RH/Src/7semi_sht45.c \
../Application/User/AT_RH/Src/AT_RH_Device.c \
../Application/User/AT_RH/Src/Lora_e5_mini_i2c.c 

OBJS += \
./Application/User/AT_RH/Src/7semi_sht45.o \
./Application/User/AT_RH/Src/AT_RH_Device.o \
./Application/User/AT_RH/Src/Lora_e5_mini_i2c.o 

C_DEPS += \
./Application/User/AT_RH/Src/7semi_sht45.d \
./Application/User/AT_RH/Src/AT_RH_Device.d \
./Application/User/AT_RH/Src/Lora_e5_mini_i2c.d 


# Each subdirectory must supply rules for building sources it contributes
Application/User/AT_RH/Src/%.o Application/User/AT_RH/Src/%.su Application/User/AT_RH/Src/%.cyclo: ../Application/User/AT_RH/Src/%.c Application/User/AT_RH/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DCORE_CM4 -DSTM32WLE5xx -DUSE_HAL_DRIVER -c -I../../Core/Inc -I../../LoRaWAN/App -I../../LoRaWAN/Target -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Utilities/trace/adv_trace -I../../Utilities/misc -I../../Utilities/sequencer -I../../Utilities/timer -I../../Utilities/lpm/tiny_lpm -I../../Middlewares/Third_Party/LoRaWAN/LmHandler/Packages -I../../Middlewares/Third_Party/SubGHz_Phy -I../../Middlewares/Third_Party/SubGHz_Phy/stm32_radio_driver -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Middlewares/Third_Party/LoRaWAN/Crypto -I../../Middlewares/Third_Party/LoRaWAN/Mac/Region -I../../Middlewares/Third_Party/LoRaWAN/Mac -I../../Middlewares/Third_Party/LoRaWAN/LmHandler -I../../Middlewares/Third_Party/LoRaWAN/Utilities -I../../Drivers/CMSIS/Include -I../../Drivers/BSP/STM32WLxx_LoRa_E5_mini -I"/home/zero/Projects/E5-Mini/Experiments/Firmware/Bare_stack/STM32CubeIDE/Application/User/AT_RH/Inc" -Og -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"

clean: clean-Application-2f-User-2f-AT_RH-2f-Src

clean-Application-2f-User-2f-AT_RH-2f-Src:
	-$(RM) ./Application/User/AT_RH/Src/7semi_sht45.cyclo ./Application/User/AT_RH/Src/7semi_sht45.d ./Application/User/AT_RH/Src/7semi_sht45.o ./Application/User/AT_RH/Src/7semi_sht45.su ./Application/User/AT_RH/Src/AT_RH_Device.cyclo ./Application/User/AT_RH/Src/AT_RH_Device.d ./Application/User/AT_RH/Src/AT_RH_Device.o ./Application/User/AT_RH/Src/AT_RH_Device.su ./Application/User/AT_RH/Src/Lora_e5_mini_i2c.cyclo ./Application/User/AT_RH/Src/Lora_e5_mini_i2c.d ./Application/User/AT_RH/Src/Lora_e5_mini_i2c.o ./Application/User/AT_RH/Src/Lora_e5_mini_i2c.su

.PHONY: clean-Application-2f-User-2f-AT_RH-2f-Src

