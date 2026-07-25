# LoRaWAN Payload Format Document

This document defines the custom LoRaWAN payload format used for transmitting the anomaly detection results and sensor data from the edge device (LoRa-E5) to the ChirpStack network server.

## 1. Payload Structure
The binary format is tightly packed to minimize airtime and power consumption. It consists of a mandatory 4-byte baseline header, followed by a dynamic array of historical distance logs (up to 16 entries).

### Data Fields
1. **Distance** (2 bytes, Unsigned Integer 16-bit): The most recently measured water level distance.
2. **Error Code** (1 byte): The anomaly detection state from the ST X-CUBE-AI model. Maps to values like `0: ok`, `2: sensor timeout`, `3: spike detected`, etc.
3. **Battery Voltage** (1 byte): The battery level of the edge device (divided by 10 for transmission).
4. **Distance Logs** (Variable, up to 32 bytes): Historical distance data points to help reconstruct recent trends leading up to an anomaly.


Below are screenshots demonstrating the payload format layout and structure:





---

## 3. Firmware Encoder implementation (C)

The edge device (e.g., STM32 / LoRa-E5) uses the following C function to pack the sensor and anomaly detection data into the `AppData.Buffer` before transmission.

```c
static void SendTxData(void)
{
	  /* USER CODE BEGIN SendTxData_1 */
	 HAL_GPIO_WritePin(GPIOB, GPIO_PIN_10, GPIO_PIN_SET);
	 HAL_Delay(2500);
	 UTIL_TIMER_Time_t nextTxIn = 0;

	#ifdef CAYENNE_LPP
	  uint8_t channel = 0;
	#else
	/*sensor value declerations */
		uint16_t batteryLevel = (uint16_t)readBatteryLevel();
		uint8_t batteryVolt = (uint8_t)(batteryLevel/10);

	    radar_uart_init();
	    Radar_Process_Pending_Data();
	   // Kalman_Process();
	    STM32CubeAI_Studio_AI_Process();

	  uint32_t i = 0;
	#endif /* CAYENNE_LPP */

	    APP_LOG(TS_ON, VLEVEL_L, "battery voltage  : %d mV\r\n", batteryLevel);
	    APP_LOG(TS_ON, VLEVEL_L, "distance for sent  : %d mm\r\n", (uint16_t)(current_distance));
	    APP_LOG(TS_ON, VLEVEL_L, "error_code for sent  : %d \r\n", corr_error_code);

	if (!init_flag) {
		log_data(LogTxData,previous_distance);
	} else {
		init_flag = false;
	}

	previous_distance = (uint16_t)(current_distance);

	    AppData.Port = LORAWAN_USER_APP_PORT;

	    // 2. Load the distance into the buffer (Big Endian format typically used for LoRaWAN)

	    AppData.Buffer[i++] = (previous_distance>> 8) & 0xFF;
	    AppData.Buffer[i++] = previous_distance& 0xFF;

	    AppData.Buffer[i++] = corr_error_code & 0xFF; // The error code byte
	    AppData.Buffer[i++] = batteryVolt & 0xFF; // The Battery Level byte

	uint8_t logIndex = 0;
	while (logIndex < log_size) {
		AppData.Buffer[i++] = (LogTxData[logIndex] >> 8) & 0xFF;
		AppData.Buffer[i++] = (LogTxData[logIndex]) & 0xFF;
		APP_PRINTF("distance_log %d : %d\n\r", logIndex,
				LogTxData[logIndex]);
		logIndex++;
	}

	    memset(global_radar_distance, 0, sizeof(global_radar_distance));
	    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_10, GPIO_PIN_RESET);

#ifdef CAYENNE_LPP
  CayenneLppReset();
  CayenneLppAddBarometricPressure(channel++, pressure);
  CayenneLppAddTemperature(channel++, temperature);
  CayenneLppAddRelativeHumidity(channel++, (uint16_t)(sensor_data.humidity));

  if ((LmHandlerParams.ActiveRegion != LORAMAC_REGION_US915) && (LmHandlerParams.ActiveRegion != LORAMAC_REGION_AU915)
      && (LmHandlerParams.ActiveRegion != LORAMAC_REGION_AS923))
  {
    CayenneLppAddDigitalInput(channel++, GetBatteryLevel());
    CayenneLppAddDigitalOutput(channel++, AppLedStateOn);
  }

  CayenneLppCopy(AppData.Buffer);
  AppData.BufferSize = CayenneLppGetSize();
#else  /* not CAYENNE_LPP */

  AppData.BufferSize = i;
#endif /* CAYENNE_LPP */

  if (LORAMAC_HANDLER_SUCCESS == LmHandlerSend(&AppData, LORAWAN_DEFAULT_CONFIRMED_MSG_STATE, &nextTxIn, false))
  {
    APP_LOG(TS_ON, VLEVEL_L, "SEND REQUEST\r\n");
  }
  else if (nextTxIn > 0)
  {
    APP_LOG(TS_ON, VLEVEL_L, "Next Tx in  : ~%d second(s)\r\n", (nextTxIn / 1000));
  }

  /* USER CODE END SendTxData_1 */
}
```

---

## 4. ChirpStack Decoder Script (JavaScript)

The following JavaScript decoder is configured in ChirpStack v3 to parse the incoming binary payload back into a structured JSON object.

```javascript
// ChirpStack v3 Decoder Entry Point
function Decode(fPort, bytes, variables) {
    var decoded = {};
    var offset = 0;

    // Ensure we have at least the 4 baseline bytes (Distance, Error, Battery)
    if (bytes.length < 4) {
        return { "error": "Payload too short" };
    }

    // 1. Current Distance (uint16)
    decoded.distance = (bytes[offset] << 8) | bytes[offset + 1];
    offset += 2;

    // 2. Error Code
    decoded.error_code = bytes[offset++];

    // 3. Battery
    decoded.battery_voltage = bytes[offset++] / 10;

    // 4. Error Description
    decoded.error_status = {
        0: "ok",
        1: "0 abort",
        2: "sensor timeout",
        3: "spike detected",
        4: "exceed limit",
        5: "sensor unstable",
        6: "predicted data"
    }[decoded.error_code] || "unknown";

    // 5. Log Data (Loops dynamically up to 16 times or until bytes run out)
    decoded.distance_logs = [];
    for (var i = 0; i < 16 && (offset + 1) < bytes.length; i++) {
        var value = (bytes[offset] << 8) | bytes[offset + 1];
        decoded.distance_logs.push(value);
        offset += 2;
    }

    return decoded;
}

// ChirpStack v3 Downlink Encoder Entry Point
// (Note: ChirpStack v3 uses 'Encode', not 'encodeDownlink')
function Encode(fPort, obj, variables) {
    return [225, 230, 255, 0];
}
```
