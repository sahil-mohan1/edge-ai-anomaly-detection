################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (13.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
S_SRCS += \
../Application/User/Startup/startup_stm32wle5jcix.s 

OBJS += \
./Application/User/Startup/startup_stm32wle5jcix.o 

S_DEPS += \
./Application/User/Startup/startup_stm32wle5jcix.d 


# Each subdirectory must supply rules for building sources it contributes
Application/User/Startup/%.o: ../Application/User/Startup/%.s Application/User/Startup/subdir.mk
	arm-none-eabi-gcc -mcpu=cortex-m4 -g3 -DDEBUG -c -I"/home/icfoss/STM32CubeIDE/radar_new/E5_mini_with_hlk_ld2413_v2.0/E5_hlk_RLS_log/E5_hlk_RLS/STM32CubeIDE/Drivers/BSP/STM32WLxx_LoRa_E5_mini" -I"/home/icfoss/STM32CubeIDE/radar_new/E5_mini_with_hlk_ld2413_v2.0/E5_hlk_RLS_log/E5_hlk_RLS/STM32CubeIDE/Application/User/hlk_ld2413" -I"/home/icfoss/STM32CubeIDE/radar_new/E5_mini_with_hlk_ld2413_v2.0/E5_hlk_RLS_log/E5_hlk_RLS/STM32CubeIDE/Application/User/AI" -I"/home/icfoss/STM32CubeIDE/radar_new/E5_mini_with_hlk_ld2413_v2.0/E5_hlk_RLS_log/E5_hlk_RLS/STM32CubeIDE/Application/User/AI/App" -I"/home/icfoss/STM32CubeIDE/radar_new/E5_mini_with_hlk_ld2413_v2.0/E5_hlk_RLS_log/E5_hlk_RLS/STM32CubeIDE/Middlewares/ST/AI/Misc/Inc" -I"/home/icfoss/STM32CubeIDE/radar_new/E5_mini_with_hlk_ld2413_v2.0/E5_hlk_RLS_log/E5_hlk_RLS/STM32CubeIDE/Middlewares/ST/AI/Inc" -x assembler-with-cpp -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@" "$<"

clean: clean-Application-2f-User-2f-Startup

clean-Application-2f-User-2f-Startup:
	-$(RM) ./Application/User/Startup/startup_stm32wle5jcix.d ./Application/User/Startup/startup_stm32wle5jcix.o

.PHONY: clean-Application-2f-User-2f-Startup

