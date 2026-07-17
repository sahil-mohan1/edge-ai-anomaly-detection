/**
 * @file    datalogger_example.c
 * @brief   Example application showing datalogger usage
 * @author  AI Assistant
 * @date    2025-10-21
 * 
 * This example demonstrates:
 * - Basic initialization
 * - Debug string logging
 * - Structured sensor data logging
 * - Format definitions
 * - Sleep/wakeup cycles
 */

#include "datalogger.h"
#include <stdio.h>

/* Format IDs */
#define FORMAT_ID_BME680    1
#define FORMAT_ID_GPS       2
#define FORMAT_ID_BATTERY   3

/* Example sensor data structures */
typedef struct {
    float temperature;
    float humidity;
    float pressure;
    uint32_t gas_resistance;
} BME680_Data_t;

typedef struct {
    double latitude;
    double longitude;
    float altitude;
    float hdop;
} GPS_Data_t;

typedef struct {
    float voltage;
    int16_t current_ma;
    uint8_t percentage;
} Battery_Data_t;

/**
 * @brief Initialize data logger with custom configuration
 */
static void example_init_logger(void)
{
    DataLogger_Config_t config;
    
    // Get default configuration
    DataLogger_GetDefaultConfig(&config);
    
    // Customize for your application
    config.max_file_size_kb = 5000;              // 5 MB per file
    config.rotation_policy = ROTATION_POLICY_SIZE_AND_TIME;
    config.max_file_time_sec = 3600;             // Rotate every hour
    config.max_sd_usage_percent = 90;            // Use up to 90% of SD card
    config.enable_circular_logging = true;        // Auto-delete old files
    config.min_log_level = LOG_LEVEL_INFO;       // Filter debug messages
    config.enable_console_echo = true;           // Echo to console
    config.enable_sync_after_write = false;      // Batch writes for efficiency
    
    // Initialize
    if (DataLogger_InitWithConfig(&config) != DATALOGGER_OK) {
        printf("ERROR: Failed to initialize data logger\n");
        return;
    }
    
    DataLogger_LogInfo("Data logger initialized successfully\n");
}

/**
 * @brief Register all data formats
 */
static void example_register_formats(void)
{
    // Define BME680 sensor format
    DataLogger_Format_t bme680_format = {
        .format_id = FORMAT_ID_BME680,
        .format_name = "BME680_Environmental",
        .field_count = 4,
        .fields = {
            {"temperature", DATA_TYPE_FLOAT, 1, "C"},
            {"humidity", DATA_TYPE_FLOAT, 1, "%"},
            {"pressure", DATA_TYPE_FLOAT, 3, "hPa"},
            {"gas_resistance", DATA_TYPE_UINT32, 3, "ohm"}
        }
    };
    
    // Define GPS format
    DataLogger_Format_t gps_format = {
        .format_id = FORMAT_ID_GPS,
        .format_name = "GPS_Position",
        .field_count = 4,
        .fields = {
            {"latitude", DATA_TYPE_DOUBLE, 3, "deg"},
            {"longitude", DATA_TYPE_DOUBLE, 3, "deg"},
            {"altitude", DATA_TYPE_FLOAT, 1, "m"},
            {"hdop", DATA_TYPE_FLOAT, 0, ""}
        }
    };
    
    // Define battery format
    DataLogger_Format_t battery_format = {
        .format_id = FORMAT_ID_BATTERY,
        .format_name = "Battery_Status",
        .field_count = 3,
        .fields = {
            {"voltage", DATA_TYPE_FLOAT, 2, "V"},
            {"current", DATA_TYPE_INT16, 2, "mA"},
            {"percentage", DATA_TYPE_UINT8, 1, "%"}
        }
    };
    
    // Register all formats
    DataLogger_RegisterFormat(&bme680_format);
    DataLogger_RegisterFormat(&gps_format);
    DataLogger_RegisterFormat(&battery_format);
    
    DataLogger_LogInfo("All data formats registered\n");
}

/**
 * @brief Example: Log BME680 sensor data
 */
static void example_log_bme680(const BME680_Data_t *data)
{
    // Method 1: Using LogDataValues (automatic packing)
    const void *values[] = {
        &data->temperature,
        &data->humidity,
        &data->pressure,
        &data->gas_resistance
    };
    
    DataLogger_LogDataValues(FORMAT_ID_BME680, values);
    
    /* Method 2: Manual packing and LogData
    uint8_t packed[1 + 4 + 4 + 4 + 4];  // format_id + 4 floats/uint32
    uint16_t offset = 0;
    
    packed[offset++] = FORMAT_ID_BME680;
    memcpy(&packed[offset], &data->temperature, 4); offset += 4;
    memcpy(&packed[offset], &data->humidity, 4); offset += 4;
    memcpy(&packed[offset], &data->pressure, 4); offset += 4;
    memcpy(&packed[offset], &data->gas_resistance, 4); offset += 4;
    
    DataLogger_LogData(FORMAT_ID_BME680, packed, offset);
    */
}

/**
 * @brief Example: Log GPS data
 */
static void example_log_gps(const GPS_Data_t *data)
{
    const void *values[] = {
        &data->latitude,
        &data->longitude,
        &data->altitude,
        &data->hdop
    };
    
    DataLogger_LogDataValues(FORMAT_ID_GPS, values);
}

/**
 * @brief Example: Log battery status
 */
static void example_log_battery(const Battery_Data_t *data)
{
    const void *values[] = {
        &data->voltage,
        &data->current_ma,
        &data->percentage
    };
    
    DataLogger_LogDataValues(FORMAT_ID_BATTERY, values);
}

/**
 * @brief Example: Measurement cycle with health check
 */
static void example_measurement_cycle(void)
{
    // Simulated sensor readings
    BME680_Data_t bme680 = {
        .temperature = 25.5f,
        .humidity = 60.2f,
        .pressure = 1013.25f,
        .gas_resistance = 50000
    };
    
    GPS_Data_t gps = {
        .latitude = 37.7749,
        .longitude = -122.4194,
        .altitude = 52.0f,
        .hdop = 1.2f
    };
    
    Battery_Data_t battery = {
        .voltage = 3.75f,
        .current_ma = -50,
        .percentage = 75
    };
    
    // Log debug information
    DataLogger_LogInfo("Starting measurement cycle\n");
    
    // Log sensor data
    example_log_bme680(&bme680);
    example_log_gps(&gps);
    example_log_battery(&battery);
    
    // Check for warnings
    if (battery.voltage < 3.3f) {
        DataLogger_LogWarning("Low battery voltage: %.2f V\n", battery.voltage);
    }
    
    // Perform health check
    if (DataLogger_HealthCheck() != DATALOGGER_OK) {
        DataLogger_LogError("Logger health check failed\n");
    }
    
    DataLogger_LogInfo("Measurement cycle complete\n");
}

/**
 * @brief Example: Sleep and wakeup cycle
 */
static void example_sleep_wakeup(void)
{
    DataLogger_LogInfo("Preparing for sleep...\n");
    
    // Flush and close resources
    DataLogger_PrepareForSleep();
    
    // ... Enter low power mode here ...
    // HAL_PWR_EnterSLEEPMode(...);
    
    // ... Wakeup from sleep ...
    
    // Re-initialize logger
    if (DataLogger_Wakeup() != DATALOGGER_OK) {
        printf("ERROR: Failed to wake up logger\n");
        return;
    }
    
    DataLogger_LogInfo("Resumed from sleep\n");
}

/**
 * @brief Example: Get and display statistics
 */
static void example_display_stats(void)
{
    DataLogger_Stats_t stats;
    
    if (DataLogger_GetStats(&stats) != DATALOGGER_OK) {
        return;
    }
    
    DataLogger_LogInfo("=== Logger Statistics ===\n");
    DataLogger_LogInfo("Current file: %s\n", DataLogger_GetCurrentFilename());
    DataLogger_LogInfo("File size: %lu bytes\n", stats.current_file_size);
    DataLogger_LogInfo("Total packets: %lu\n", stats.total_packets_written);
    DataLogger_LogInfo("  Debug: %lu\n", stats.debug_packets);
    DataLogger_LogInfo("  Data: %lu\n", stats.data_packets);
    DataLogger_LogInfo("  Format: %lu\n", stats.format_packets);
    DataLogger_LogInfo("Write errors: %lu\n", stats.write_errors);
}

/**
 * @brief Example: Force file rotation
 */
static void example_force_rotation(void)
{
    DataLogger_LogInfo("Forcing file rotation...\n");
    
    if (DataLogger_ForceRotation() == DATALOGGER_OK) {
        DataLogger_LogInfo("Rotated to new file: %s\n", 
                          DataLogger_GetCurrentFilename());
    } else {
        DataLogger_LogError("File rotation failed\n");
    }
}

/**
 * @brief Main example function
 */
void datalogger_example_main(void)
{
    printf("=== Data Logger Example ===\n\n");
    
    // 1. Initialize logger
    printf("1. Initializing logger...\n");
    example_init_logger();
    
    // 2. Register data formats
    printf("2. Registering data formats...\n");
    example_register_formats();
    
    // 3. Perform measurement cycles
    printf("3. Running measurement cycles...\n");
    for (int i = 0; i < 10; i++) {
        example_measurement_cycle();
        HAL_Delay(1000);  // 1 second delay
    }
    
    // 4. Display statistics
    printf("4. Displaying statistics...\n");
    example_display_stats();
    
    // 5. Force file rotation
    printf("5. Testing file rotation...\n");
    example_force_rotation();
    
    // 6. Test sleep/wakeup
    printf("6. Testing sleep/wakeup...\n");
    example_sleep_wakeup();
    
    // 7. More measurements after wakeup
    printf("7. Continuing measurements...\n");
    for (int i = 0; i < 5; i++) {
        example_measurement_cycle();
        HAL_Delay(1000);
    }
    
    // 8. Final sync and cleanup
    printf("8. Final sync...\n");
    DataLogger_Sync();
    
    printf("\n=== Example Complete ===\n");
    printf("Check SD card for log files (LOG_*.bin)\n");
    printf("Use decoder tool to view contents:\n");
    printf("  python datalogger_decoder.py LOG_*.bin --txt output.txt\n");
}

/**
 * @brief Integration example with existing aqi_datalogger users
 * 
 * This shows how to migrate from the old aqi_datalogger API
 */
void migration_example(void)
{
    // Old: DataLogger_Init()
    // New: Same API, compatible!
    DataLogger_Init();
    
    // Old: DataLogger_Log("Message: %d\n", value)
    // New: DataLogger_LogInfo("Message: %d\n", value)
    int value = 42;
    DataLogger_LogInfo("Value: %d\n", value);
    
    // Old: DataLogger_PrepareForSleep()
    // New: Same API, compatible!
    DataLogger_PrepareForSleep();
    
    // Old: DataLogger_Wakeup()
    // New: Same API, compatible!
    DataLogger_Wakeup();
    
    // Old: DataLogger_Sync()
    // New: Same API, compatible!
    DataLogger_Sync();
    
    // OLD: Only plain text logging
    // NEW: Can now log structured binary data!
    BME680_Data_t sensor_data = {25.5f, 60.2f, 1013.25f, 50000};
    example_log_bme680(&sensor_data);
}
