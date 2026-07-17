/**
  ******************************************************************************
  * @file    logger.h
  * @author  CDOH Team
  * @brief   Header file for the logging utility of the flood monitoring station.
  *          This file provides definitions and function prototypes for managing
  *          logging of different data types such as uint8, int16, float, etc.
  *
  * @verbatim
  ==============================================================================
                        ##### How to use this driver #####
  ==============================================================================
  (1) Include "logger.h" in your application to access logging functionality.
  (2) Define a buffer to store log data, e.g., uint8_t log_buffer[log_size];
  (3) Call log_data(buffer, value) to log different data types to the specified buffer.
  (4) Call UPDATE_PACKED_LOG(&logData, newEvent, maxEvents) to log compressed data
  (5) Call GET_LOGGED_PACKED_EVENT to retrieve the packed data
      For example:
          - log_data(log_buffer, data); // Use the generic macro for any data type.
  ******************************************************************************
  */

#ifndef APPLICATION_AUTOMATIC_LEVEL_MONITORING_STATION_INC_LOGGER_H_
#define APPLICATION_AUTOMATIC_LEVEL_MONITORING_STATION_INC_LOGGER_H_

#include <stdint.h>
#include <stddef.h>

// Size of the log buffer
#define log_size					16

/* Function Prototypes for Logging Different Data Types */

/**
  * @brief  Logs an 8-bit unsigned integer to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The 8-bit unsigned data to be logged.
  * @retval None
  */

void log_uint8(uint8_t *log_buffer, uint8_t new_data);

/**
  * @brief  Logs an 8-bit signed integer to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The 8-bit signed data to be logged.
  * @retval None
  */

void log_int8(int8_t *log_buffer, int8_t new_data);

/**
  * @brief  Logs a 16-bit unsigned integer to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The 16-bit unsigned data to be logged.
  * @retval None
  */

void log_uint16(uint16_t *log_buffer, uint16_t new_data);

/**
  * @brief  Logs a 16-bit signed integer to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The 16-bit signed data to be logged.
  * @retval None
  */

void log_int16(int16_t *log_buffer, int16_t new_data);

/**
  * @brief  Logs a 32-bit unsigned integer to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The 32-bit unsigned data to be logged.
  * @retval None
  */

void log_uint32(uint32_t *log_buffer, uint32_t new_data);

/**
  * @brief  Logs a 32-bit signed integer to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The 32-bit signed data to be logged.
  * @retval None
  */

void log_int32(int32_t *log_buffer, int32_t new_data);


/**
  * @brief  Logs a 64-bit unsigned integer to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The 64-bit unsigned data to be logged.
  * @retval None
  */

void log_uint64(uint64_t *log_buffer, uint64_t new_data);

/**
  * @brief  Logs a 64-bit signed integer to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The 64-bit signed data to be logged.
  * @retval None
  */

void log_int64(int64_t *log_buffer, int64_t new_data);

/**
  * @brief  Logs a floating-point value to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The float data to be logged.
  * @retval None
  */

void log_float(float *log_buffer, float new_data);

/**
  * @brief  Logs a double-precision floating-point value to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The double data to be logged.
  * @retval None
  */

void log_double(double *log_buffer, double new_data);

/* Generic Macro for Logging */
/**
  * @brief  Logs new data to the provided buffer based on its type.
  *         Uses a generic macro to select the appropriate logging function.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The data to be logged. This can be of multiple types (e.g., uint8_t, int16_t).
  * @retval None
  */

#define log_data(log_buffer, new_data) _Generic((new_data), \
    uint8_t: log_uint8, \
    int8_t: log_int8, \
    uint16_t: log_uint16, \
    int16_t: log_int16, \
    uint32_t: log_uint32, \
    int32_t: log_int32, \
    uint64_t: log_uint64, \
    int64_t: log_int64, \
    float: log_float, \
    double: log_double \
)(log_buffer, new_data)

/*
 * Updates the 32-bit log for an unsigned 2-bit event.
 * Parameters:
 *   logData   - Pointer to the 32-bit log storage.
 *   newEvent  - New event value (unsigned) to be inserted (0..3).
 *   maxEvents - Maximum number of events to retain (1 to 16).
 */
void updateLogUnsigned(uint32_t *logData, unsigned int newEvent, unsigned int maxEvents);

/*
 * Retrieves an unsigned event from the 32-bit log.
 * Parameters:
 *   logData   - 32-bit log storage.
 *   index     - Event index to retrieve (0 is the most recent).
 *   maxEvents - Maximum number of events stored (1 to 16).
 * Returns:
 *   The uint32_t event value (0..3).
 */
uint32_t getLoggedEventUnsigned(uint32_t logData, unsigned int index, unsigned int maxEvents);

/*
 * UPDATE_PACKED_LOG:
 * Inserts a new unsigned event into the 32-bit log.
 * Usage:
 *   UPDATE_PACKED_LOG(&logData, newEvent, maxEvents);
 */
#define UPDATE_PACKED_LOG(logData, newEvent, maxEvents) \
		updateLogUnsigned(logData, newEvent, maxEvents)

/*
 * GET_LOGGED_PACKED_EVENT:
 * Retrieves an unsigned event from the 32-bit log.
 * Usage:
 *   unsigned int event = GET_LOGGED_PACKED_EVENT(logData, index, maxEvents);
 */
#define GET_LOGGED_PACKED_EVENT(logData, index, maxEvents) \
		getLoggedEventUnsigned(logData, index, maxEvents)


#endif /* APPLICATION_AUTOMATIC_LEVEL_MONITORING_STATION_INC_LOGGER_H_ */
