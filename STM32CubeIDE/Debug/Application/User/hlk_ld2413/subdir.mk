################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (13.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../Application/User/hlk_ld2413/hlk_ld2413.c 

OBJS += \
./Application/User/hlk_ld2413/hlk_ld2413.o 

C_DEPS += \
./Application/User/hlk_ld2413/hlk_ld2413.d 


# Each subdirectory must supply rules for building sources it contributes
Application/User/hlk_ld2413/%.o Application/User/hlk_ld2413/%.su Application/User/hlk_ld2413/%.cyclo: ../Application/User/hlk_ld2413/%.c Application/User/hlk_ld2413/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DCORE_CM4 -DSTM32WLE5xx -DUSE_HAL_DRIVER -c -I../../Core/Inc -I/home/icfoss/STM32CubeIDE/radar_new/E5_mini_with_hlk_ld2413_v2.0/E5_hlk_RLS_log/E5_hlk_RLS/Middlewares/ST -I../../LoRaWAN/App -I../../LoRaWAN/Target -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Utilities/trace/adv_trace -I../../Utilities/misc -I../../Utilities/sequencer -I../../Utilities/timer -I../../Utilities/lpm/tiny_lpm -I../../Middlewares/Third_Party/LoRaWAN/LmHandler/Packages -I../../Middlewares/Third_Party/SubGHz_Phy -I../../Middlewares/Third_Party/SubGHz_Phy/stm32_radio_driver -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Middlewares/Third_Party/LoRaWAN/Crypto -I../../Middlewares/Third_Party/LoRaWAN/Mac/Region -I../../Middlewares/Third_Party/LoRaWAN/Mac -I../../Middlewares/Third_Party/LoRaWAN/LmHandler -I../../Middlewares/Third_Party/LoRaWAN/Utilities -I../../Drivers/CMSIS/Include -I../../Drivers/BSP/STM32WLxx_LoRa_E5_mini -I"/home/icfoss/STM32CubeIDE/radar_new/E5_mini_with_hlk_ld2413_v2.0/E5_hlk_RLS_log/E5_hlk_RLS/STM32CubeIDE/Drivers/BSP/STM32WLxx_LoRa_E5_mini" -I"/home/icfoss/STM32CubeIDE/radar_new/E5_mini_with_hlk_ld2413_v2.0/E5_hlk_RLS_log/E5_hlk_RLS/STM32CubeIDE/Application/User/hlk_ld2413" -I"/home/icfoss/STM32CubeIDE/radar_new/E5_mini_with_hlk_ld2413_v2.0/E5_hlk_RLS_log/E5_hlk_RLS/STM32CubeIDE/Application/User/AI" -I"/home/icfoss/STM32CubeIDE/radar_new/E5_mini_with_hlk_ld2413_v2.0/E5_hlk_RLS_log/E5_hlk_RLS/STM32CubeIDE/Application/User/AI/App" -I"/home/icfoss/STM32CubeIDE/radar_new/E5_mini_with_hlk_ld2413_v2.0/E5_hlk_RLS_log/E5_hlk_RLS/STM32CubeIDE/Middlewares/ST/AI/Misc/Inc" -I"/home/icfoss/STM32CubeIDE/radar_new/E5_mini_with_hlk_ld2413_v2.0/E5_hlk_RLS_log/E5_hlk_RLS/STM32CubeIDE/Middlewares/ST/AI/Inc" -Og -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"

clean: clean-Application-2f-User-2f-hlk_ld2413

clean-Application-2f-User-2f-hlk_ld2413:
	-$(RM) ./Application/User/hlk_ld2413/hlk_ld2413.cyclo ./Application/User/hlk_ld2413/hlk_ld2413.d ./Application/User/hlk_ld2413/hlk_ld2413.o ./Application/User/hlk_ld2413/hlk_ld2413.su

.PHONY: clean-Application-2f-User-2f-hlk_ld2413

