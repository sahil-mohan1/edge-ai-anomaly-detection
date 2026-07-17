/**
 * ChirpStack LoRaWAN Codec for AQI Prototype v2.2
 * 
 * Decodes compressed sensor data from STM32WLE5 AQI air quality monitoring device
 * 
 * Payload Structure: 47 bytes
 * - BME690 Gas Sensor (IAQ, CO2, VOC, Temp, Humidity, Pressure)
 * - BMV080 Particulate Matter (PM1.0, PM2.5, PM10)
 * - INA219 Power Monitors (Solar & Battery voltage/current)
 * - NavIC GNSS (Location, satellites, accuracy)
 * - Status flags and accuracies
 * - Unix timestamp
 * 
 * InfluxDB Compatibility:
 * - ALL fields return consistent numeric types (float/integer) or strings
 * - Accuracy fields use numeric codes 0-3 (0=Stabilizing, 1=Low, 2=Medium, 3=High)
 * - Boolean fields use 0/1 integers (not true/false)
 * - GPS coordinates ONLY included when valid fix exists (prevents 0,0 on maps)
 * - Only decodes fPort 2 payloads (returns raw for other ports)
 * - Timestamp converted to IST (UTC+5:30) format strings
 * 
 * Timestamp Fields:
 * - timestamp_unix: Unix timestamp (integer)
 * - timestamp_ist_date: Date in IST (YYYY-MM-DD)
 * - timestamp_ist_time: Time in IST (HH:MM:SS)
 * - timestamp_ist_datetime: Full datetime in IST (YYYY-MM-DD HH:MM:SS IST)
 * 
 * @author Generated for E5-Mini AQI Project
 * @date October 10, 2025
 */

/**
 * Decode uplink function
 * 
 * @param {object} input
 * @param {number[]} input.bytes Byte array containing the uplink payload
 * @param {number} input.fPort Uplink fPort
 * @param {Record<string, string>} input.variables Device variables
 * 
 * @returns {{data: object}} Decoded payload with all sensor readings
 */
function decodeUplink(input) {
  const bytes = input.bytes;
  const fPort = input.fPort;
  
  // Only decode on fPort 2 - return raw bytes for other ports
  if (fPort !== 2) {
    return {
      data: {
        raw_payload: Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('')
      },
      warnings: [`Payload received on fPort ${fPort}, expected fPort 2. Returning raw data.`]
    };
  }
  
  // Validate payload length
  if (bytes.length < 47) {
    return {
      errors: [`Invalid payload length: ${bytes.length} bytes (expected 47)`],
      warnings: ["Incomplete sensor data"]
    };
  }

  let offset = 0;

  // Helper function: Read uint16 big-endian
  const readUint16 = () => {
    const value = (bytes[offset] << 8) | bytes[offset + 1];
    offset += 2;
    return value;
  };

  // Helper function: Read int16 big-endian (two's complement)
  const readInt16 = () => {
    const value = (bytes[offset] << 8) | bytes[offset + 1];
    offset += 2;
    return value > 0x7FFF ? value - 0x10000 : value;
  };

  // Helper function: Read uint32 big-endian
  const readUint32 = () => {
    const value = (bytes[offset] << 24) | (bytes[offset + 1] << 16) | 
                  (bytes[offset + 2] << 8) | bytes[offset + 3];
    offset += 4;
    return value >>> 0; // Ensure unsigned
  };

  // Helper function: Read int32 big-endian (two's complement)
  const readInt32 = () => {
    const value = (bytes[offset] << 24) | (bytes[offset + 1] << 16) | 
                  (bytes[offset + 2] << 8) | bytes[offset + 3];
    offset += 4;
    return value;
  };

  // Helper function: Read uint8
  const readUint8 = () => bytes[offset++];

  // ===========================================================================
  // DECODE BME690 GAS SENSOR DATA (14 bytes)
  // ===========================================================================
  
  const iaq = readUint16() / 10.0;                    // Indoor Air Quality (0-500 scale)
  const static_iaq = readUint16() / 10.0;             // Static IAQ
  const co2_equivalent = readUint16();                // CO2 equivalent (ppm)
  const breath_voc_equivalent = readUint16() / 100.0; // Breath VOC (ppm)
  const temperature = readInt16() / 100.0;            // Temperature (°C)
  const humidity = readUint16() / 100.0;              // Relative Humidity (%)
  
  // Pressure: Add back the 90000 Pa offset
  const PRESSURE_OFFSET_PA = 90000;
  const pressure_raw = readUint16();
  const pressure = pressure_raw + PRESSURE_OFFSET_PA; // Pressure (Pa)
  const pressure_hPa = pressure / 100.0;              // Convert to hPa for convenience

  // ===========================================================================
  // DECODE BMV080 PARTICULATE MATTER DATA (6 bytes)
  // ===========================================================================
  
  const pm1_0 = readUint16();  // PM1.0 (µg/m³)
  const pm2_5 = readUint16();  // PM2.5 (µg/m³)
  const pm10 = readUint16();   // PM10 (µg/m³)

  // ===========================================================================
  // DECODE INA219 POWER MONITOR DATA (8 bytes)
  // ===========================================================================
  
  const solar_voltage = readUint16() / 1000.0;    // Solar panel voltage (V)
  const solar_current = readInt16() / 10.0;       // Solar panel current (mA)
  const solar_power = solar_voltage * solar_current; // Solar power (mW)
  
  const battery_voltage = readUint16() / 1000.0;  // Battery voltage (V)
  const battery_current = readInt16() / 10.0;     // Battery current (mA)
  const battery_power = battery_voltage * battery_current; // Battery power (mW)

  // ===========================================================================
  // DECODE NAVIC GNSS DATA (11 bytes)
  // ===========================================================================
  
  const latitude = readInt32() / 1000000.0;   // Latitude (decimal degrees)
  const longitude = readInt32() / 1000000.0;  // Longitude (decimal degrees)
  const altitude = readInt16();               // Altitude (meters)
  const satellites_used = readUint8();        // Number of satellites
  const hdop = readUint8() / 10.0;            // Horizontal Dilution of Precision

  // ===========================================================================
  // DECODE STATUS AND ACCURACY FLAGS (4 bytes)
  // ===========================================================================
  
  // Byte 40: IAQ and Static IAQ accuracies (nibbles)
  const accuracies1 = readUint8();
  const iaq_accuracy = (accuracies1 >> 4) & 0x0F;
  const static_iaq_accuracy = accuracies1 & 0x0F;

  // Byte 41: CO2 and Breath VOC accuracies (nibbles)
  const accuracies2 = readUint8();
  const co2_accuracy = (accuracies2 >> 4) & 0x0F;
  const breath_voc_accuracy = accuracies2 & 0x0F;

  // Byte 42: TVOC accuracy (high nibble)
  const accuracies3 = readUint8();
  const tvoc_accuracy = (accuracies3 >> 4) & 0x0F;

  // Byte 43: Status byte (bitfield)
  const status_byte = readUint8();
  const stabilization_status = (status_byte >> 0) & 0x01;  // 0=ongoing, 1=complete
  const run_in_status = (status_byte >> 1) & 0x01;         // 0=ongoing, 1=complete
  const is_obstructed = (status_byte >> 2) & 0x01;         // 0=clear, 1=obstructed
  const fix_quality = (status_byte >> 3) & 0x0F;           // GPS fix quality (0-15)

  // ===========================================================================
  // DECODE UNIX TIMESTAMP (4 bytes)
  // ===========================================================================
  
  const timestamp = readUint32();  // Unix timestamp (seconds since epoch)
  
  // Convert to ISO 8601 string for convenience
  const timestamp_iso = timestamp > 0 ? new Date(timestamp * 1000).toISOString() : "Invalid";

  // ===========================================================================
  // HELPER FUNCTIONS FOR INTERPRETATION
  // ===========================================================================

  // Convert Unix timestamp to IST (UTC+5:30)
  const convertToIST = (unixTimestamp) => {
    if (unixTimestamp === 0 || unixTimestamp < 946684800) {
      return {
        date: "Invalid",
        time: "Invalid",
        datetime: "Invalid"
      };
    }
    
    // Create Date object from Unix timestamp (in seconds)
    const date = new Date(unixTimestamp * 1000);
    
    // IST is UTC+5:30 (330 minutes offset)
    const istOffset = 330; // minutes
    const utcTime = date.getTime() + (date.getTimezoneOffset() * 60000);
    const istTime = new Date(utcTime + (istOffset * 60000));
    
    // Format: YYYY-MM-DD
    const year = istTime.getFullYear();
    const month = String(istTime.getMonth() + 1).padStart(2, '0');
    const day = String(istTime.getDate()).padStart(2, '0');
    const dateStr = `${year}-${month}-${day}`;
    
    // Format: HH:MM:SS
    const hours = String(istTime.getHours()).padStart(2, '0');
    const minutes = String(istTime.getMinutes()).padStart(2, '0');
    const seconds = String(istTime.getSeconds()).padStart(2, '0');
    const timeStr = `${hours}:${minutes}:${seconds}`;
    
    // Format: YYYY-MM-DD HH:MM:SS IST
    const datetimeStr = `${dateStr} ${timeStr} IST`;
    
    return {
      date: dateStr,
      time: timeStr,
      datetime: datetimeStr
    };
  };

  // ===========================================================================
  // RETURN DECODED DATA
  // ===========================================================================
  
  // Check if GPS has valid fix
  const gps_has_fix = fix_quality > 0 && satellites_used > 0 && 
                      (latitude !== 0 || longitude !== 0);

  // Convert timestamp to IST
  const ist_time = convertToIST(timestamp);

  // Build categorized data structure
  const decodedData = {
    // Air Quality (BME690 Gas Sensor)
    air_quality: {
      iaq: parseFloat(iaq.toFixed(1)),
      iaq_accuracy: iaq_accuracy,
      static_iaq: parseFloat(static_iaq.toFixed(1)),
      static_iaq_accuracy: static_iaq_accuracy,
      co2_equivalent: co2_equivalent,
      co2_accuracy: co2_accuracy,
      bvoc: parseFloat(breath_voc_equivalent.toFixed(2)),
      bvoc_accuracy: breath_voc_accuracy,
      tvoc_accuracy: tvoc_accuracy,
      stabilization_status: stabilization_status,
      run_in_status: run_in_status
    },
    
    // Environment (Temperature, Humidity, Pressure)
    environment: {
      temperature: parseFloat(temperature.toFixed(2)),
      humidity: parseFloat(humidity.toFixed(2)),
      pressure: parseFloat(pressure_hPa.toFixed(2))
    },
    
    // Particulate Matter (BMV080)
    particulate_matter: {
      pm1: pm1_0,
      pm2_5: pm2_5,
      pm10: pm10,
      sensor_obstructed: is_obstructed
    },
    
    // Power System (INA219)
    power: {
      solar_voltage: parseFloat(solar_voltage.toFixed(3)),
      solar_current: parseFloat(solar_current.toFixed(1)),
      solar_power: parseFloat(solar_power.toFixed(2)),
      battery_voltage: parseFloat(battery_voltage.toFixed(3)),
      battery_current: parseFloat(battery_current.toFixed(1)),
      battery_power: parseFloat(battery_power.toFixed(2))
    },
    
    // Location (NavIC GNSS)
    location: {
      altitude: altitude,
      fix_quality: fix_quality,
      satellites_used: satellites_used,
      hdop: parseFloat(hdop.toFixed(1)),
      valid_fix: gps_has_fix ? 1 : 0
    },
    
    // Timestamp
    timestamp: {
      date: ist_time.date,
      time: ist_time.time,
      datetime: ist_time.datetime,
      unix: timestamp
    }
  };
  
  // Only include lat/long if GPS has valid fix (avoid 0,0 on map)
  if (gps_has_fix) {
    decodedData.location.latitude = parseFloat(latitude.toFixed(6));
    decodedData.location.longitude = parseFloat(longitude.toFixed(6));
  }

  return {
    data: decodedData
  };
}

/**
 * Encode downlink function
 * 
 * @param {object} input
 * @param {object} input.data Payload to be encoded
 * @param {Record<string, string>} input.variables Device variables
 * 
 * @returns {{bytes: number[]}} Encoded downlink payload
 */
function encodeDownlink(input) {
  // Example downlink commands:
  // - Command 0x01: Set measurement interval (minutes)
  // - Command 0x02: Request immediate transmission
  // - Command 0x03: Set LoRaWAN data rate
  // - Command 0xFF: Reset device
  
  const data = input.data;
  
  if (data.command === "set_interval" && data.interval_minutes) {
    return {
      bytes: [
        0x01,  // Command: Set interval
        data.interval_minutes & 0xFF  // Interval in minutes
      ],
      fPort: 2  // Use fPort 2 for downlink commands
    };
  }
  
  if (data.command === "request_transmission") {
    return {
      bytes: [0x02],  // Command: Request immediate transmission
      fPort: 2
    };
  }
  
  if (data.command === "set_data_rate" && data.data_rate !== undefined) {
    return {
      bytes: [
        0x03,  // Command: Set data rate
        data.data_rate & 0x0F  // Data rate (DR0-DR15)
      ],
      fPort: 2
    };
  }
  
  if (data.command === "reset") {
    return {
      bytes: [0xFF],  // Command: Reset device
      fPort: 2
    };
  }
  
  // Default: Empty downlink
  return {
    bytes: [],
    errors: ["Unknown command or missing parameters"]
  };
}

/**
 * Test function to validate codec with sample data
 * (Not used by ChirpStack, for development only)
 */
function testCodec() {
  console.log("=== Test 1: Valid payload on fPort 2 (no GPS fix) ===");
  const sampleBytes1 = [
    0x00, 0x00,  // IAQ = 0.0
    0x00, 0x00,  // Static IAQ = 0.0
    0x00, 0x00,  // CO2 = 0 ppm
    0x00, 0x00,  // Breath VOC = 0.0 ppm
    0x00, 0x00,  // Temp = 0.0°C
    0x00, 0x00,  // Humidity = 0.0%
    0x00, 0x00,  // Pressure offset = 0
    0x00, 0x00,  // PM1.0 = 0
    0x00, 0x00,  // PM2.5 = 0
    0x00, 0x00,  // PM10 = 0
    0x00, 0x24,  // Solar voltage = 0.036V
    0x00, 0x02,  // Solar current = 0.2mA
    0x0D, 0xA4,  // Battery voltage = 3.492V
    0x0C, 0x4C,  // Battery current = 314.0mA
    0x00, 0x00, 0x00, 0x00,  // Latitude = 0
    0x00, 0x00, 0x00, 0x00,  // Longitude = 0
    0x00, 0x00,  // Altitude = 0
    0x00,        // Satellites = 0
    0x00,        // HDOP = 0.0
    0x00,        // Accuracies 1
    0x00,        // Accuracies 2
    0x00,        // Accuracies 3
    0x00,        // Status byte
    0x00, 0x00, 0x00, 0x00  // Timestamp = 0
  ];
  
  const result1 = decodeUplink({ bytes: sampleBytes1, fPort: 2, variables: {} });
  console.log(JSON.stringify(result1, null, 2));
  console.log("Note: gps_latitude and gps_longitude should NOT be present (no fix)\n");
  
  console.log("=== Test 2: Wrong fPort (should return raw) ===");
  const result2 = decodeUplink({ bytes: [0x01, 0x02, 0x03], fPort: 1, variables: {} });
  console.log(JSON.stringify(result2, null, 2));
  console.log();
  
  console.log("=== Test 3: Valid payload with GPS fix and IST timestamp ===");
  const sampleBytes3 = [
    0x00, 0xC8,  // IAQ = 20.0
    0x00, 0xC8,  // Static IAQ = 20.0
    0x01, 0xF4,  // CO2 = 500 ppm
    0x00, 0x64,  // Breath VOC = 1.0 ppm
    0x0B, 0xB8,  // Temp = 30.0°C
    0x18, 0x6A,  // Humidity = 62.5%
    0x1B, 0x58,  // Pressure offset = 7000 (97000 Pa total)
    0x00, 0x0A,  // PM1.0 = 10
    0x00, 0x14,  // PM2.5 = 20
    0x00, 0x1E,  // PM10 = 30
    0x01, 0x2C,  // Solar voltage = 0.3V
    0x00, 0x64,  // Solar current = 10mA
    0x0E, 0x74,  // Battery voltage = 3.7V
    0x0D, 0xAC,  // Battery current = 350mA
    0x00, 0xC3, 0x50, 0xE8,  // Latitude = 12.789 degrees
    0x02, 0x79, 0x22, 0x80,  // Longitude = 77.123 degrees
    0x01, 0xF4,  // Altitude = 500m
    0x08,        // Satellites = 8
    0x0F,        // HDOP = 1.5
    0x33,        // Accuracies 1: IAQ=3, Static IAQ=3
    0x33,        // Accuracies 2: CO2=3, VOC=3
    0x30,        // Accuracies 3: TVOC=3
    0x19,        // Status: stabilized(1), run-in(1), clear(0), fix=1
    0x67, 0x14, 0x5C, 0x80  // Timestamp = 1729000000 (Oct 15, 2024 ~19:43:20 IST)
  ];
  
  const result3 = decodeUplink({ bytes: sampleBytes3, fPort: 2, variables: {} });
  console.log(JSON.stringify(result3, null, 2));
  console.log("Note: gps_latitude, gps_longitude SHOULD be present (valid fix)");
  console.log("Note: timestamp_ist_date, timestamp_ist_time, timestamp_ist_datetime show IST time\n");
}

// Uncomment to test locally with Node.js:
// testCodec();
