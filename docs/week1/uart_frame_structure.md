# UART Frame Structure

This document details the byte-level structure of the UART protocol for the HLK-LD2413 sensor, based on Chapter 5 of the official user manual.

## 1. Real-Time Distance Reporting Frame
By default, the factory firmware continuously outputs the detected distance. 

| Frame Segment | Length | Byte Values (Hex) | Description |
| :--- | :--- | :--- | :--- |
| **Frame Header** | 4 Bytes | `F4 F3 F2 F1` | Standard reporting header. |
| **Data Length** | 2 Bytes | `04 00` | Indicates 4 bytes of payload (Little-endian). |
| **Payload (Distance)**| 4 Bytes | `XX XX XX XX` | Single-precision Float (IEEE 754) in Little-endian format representing the distance in millimeters (mm). |
| **Frame End** | 4 Bytes | `F8 F7 F6 F5` | Standard reporting tail. |

**Example Parsing:**
- Raw Data: `F4 F3 F2 F1 04 00 FD 3B FE 44 F8 F7 F6 F5`
- Distance Payload: `FD 3B FE 44` (Little-endian)
- Converted to Float: `2033.87 mm`

---

## 2. Command Protocol Frame (Host to Sensor)
When configuring the sensor (e.g., updating thresholds, changing reporting cycles), the host sends a command frame. 

| Frame Segment | Length | Byte Values (Hex) | Description |
| :--- | :--- | :--- | :--- |
| **Frame Header** | 4 Bytes | `FD FC FB FA` | Standard command header. |
| **Data Length** | 2 Bytes | `XX XX` | Length of the intra-frame data. |
| **Command Word** | 2 Bytes | `XX XX` | The specific command ID (e.g., `FF 00` for Enable Config). |
| **Command Value** | N Bytes | `...` | The parameter data (if applicable). |
| **Frame End** | 4 Bytes | `04 03 02 01` | Standard command tail. |

---

## 3. ACK Protocol Frame (Sensor to Host)
Whenever the host sends a command, the sensor replies with an Acknowledgment (ACK) frame.

| Frame Segment | Length | Byte Values (Hex) | Description |
| :--- | :--- | :--- | :--- |
| **Frame Header** | 4 Bytes | `FD FC FB FA` | Standard ACK header. |
| **Data Length** | 2 Bytes | `XX XX` | Length of the intra-frame data. |
| **Command Word** | 2 Bytes | `XX XX` | The command ID being acknowledged (e.g., `FF 01`). |
| **ACK Status** | 2 Bytes | `00 00` or `01 00` | `00 00` = Success, `01 00` = Failure. |
| **Return Value** | N Bytes | `...` | Optional returned parameters (e.g., reading a configuration). |
| **Frame End** | 4 Bytes | `04 03 02 01` | Standard ACK tail. |

### Important Commands:
- **Enable Configuration:** Command `0x00FF`, Value `0x0001` (Must be sent before any other config command).
- **End Configuration:** Command `0x00FE`, Value None (Returns sensor to normal working mode).
- **Set Reporting Cycle:** Command `0x0071`, Value: 2-byte integer (50 to 1000 ms).
