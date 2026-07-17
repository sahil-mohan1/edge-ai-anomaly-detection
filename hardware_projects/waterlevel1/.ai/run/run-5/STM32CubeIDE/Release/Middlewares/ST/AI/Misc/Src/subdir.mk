################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (14.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-5/Middlewares/ST/AI/Misc/Src/aiTestHelper_ST_AI.c \
C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-5/Middlewares/ST/AI/Misc/Src/aiTestUtility.c \
C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-5/Middlewares/ST/AI/Misc/Src/ai_device_adaptor.c \
C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-5/Middlewares/ST/AI/Misc/Src/lc_print.c \
C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-5/Middlewares/ST/AI/Misc/Src/syscalls.c 

OBJS += \
./Middlewares/ST/AI/Misc/Src/aiTestHelper_ST_AI.o \
./Middlewares/ST/AI/Misc/Src/aiTestUtility.o \
./Middlewares/ST/AI/Misc/Src/ai_device_adaptor.o \
./Middlewares/ST/AI/Misc/Src/lc_print.o \
./Middlewares/ST/AI/Misc/Src/syscalls.o 

C_DEPS += \
./Middlewares/ST/AI/Misc/Src/aiTestHelper_ST_AI.d \
./Middlewares/ST/AI/Misc/Src/aiTestUtility.d \
./Middlewares/ST/AI/Misc/Src/ai_device_adaptor.d \
./Middlewares/ST/AI/Misc/Src/lc_print.d \
./Middlewares/ST/AI/Misc/Src/syscalls.d 


# Each subdirectory must supply rules for building sources it contributes
Middlewares/ST/AI/Misc/Src/aiTestHelper_ST_AI.o: C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-5/Middlewares/ST/AI/Misc/Src/aiTestHelper_ST_AI.c Middlewares/ST/AI/Misc/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Validation/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../Middlewares/ST/AI/Validation/Src -I../../AI/App -Os -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"
Middlewares/ST/AI/Misc/Src/aiTestUtility.o: C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-5/Middlewares/ST/AI/Misc/Src/aiTestUtility.c Middlewares/ST/AI/Misc/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Validation/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../Middlewares/ST/AI/Validation/Src -I../../AI/App -Os -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"
Middlewares/ST/AI/Misc/Src/ai_device_adaptor.o: C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-5/Middlewares/ST/AI/Misc/Src/ai_device_adaptor.c Middlewares/ST/AI/Misc/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Validation/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../Middlewares/ST/AI/Validation/Src -I../../AI/App -Os -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"
Middlewares/ST/AI/Misc/Src/lc_print.o: C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-5/Middlewares/ST/AI/Misc/Src/lc_print.c Middlewares/ST/AI/Misc/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Validation/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../Middlewares/ST/AI/Validation/Src -I../../AI/App -Os -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"
Middlewares/ST/AI/Misc/Src/syscalls.o: C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-5/Middlewares/ST/AI/Misc/Src/syscalls.c Middlewares/ST/AI/Misc/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Validation/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../Middlewares/ST/AI/Validation/Src -I../../AI/App -Os -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"

clean: clean-Middlewares-2f-ST-2f-AI-2f-Misc-2f-Src

clean-Middlewares-2f-ST-2f-AI-2f-Misc-2f-Src:
	-$(RM) ./Middlewares/ST/AI/Misc/Src/aiTestHelper_ST_AI.cyclo ./Middlewares/ST/AI/Misc/Src/aiTestHelper_ST_AI.d ./Middlewares/ST/AI/Misc/Src/aiTestHelper_ST_AI.o ./Middlewares/ST/AI/Misc/Src/aiTestHelper_ST_AI.su ./Middlewares/ST/AI/Misc/Src/aiTestUtility.cyclo ./Middlewares/ST/AI/Misc/Src/aiTestUtility.d ./Middlewares/ST/AI/Misc/Src/aiTestUtility.o ./Middlewares/ST/AI/Misc/Src/aiTestUtility.su ./Middlewares/ST/AI/Misc/Src/ai_device_adaptor.cyclo ./Middlewares/ST/AI/Misc/Src/ai_device_adaptor.d ./Middlewares/ST/AI/Misc/Src/ai_device_adaptor.o ./Middlewares/ST/AI/Misc/Src/ai_device_adaptor.su ./Middlewares/ST/AI/Misc/Src/lc_print.cyclo ./Middlewares/ST/AI/Misc/Src/lc_print.d ./Middlewares/ST/AI/Misc/Src/lc_print.o ./Middlewares/ST/AI/Misc/Src/lc_print.su ./Middlewares/ST/AI/Misc/Src/syscalls.cyclo ./Middlewares/ST/AI/Misc/Src/syscalls.d ./Middlewares/ST/AI/Misc/Src/syscalls.o ./Middlewares/ST/AI/Misc/Src/syscalls.su

.PHONY: clean-Middlewares-2f-ST-2f-AI-2f-Misc-2f-Src

