################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (13.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../Drivers/AQI_Drivers_Common/Src/FATFS_SD.c \
../Drivers/AQI_Drivers_Common/Src/INA219.c \
../Drivers/AQI_Drivers_Common/Src/NavIC.c \
../Drivers/AQI_Drivers_Common/Src/bme690_bsec_integration.c \
../Drivers/AQI_Drivers_Common/Src/bme690_integration.c \
../Drivers/AQI_Drivers_Common/Src/bme69x.c \
../Drivers/AQI_Drivers_Common/Src/bmv080_integration.c \
../Drivers/AQI_Drivers_Common/Src/bmv080_stm.c \
../Drivers/AQI_Drivers_Common/Src/ccsbcs.c \
../Drivers/AQI_Drivers_Common/Src/datalogger.c \
../Drivers/AQI_Drivers_Common/Src/datalogger_format.c \
../Drivers/AQI_Drivers_Common/Src/datalogger_storage.c \
../Drivers/AQI_Drivers_Common/Src/diskio.c \
../Drivers/AQI_Drivers_Common/Src/ff.c \
../Drivers/AQI_Drivers_Common/Src/ff_gen_drv.c 

OBJS += \
./Drivers/AQI_Drivers_Common/Src/FATFS_SD.o \
./Drivers/AQI_Drivers_Common/Src/INA219.o \
./Drivers/AQI_Drivers_Common/Src/NavIC.o \
./Drivers/AQI_Drivers_Common/Src/bme690_bsec_integration.o \
./Drivers/AQI_Drivers_Common/Src/bme690_integration.o \
./Drivers/AQI_Drivers_Common/Src/bme69x.o \
./Drivers/AQI_Drivers_Common/Src/bmv080_integration.o \
./Drivers/AQI_Drivers_Common/Src/bmv080_stm.o \
./Drivers/AQI_Drivers_Common/Src/ccsbcs.o \
./Drivers/AQI_Drivers_Common/Src/datalogger.o \
./Drivers/AQI_Drivers_Common/Src/datalogger_format.o \
./Drivers/AQI_Drivers_Common/Src/datalogger_storage.o \
./Drivers/AQI_Drivers_Common/Src/diskio.o \
./Drivers/AQI_Drivers_Common/Src/ff.o \
./Drivers/AQI_Drivers_Common/Src/ff_gen_drv.o 

C_DEPS += \
./Drivers/AQI_Drivers_Common/Src/FATFS_SD.d \
./Drivers/AQI_Drivers_Common/Src/INA219.d \
./Drivers/AQI_Drivers_Common/Src/NavIC.d \
./Drivers/AQI_Drivers_Common/Src/bme690_bsec_integration.d \
./Drivers/AQI_Drivers_Common/Src/bme690_integration.d \
./Drivers/AQI_Drivers_Common/Src/bme69x.d \
./Drivers/AQI_Drivers_Common/Src/bmv080_integration.d \
./Drivers/AQI_Drivers_Common/Src/bmv080_stm.d \
./Drivers/AQI_Drivers_Common/Src/ccsbcs.d \
./Drivers/AQI_Drivers_Common/Src/datalogger.d \
./Drivers/AQI_Drivers_Common/Src/datalogger_format.d \
./Drivers/AQI_Drivers_Common/Src/datalogger_storage.d \
./Drivers/AQI_Drivers_Common/Src/diskio.d \
./Drivers/AQI_Drivers_Common/Src/ff.d \
./Drivers/AQI_Drivers_Common/Src/ff_gen_drv.d 


# Each subdirectory must supply rules for building sources it contributes
Drivers/AQI_Drivers_Common/Src/%.o Drivers/AQI_Drivers_Common/Src/%.su Drivers/AQI_Drivers_Common/Src/%.cyclo: ../Drivers/AQI_Drivers_Common/Src/%.c Drivers/AQI_Drivers_Common/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DCORE_CM4 -DSTM32WLE5xx -DUSE_HAL_DRIVER -c -I../../Core/Inc -I../../LoRaWAN/App -I../../LoRaWAN/Target -I../../Drivers/STM32WLxx_HAL_Driver/Inc -I../../Drivers/STM32WLxx_HAL_Driver/Inc/Legacy -I../../Utilities/trace/adv_trace -I../../Utilities/misc -I../../Utilities/sequencer -I../../Utilities/timer -I../../Utilities/lpm/tiny_lpm -I../../Middlewares/Third_Party/LoRaWAN/LmHandler/Packages -I../../Middlewares/Third_Party/SubGHz_Phy -I../../Middlewares/Third_Party/SubGHz_Phy/stm32_radio_driver -I../../Drivers/CMSIS/Device/ST/STM32WLxx/Include -I../../Middlewares/Third_Party/LoRaWAN/Crypto -I../../Middlewares/Third_Party/LoRaWAN/Mac/Region -I../../Middlewares/Third_Party/LoRaWAN/Mac -I../../Middlewares/Third_Party/LoRaWAN/LmHandler -I../../Middlewares/Third_Party/LoRaWAN/Utilities -I../../Drivers/CMSIS/Include -I../../Drivers/BSP/STM32WLxx_LoRa_E5_mini -I"/home/zero/Projects/E5-Mini/Experiments/E5_hlk_RLS/STM32CubeIDE/Drivers/AQI_Drivers_Common/Examples/Inc" -I"/home/zero/Projects/E5-Mini/Experiments/E5_hlk_RLS/STM32CubeIDE/Drivers/AQI_Drivers_Common/Inc" -I"/home/zero/Projects/E5-Mini/Experiments/E5_hlk_RLS/STM32CubeIDE/Drivers/BSP/STM32WLxx_LoRa_E5_mini" -I"/home/zero/Projects/E5-Mini/Experiments/E5_hlk_RLS/STM32CubeIDE/Application/User/hlk_ld2413" -Og -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"

clean: clean-Drivers-2f-AQI_Drivers_Common-2f-Src

clean-Drivers-2f-AQI_Drivers_Common-2f-Src:
	-$(RM) ./Drivers/AQI_Drivers_Common/Src/FATFS_SD.cyclo ./Drivers/AQI_Drivers_Common/Src/FATFS_SD.d ./Drivers/AQI_Drivers_Common/Src/FATFS_SD.o ./Drivers/AQI_Drivers_Common/Src/FATFS_SD.su ./Drivers/AQI_Drivers_Common/Src/INA219.cyclo ./Drivers/AQI_Drivers_Common/Src/INA219.d ./Drivers/AQI_Drivers_Common/Src/INA219.o ./Drivers/AQI_Drivers_Common/Src/INA219.su ./Drivers/AQI_Drivers_Common/Src/NavIC.cyclo ./Drivers/AQI_Drivers_Common/Src/NavIC.d ./Drivers/AQI_Drivers_Common/Src/NavIC.o ./Drivers/AQI_Drivers_Common/Src/NavIC.su ./Drivers/AQI_Drivers_Common/Src/bme690_bsec_integration.cyclo ./Drivers/AQI_Drivers_Common/Src/bme690_bsec_integration.d ./Drivers/AQI_Drivers_Common/Src/bme690_bsec_integration.o ./Drivers/AQI_Drivers_Common/Src/bme690_bsec_integration.su ./Drivers/AQI_Drivers_Common/Src/bme690_integration.cyclo ./Drivers/AQI_Drivers_Common/Src/bme690_integration.d ./Drivers/AQI_Drivers_Common/Src/bme690_integration.o ./Drivers/AQI_Drivers_Common/Src/bme690_integration.su ./Drivers/AQI_Drivers_Common/Src/bme69x.cyclo ./Drivers/AQI_Drivers_Common/Src/bme69x.d ./Drivers/AQI_Drivers_Common/Src/bme69x.o ./Drivers/AQI_Drivers_Common/Src/bme69x.su ./Drivers/AQI_Drivers_Common/Src/bmv080_integration.cyclo ./Drivers/AQI_Drivers_Common/Src/bmv080_integration.d ./Drivers/AQI_Drivers_Common/Src/bmv080_integration.o ./Drivers/AQI_Drivers_Common/Src/bmv080_integration.su ./Drivers/AQI_Drivers_Common/Src/bmv080_stm.cyclo ./Drivers/AQI_Drivers_Common/Src/bmv080_stm.d ./Drivers/AQI_Drivers_Common/Src/bmv080_stm.o ./Drivers/AQI_Drivers_Common/Src/bmv080_stm.su ./Drivers/AQI_Drivers_Common/Src/ccsbcs.cyclo ./Drivers/AQI_Drivers_Common/Src/ccsbcs.d ./Drivers/AQI_Drivers_Common/Src/ccsbcs.o ./Drivers/AQI_Drivers_Common/Src/ccsbcs.su ./Drivers/AQI_Drivers_Common/Src/datalogger.cyclo ./Drivers/AQI_Drivers_Common/Src/datalogger.d ./Drivers/AQI_Drivers_Common/Src/datalogger.o ./Drivers/AQI_Drivers_Common/Src/datalogger.su ./Drivers/AQI_Drivers_Common/Src/datalogger_format.cyclo ./Drivers/AQI_Drivers_Common/Src/datalogger_format.d ./Drivers/AQI_Drivers_Common/Src/datalogger_format.o ./Drivers/AQI_Drivers_Common/Src/datalogger_format.su ./Drivers/AQI_Drivers_Common/Src/datalogger_storage.cyclo ./Drivers/AQI_Drivers_Common/Src/datalogger_storage.d ./Drivers/AQI_Drivers_Common/Src/datalogger_storage.o ./Drivers/AQI_Drivers_Common/Src/datalogger_storage.su ./Drivers/AQI_Drivers_Common/Src/diskio.cyclo ./Drivers/AQI_Drivers_Common/Src/diskio.d ./Drivers/AQI_Drivers_Common/Src/diskio.o ./Drivers/AQI_Drivers_Common/Src/diskio.su ./Drivers/AQI_Drivers_Common/Src/ff.cyclo ./Drivers/AQI_Drivers_Common/Src/ff.d ./Drivers/AQI_Drivers_Common/Src/ff.o ./Drivers/AQI_Drivers_Common/Src/ff.su ./Drivers/AQI_Drivers_Common/Src/ff_gen_drv.cyclo ./Drivers/AQI_Drivers_Common/Src/ff_gen_drv.d ./Drivers/AQI_Drivers_Common/Src/ff_gen_drv.o ./Drivers/AQI_Drivers_Common/Src/ff_gen_drv.su

.PHONY: clean-Drivers-2f-AQI_Drivers_Common-2f-Src

