/**
  ******************************************************************************
  * @file    logger.c
  * @author  CDOH Team
  * @brief   Source file for the logging utility of the flood monitoring station.
  *          This file provides function implementations for logging different
  *          data types, including uint8, int16, float, etc.
  ******************************************************************************
  */

#include "logger.h"
#include <string.h>

#define BITS_PER_EVENT 2
#define EVENT_MASK  ((uint32_t)0x3)  // 0x3 = binary 11 for 2 bits


/**
  * @brief  Logs an 8-bit unsigned integer to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The 8-bit unsigned data to be logged.
  * @retval None
  */

void log_uint8(uint8_t *log_buffer, uint8_t new_data) {
    memmove(log_buffer + 1, log_buffer, (log_size - 1) * sizeof(uint8_t));
    log_buffer[0] = new_data;
}

/**
  * @brief  Logs an 8-bit signed integer to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The 8-bit signed data to be logged.
  * @retval None
  */
void log_int8(int8_t *log_buffer, int8_t new_data) {
    memmove(log_buffer + 1, log_buffer, (log_size - 1) * sizeof(int8_t));
    log_buffer[0] = new_data;
}

/**
  * @brief  Logs a 16-bit unsigned integer to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The 16-bit unsigned data to be logged.
  * @retval None
  */
void log_uint16(uint16_t *log_buffer, uint16_t new_data) {
    memmove(log_buffer + 1, log_buffer, (log_size - 1) * sizeof(uint16_t));
    log_buffer[0] = new_data;
}

/**
  * @brief  Logs a 16-bit signed integer to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The 16-bit signed data to be logged.
  * @retval None
  */
void log_int16(int16_t *log_buffer, int16_t new_data) {
    memmove(log_buffer + 1, log_buffer, (log_size - 1) * sizeof(int16_t));
    log_buffer[0] = new_data;
}

/**
  * @brief  Logs a 32-bit unsigned integer to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The 32-bit unsigned data to be logged.
  * @retval None
  */
void log_uint32(uint32_t *log_buffer, uint32_t new_data) {
    memmove(log_buffer + 1, log_buffer, (log_size - 1) * sizeof(uint32_t));
    log_buffer[0] = new_data;
}

/**
  * @brief  Logs a 32-bit signed integer to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The 32-bit signed data to be logged.
  * @retval None
  */
void log_int32(int32_t *log_buffer, int32_t new_data) {
    memmove(log_buffer + 1, log_buffer, (log_size - 1) * sizeof(int32_t));
    log_buffer[0] = new_data;
}

/**
  * @brief  Logs a 64-bit unsigned integer to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The 64-bit unsigned data to be logged.
  * @retval None
  */
void log_uint64(uint64_t *log_buffer, uint64_t new_data) {
    memmove(log_buffer + 1, log_buffer, (log_size - 1) * sizeof(uint64_t));
    log_buffer[0] = new_data;
}

/**
  * @brief  Logs a 64-bit signed integer to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The 64-bit signed data to be logged.
  * @retval None
  */
void log_int64(int64_t *log_buffer, int64_t new_data) {
    memmove(log_buffer + 1, log_buffer, (log_size - 1) * sizeof(int64_t));
    log_buffer[0] = new_data;
}

/**
  * @brief  Logs a floating-point value to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The float data to be logged.
  * @retval None
  */
void log_float(float *log_buffer, float new_data) {
    memmove(log_buffer + 1, log_buffer, (log_size - 1) * sizeof(float));
    log_buffer[0] = new_data;
}

/**
  * @brief  Logs a double-precision floating-point value to the provided buffer.
  * @param  log_buffer: Pointer to the buffer that stores log data.
  * @param  new_data: The double data to be logged.
  * @retval None
  */
void log_double(double *log_buffer, double new_data) {
    memmove(log_buffer + 1, log_buffer, (log_size - 1) * sizeof(double));
    log_buffer[0] = new_data;
}

/*
 * Updates the log for an unsigned 2-bit event.
 * The log is shifted left by 2 bits and the new event is inserted at index 0.
 * Only the most recent 'maxEvents' events are retained.
 */
void updateLogUnsigned(uint32_t *logData, unsigned int newEvent, unsigned int maxEvents)
{
    // Calculate total bits used for maxEvents.
    unsigned int totalBits = maxEvents * BITS_PER_EVENT;
    // Create a mask to keep only the lower totalBits.
    uint32_t log_mask = (totalBits == 32) ? 0xFFFFFFFF : (((uint32_t)1 << totalBits) - 1);

    // Ensure the new event fits in 2 bits.
    newEvent &= EVENT_MASK;
    // Shift the log left by 2 bits and OR in the new event.
    *logData = ((*logData << BITS_PER_EVENT) | newEvent) & log_mask;
}

/*
 * Retrieves an unsigned event from the 32-bit log.
 * Shifts right by (index * 2) bits and applies a mask.
 */
uint32_t getLoggedEventUnsigned(uint32_t logData, unsigned int index, unsigned int maxEvents)
{
    (void)maxEvents; // maxEvents is used during update; here index determines the shift.
    return (logData >> (index * BITS_PER_EVENT)) & EVENT_MASK;
}
