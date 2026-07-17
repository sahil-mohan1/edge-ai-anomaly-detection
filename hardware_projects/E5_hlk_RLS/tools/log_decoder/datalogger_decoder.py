#!/usr/bin/env python3
"""
Binary Data Logger Decoder Tool
Decodes binary log files created by the embedded datalogger system
Supports export to CSV, TXT, and JSON formats

Author: AI Assistant
Version: 1.0.0
Date: 2025-10-21
"""

import struct
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from enum import IntEnum

# Constants matching C definitions
DATALOGGER_PACKET_SYNC = 0xAA55
DATALOGGER_FILE_MAGIC = 0x444C4F47  # "DLOG"

class PacketType(IntEnum):
    """Packet types"""
    DEBUG_STRING = 0x01
    STRUCTURED_DATA = 0x02
    FORMAT_DEFINITION = 0x03
    FILE_HEADER = 0x04

class LogLevel(IntEnum):
    """Debug log levels"""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4

class DataType(IntEnum):
    """Data types for structured logging"""
    INT8 = 0
    UINT8 = 1
    INT16 = 2
    UINT16 = 3
    INT32 = 4
    UINT32 = 5
    FLOAT = 6
    DOUBLE = 7

# Data type sizes and struct formats
DATA_TYPE_INFO = {
    DataType.INT8: (1, 'b'),
    DataType.UINT8: (1, 'B'),
    DataType.INT16: (2, 'h'),
    DataType.UINT16: (2, 'H'),
    DataType.INT32: (4, 'i'),
    DataType.UINT32: (4, 'I'),
    DataType.FLOAT: (4, 'f'),
    DataType.DOUBLE: (8, 'd'),
}

class BinaryLogDecoder:
    """Decoder for binary log files"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.formats: Dict[int, Dict] = {}  # Format registry
        self.packets: List[Dict] = []  # Decoded packets
        self.file_info: Optional[Dict] = None
        
    def decode(self) -> bool:
        """Decode the entire log file"""
        try:
            with open(self.filename, 'rb') as f:
                while True:
                    packet = self._read_packet(f)
                    if packet is None:
                        break
                    self.packets.append(packet)
            
            print(f"Successfully decoded {len(self.packets)} packets")
            return True
            
        except Exception as e:
            print(f"Error decoding file: {e}")
            return False
    
    def _read_packet(self, f) -> Optional[Dict]:
        """Read and decode a single packet"""
        # Read packet header
        header_data = f.read(12)  # sizeof(DataLogger_PacketHeader_t)
        if len(header_data) < 12:
            return None  # EOF
        
        # Unpack header (little-endian)
        sync, pkt_type, flags, timestamp, payload_len, crc16 = struct.unpack(
            '<HBBIHH', header_data
        )
        
        # Verify sync marker
        if sync != DATALOGGER_PACKET_SYNC:
            print(f"Warning: Invalid sync marker: 0x{sync:04X}")
            return None
        
        # Read payload
        payload = f.read(payload_len)
        if len(payload) < payload_len:
            print(f"Warning: Truncated payload")
            return None
        
        # Verify CRC (simplified - just checking)
        calculated_crc = self._calculate_crc16(payload)
        if calculated_crc != crc16:
            print(f"Warning: CRC mismatch (expected: 0x{crc16:04X}, got: 0x{calculated_crc:04X})")
        
        # Decode based on packet type
        packet = {
            'timestamp': timestamp,
            'timestamp_str': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
            'type': PacketType(pkt_type).name,
            'flags': flags,
        }
        
        if pkt_type == PacketType.FILE_HEADER:
            packet['data'] = self._decode_file_header(payload)
            self.file_info = packet['data']
        elif pkt_type == PacketType.DEBUG_STRING:
            packet['data'] = self._decode_debug_string(payload)
        elif pkt_type == PacketType.FORMAT_DEFINITION:
            packet['data'] = self._decode_format_definition(payload)
        elif pkt_type == PacketType.STRUCTURED_DATA:
            packet['data'] = self._decode_structured_data(payload)
        else:
            packet['data'] = {'raw': payload.hex()}
        
        return packet
    
    def _decode_file_header(self, payload: bytes) -> Dict:
        """Decode file header packet"""
        magic, ver_major, ver_minor, ver_patch, reserved, creation_time = struct.unpack(
            '<IBBBBL', payload[:12]
        )
        device_id = payload[12:28].decode('utf-8', errors='ignore').rstrip('\x00')
        
        return {
            'magic': f"0x{magic:08X}",
            'version': f"{ver_major}.{ver_minor}.{ver_patch}",
            'creation_time': datetime.fromtimestamp(creation_time).strftime('%Y-%m-%d %H:%M:%S'),
            'device_id': device_id,
        }
    
    def _decode_debug_string(self, payload: bytes) -> Dict:
        """Decode debug string packet"""
        level = LogLevel(payload[0])
        message = payload[1:].decode('utf-8', errors='ignore')
        
        return {
            'level': level.name,
            'message': message,
        }
    
    def _decode_format_definition(self, payload: bytes) -> Dict:
        """Decode format definition packet"""
        offset = 0
        
        # Format ID
        format_id = payload[offset]
        offset += 1
        
        # Format name
        name_len = payload[offset]
        offset += 1
        format_name = payload[offset:offset+name_len].decode('utf-8', errors='ignore')
        offset += name_len
        
        # Field count
        field_count = payload[offset]
        offset += 1
        
        # Fields
        fields = []
        for _ in range(field_count):
            # Field name
            field_name_len = payload[offset]
            offset += 1
            field_name = payload[offset:offset+field_name_len].decode('utf-8', errors='ignore')
            offset += field_name_len
            
            # Data type
            data_type = DataType(payload[offset])
            offset += 1
            
            # Unit
            unit_len = payload[offset]
            offset += 1
            unit = ''
            if unit_len > 0:
                unit = payload[offset:offset+unit_len].decode('utf-8', errors='ignore')
                offset += unit_len
            
            fields.append({
                'name': field_name,
                'type': data_type.name,
                'unit': unit,
            })
        
        # Register format for future structured data packets
        self.formats[format_id] = {
            'id': format_id,
            'name': format_name,
            'fields': fields,
        }
        
        return self.formats[format_id]
    
    def _decode_structured_data(self, payload: bytes) -> Dict:
        """Decode structured data packet"""
        format_id = payload[0]
        
        if format_id not in self.formats:
            return {
                'format_id': format_id,
                'error': 'Format not found',
                'raw': payload[1:].hex(),
            }
        
        fmt = self.formats[format_id]
        offset = 1
        values = {}
        
        for field in fmt['fields']:
            data_type = DataType[field['type']]
            size, struct_fmt = DATA_TYPE_INFO[data_type]
            
            if offset + size > len(payload):
                values[field['name']] = 'TRUNCATED'
                break
            
            value = struct.unpack('<' + struct_fmt, payload[offset:offset+size])[0]
            offset += size
            
            # Format value with unit
            if field['unit']:
                values[field['name']] = f"{value} {field['unit']}"
            else:
                values[field['name']] = value
        
        return {
            'format_id': format_id,
            'format_name': fmt['name'],
            'values': values,
        }
    
    def _calculate_crc16(self, data: bytes) -> int:
        """Calculate CRC16-CCITT"""
        crc = 0xFFFF
        poly = 0x1021
        
        for byte in data:
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ poly) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        
        return crc
    
    def export_to_csv(self, output_file: str):
        """Export decoded packets to CSV"""
        import csv
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['Timestamp', 'Type', 'Content'])
            
            # Write packets
            for pkt in self.packets:
                ts = pkt['timestamp_str']
                pkt_type = pkt['type']
                
                if pkt_type == 'DEBUG_STRING':
                    content = f"[{pkt['data']['level']}] {pkt['data']['message']}"
                elif pkt_type == 'STRUCTURED_DATA':
                    content = f"{pkt['data'].get('format_name', 'Unknown')}: {pkt['data']['values']}"
                elif pkt_type == 'FORMAT_DEFINITION':
                    content = f"Format: {pkt['data']['name']}"
                else:
                    content = str(pkt['data'])
                
                writer.writerow([ts, pkt_type, content])
        
        print(f"Exported to CSV: {output_file}")
    
    def export_to_txt(self, output_file: str):
        """Export decoded packets to readable text file"""
        with open(output_file, 'w') as f:
            # Write file header if available
            if self.file_info:
                f.write("=" * 70 + "\n")
                f.write(f"Log File: {self.filename}\n")
                f.write(f"Device: {self.file_info.get('device_id', 'Unknown')}\n")
                f.write(f"Version: {self.file_info.get('version', 'Unknown')}\n")
                f.write(f"Created: {self.file_info.get('creation_time', 'Unknown')}\n")
                f.write("=" * 70 + "\n\n")
            
            # Write packets
            for pkt in self.packets:
                f.write(f"[{pkt['timestamp_str']}] {pkt['type']}\n")
                
                if pkt['type'] == 'DEBUG_STRING':
                    f.write(f"  [{pkt['data']['level']}] {pkt['data']['message']}\n")
                elif pkt['type'] == 'STRUCTURED_DATA':
                    f.write(f"  Format: {pkt['data'].get('format_name', 'Unknown')}\n")
                    for key, val in pkt['data']['values'].items():
                        f.write(f"    {key}: {val}\n")
                elif pkt['type'] == 'FORMAT_DEFINITION':
                    f.write(f"  Format: {pkt['data']['name']} (ID: {pkt['data']['id']})\n")
                    for field in pkt['data']['fields']:
                        f.write(f"    - {field['name']} ({field['type']})")
                        if field['unit']:
                            f.write(f" [{field['unit']}]")
                        f.write("\n")
                else:
                    f.write(f"  {pkt['data']}\n")
                
                f.write("\n")
        
        print(f"Exported to TXT: {output_file}")
    
    def export_to_json(self, output_file: str):
        """Export decoded packets to JSON"""
        data = {
            'file_info': self.file_info,
            'formats': self.formats,
            'packets': self.packets,
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Exported to JSON: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Decode binary log files from embedded datalogger',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Decode and display summary
  %(prog)s logfile.bin
  
  # Export to CSV
  %(prog)s logfile.bin --csv output.csv
  
  # Export to multiple formats
  %(prog)s logfile.bin --txt output.txt --json output.json
        """
    )
    
    parser.add_argument('input', help='Input binary log file')
    parser.add_argument('--csv', help='Export to CSV file')
    parser.add_argument('--txt', help='Export to text file')
    parser.add_argument('--json', help='Export to JSON file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not Path(args.input).exists():
        print(f"Error: File not found: {args.input}")
        sys.exit(1)
    
    # Decode file
    print(f"Decoding: {args.input}")
    decoder = BinaryLogDecoder(args.input)
    
    if not decoder.decode():
        sys.exit(1)
    
    # Export to requested formats
    if args.csv:
        decoder.export_to_csv(args.csv)
    
    if args.txt:
        decoder.export_to_txt(args.txt)
    
    if args.json:
        decoder.export_to_json(args.json)
    
    # If no export format specified, show summary
    if not (args.csv or args.txt or args.json):
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        if decoder.file_info:
            print(f"Device: {decoder.file_info.get('device_id', 'Unknown')}")
            print(f"Version: {decoder.file_info.get('version', 'Unknown')}")
        print(f"Total packets: {len(decoder.packets)}")
        
        # Count by type
        type_counts = {}
        for pkt in decoder.packets:
            pkt_type = pkt['type']
            type_counts[pkt_type] = type_counts.get(pkt_type, 0) + 1
        
        print("\nPacket types:")
        for pkt_type, count in sorted(type_counts.items()):
            print(f"  {pkt_type}: {count}")
        
        print("\nRegistered formats:")
        for fmt_id, fmt in decoder.formats.items():
            print(f"  ID {fmt_id}: {fmt['name']} ({len(fmt['fields'])} fields)")


if __name__ == '__main__':
    main()
