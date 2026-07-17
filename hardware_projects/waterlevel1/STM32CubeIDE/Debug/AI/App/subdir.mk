################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (14.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
C:/Users/sahil/Desktop/ICFOSS/Anomaly\ Detection/hardware_projects/waterlevel1/AI/App/app_x-cube-ai.c \
C:/Users/sahil/Desktop/ICFOSS/Anomaly\ Detection/hardware_projects/waterlevel1/AI/App/network.c \
C:/Users/sahil/Desktop/ICFOSS/Anomaly\ Detection/hardware_projects/waterlevel1/AI/App/network_data.c \
C:/Users/sahil/Desktop/ICFOSS/Anomaly\ Detection/hardware_projects/waterlevel1/AI/App/network_weights.c \
C:/Users/sahil/Desktop/ICFOSS/Anomaly\ Detection/hardware_projects/waterlevel1/AI/App/user_init.c 

OBJS += \
./AI/App/app_x-cube-ai.o \
./AI/App/network.o \
./AI/App/network_data.o \
./AI/App/network_weights.o \
./AI/App/user_init.o 

C_DEPS += \
./AI/App/app_x-cube-ai.d \
./AI/App/network.d \
./AI/App/network_data.d \
./AI/App/network_weights.d \
./AI/App/user_init.d 


# Each subdirectory must supply rules for building sources it contributes
AI/App/app_x-cube-ai.o: C:/Users/sahil/Desktop/ICFOSS/Anomaly\ Detection/hardware_projects/waterlevel1/AI/App/app_x-cube-ai.c AI/App/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../AI/App -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"AI/App/app_x-cube-ai.d" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"
AI/App/network.o: C:/Users/sahil/Desktop/ICFOSS/Anomaly\ Detection/hardware_projects/waterlevel1/AI/App/network.c AI/App/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../AI/App -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"AI/App/network.d" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"
AI/App/network_data.o: C:/Users/sahil/Desktop/ICFOSS/Anomaly\ Detection/hardware_projects/waterlevel1/AI/App/network_data.c AI/App/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../AI/App -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"AI/App/network_data.d" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"
AI/App/network_weights.o: C:/Users/sahil/Desktop/ICFOSS/Anomaly\ Detection/hardware_projects/waterlevel1/AI/App/network_weights.c AI/App/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../AI/App -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"AI/App/network_weights.d" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"
AI/App/user_init.o: C:/Users/sahil/Desktop/ICFOSS/Anomaly\ Detection/hardware_projects/waterlevel1/AI/App/user_init.c AI/App/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../AI/App -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"AI/App/user_init.d" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"

clean: clean-AI-2f-App

clean-AI-2f-App:
	-$(RM) ./AI/App/app_x-cube-ai.cyclo ./AI/App/app_x-cube-ai.d ./AI/App/app_x-cube-ai.o ./AI/App/app_x-cube-ai.su ./AI/App/network.cyclo ./AI/App/network.d ./AI/App/network.o ./AI/App/network.su ./AI/App/network_data.cyclo ./AI/App/network_data.d ./AI/App/network_data.o ./AI/App/network_data.su ./AI/App/network_weights.cyclo ./AI/App/network_weights.d ./AI/App/network_weights.o ./AI/App/network_weights.su ./AI/App/user_init.cyclo ./AI/App/user_init.d ./AI/App/user_init.o ./AI/App/user_init.su

.PHONY: clean-AI-2f-App

