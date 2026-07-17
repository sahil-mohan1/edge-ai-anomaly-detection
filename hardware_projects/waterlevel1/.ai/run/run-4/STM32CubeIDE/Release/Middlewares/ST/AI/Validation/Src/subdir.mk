################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (14.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-4/Middlewares/ST/AI/Validation/Src/aiPbIO.c \
C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-4/Middlewares/ST/AI/Validation/Src/aiPbMemRWServices.c \
C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-4/Middlewares/ST/AI/Validation/Src/aiPbMgr.c \
C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-4/Middlewares/ST/AI/Validation/Src/aiValidation_ST_AI.c \
C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-4/Middlewares/ST/AI/Validation/Src/pb_common.c \
C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-4/Middlewares/ST/AI/Validation/Src/pb_decode.c \
C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-4/Middlewares/ST/AI/Validation/Src/pb_encode.c \
C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-4/Middlewares/ST/AI/Validation/Src/stm32msg.pb.c 

OBJS += \
./Middlewares/ST/AI/Validation/Src/aiPbIO.o \
./Middlewares/ST/AI/Validation/Src/aiPbMemRWServices.o \
./Middlewares/ST/AI/Validation/Src/aiPbMgr.o \
./Middlewares/ST/AI/Validation/Src/aiValidation_ST_AI.o \
./Middlewares/ST/AI/Validation/Src/pb_common.o \
./Middlewares/ST/AI/Validation/Src/pb_decode.o \
./Middlewares/ST/AI/Validation/Src/pb_encode.o \
./Middlewares/ST/AI/Validation/Src/stm32msg.pb.o 

C_DEPS += \
./Middlewares/ST/AI/Validation/Src/aiPbIO.d \
./Middlewares/ST/AI/Validation/Src/aiPbMemRWServices.d \
./Middlewares/ST/AI/Validation/Src/aiPbMgr.d \
./Middlewares/ST/AI/Validation/Src/aiValidation_ST_AI.d \
./Middlewares/ST/AI/Validation/Src/pb_common.d \
./Middlewares/ST/AI/Validation/Src/pb_decode.d \
./Middlewares/ST/AI/Validation/Src/pb_encode.d \
./Middlewares/ST/AI/Validation/Src/stm32msg.pb.d 


# Each subdirectory must supply rules for building sources it contributes
Middlewares/ST/AI/Validation/Src/aiPbIO.o: C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-4/Middlewares/ST/AI/Validation/Src/aiPbIO.c Middlewares/ST/AI/Validation/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Validation/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../Middlewares/ST/AI/Validation/Src -I../../AI/App -Os -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"
Middlewares/ST/AI/Validation/Src/aiPbMemRWServices.o: C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-4/Middlewares/ST/AI/Validation/Src/aiPbMemRWServices.c Middlewares/ST/AI/Validation/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Validation/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../Middlewares/ST/AI/Validation/Src -I../../AI/App -Os -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"
Middlewares/ST/AI/Validation/Src/aiPbMgr.o: C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-4/Middlewares/ST/AI/Validation/Src/aiPbMgr.c Middlewares/ST/AI/Validation/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Validation/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../Middlewares/ST/AI/Validation/Src -I../../AI/App -Os -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"
Middlewares/ST/AI/Validation/Src/aiValidation_ST_AI.o: C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-4/Middlewares/ST/AI/Validation/Src/aiValidation_ST_AI.c Middlewares/ST/AI/Validation/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Validation/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../Middlewares/ST/AI/Validation/Src -I../../AI/App -Os -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"
Middlewares/ST/AI/Validation/Src/pb_common.o: C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-4/Middlewares/ST/AI/Validation/Src/pb_common.c Middlewares/ST/AI/Validation/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Validation/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../Middlewares/ST/AI/Validation/Src -I../../AI/App -Os -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"
Middlewares/ST/AI/Validation/Src/pb_decode.o: C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-4/Middlewares/ST/AI/Validation/Src/pb_decode.c Middlewares/ST/AI/Validation/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Validation/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../Middlewares/ST/AI/Validation/Src -I../../AI/App -Os -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"
Middlewares/ST/AI/Validation/Src/pb_encode.o: C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-4/Middlewares/ST/AI/Validation/Src/pb_encode.c Middlewares/ST/AI/Validation/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Validation/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../Middlewares/ST/AI/Validation/Src -I../../AI/App -Os -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"
Middlewares/ST/AI/Validation/Src/stm32msg.pb.o: C:/Users/sahil/.stm32cubeaistudio/workspace/waterlevel1/.ai/run/run-4/Middlewares/ST/AI/Validation/Src/stm32msg.pb.c Middlewares/ST/AI/Validation/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -DCORE_CM4 -DUSE_HAL_DRIVER -DSTM32WLE5xx -DHAVE_NETWORK_INFO -c -I../../Core/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Drivers/CMSIS/Include -I../../Middlewares/ST/AI/Inc -I../../Middlewares/ST/AI/Misc/Inc -I../../Middlewares/ST/AI/Validation/Inc -I../../Middlewares/ST/AI/Misc/Src -I../../Middlewares/ST/AI/Validation/Src -I../../AI/App -Os -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"

clean: clean-Middlewares-2f-ST-2f-AI-2f-Validation-2f-Src

clean-Middlewares-2f-ST-2f-AI-2f-Validation-2f-Src:
	-$(RM) ./Middlewares/ST/AI/Validation/Src/aiPbIO.cyclo ./Middlewares/ST/AI/Validation/Src/aiPbIO.d ./Middlewares/ST/AI/Validation/Src/aiPbIO.o ./Middlewares/ST/AI/Validation/Src/aiPbIO.su ./Middlewares/ST/AI/Validation/Src/aiPbMemRWServices.cyclo ./Middlewares/ST/AI/Validation/Src/aiPbMemRWServices.d ./Middlewares/ST/AI/Validation/Src/aiPbMemRWServices.o ./Middlewares/ST/AI/Validation/Src/aiPbMemRWServices.su ./Middlewares/ST/AI/Validation/Src/aiPbMgr.cyclo ./Middlewares/ST/AI/Validation/Src/aiPbMgr.d ./Middlewares/ST/AI/Validation/Src/aiPbMgr.o ./Middlewares/ST/AI/Validation/Src/aiPbMgr.su ./Middlewares/ST/AI/Validation/Src/aiValidation_ST_AI.cyclo ./Middlewares/ST/AI/Validation/Src/aiValidation_ST_AI.d ./Middlewares/ST/AI/Validation/Src/aiValidation_ST_AI.o ./Middlewares/ST/AI/Validation/Src/aiValidation_ST_AI.su ./Middlewares/ST/AI/Validation/Src/pb_common.cyclo ./Middlewares/ST/AI/Validation/Src/pb_common.d ./Middlewares/ST/AI/Validation/Src/pb_common.o ./Middlewares/ST/AI/Validation/Src/pb_common.su ./Middlewares/ST/AI/Validation/Src/pb_decode.cyclo ./Middlewares/ST/AI/Validation/Src/pb_decode.d ./Middlewares/ST/AI/Validation/Src/pb_decode.o ./Middlewares/ST/AI/Validation/Src/pb_decode.su ./Middlewares/ST/AI/Validation/Src/pb_encode.cyclo ./Middlewares/ST/AI/Validation/Src/pb_encode.d ./Middlewares/ST/AI/Validation/Src/pb_encode.o ./Middlewares/ST/AI/Validation/Src/pb_encode.su ./Middlewares/ST/AI/Validation/Src/stm32msg.pb.cyclo ./Middlewares/ST/AI/Validation/Src/stm32msg.pb.d ./Middlewares/ST/AI/Validation/Src/stm32msg.pb.o ./Middlewares/ST/AI/Validation/Src/stm32msg.pb.su

.PHONY: clean-Middlewares-2f-ST-2f-AI-2f-Validation-2f-Src

