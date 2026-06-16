#!/usr/bin/env python3
"""Attendance API server - lightweight REST API for 金禾广场排班系统"""

import json
import sqlite3
import os
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

DB_DIR = '/var/lib/attendance'
DB_PATH = os.path.join(DB_DIR, 'attendance.db')
PORT = 8083

def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            date TEXT NOT NULL,
            shift TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (date, shift)
        )
    ''')
    conn.commit()
    conn.close()

def json_response(data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    return (status, [('Content-Type', 'application/json; charset=utf-8'),
                     ('Access-Control-Allow-Origin', '*'),
                     ('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS'),
                     ('Access-Control-Allow-Headers', 'Content-Type'),
                     ('Content-Length', str(len(body)))], body)

def error(msg, status=400):
    return json_response({'error': msg}, status)

class AttendanceHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        
        if parsed.path == '/api/attendance/list':
            year = params.get('year', [None])[0]
            month = params.get('month', [None])[0]
            if not year or not month:
                return self._respond(*error('需要 year 和 month 参数'))
            prefix = f"{year}-{int(month):02d}"
            
            conn = sqlite3.connect(DB_PATH)
            cur = conn.execute('SELECT date, shift, data FROM attendance WHERE date LIKE ? ORDER BY date, shift',
                               (prefix + '%',))
            records = {}
            for row in cur.fetchall():
                key = row[0] + '_' + row[1]
                records[key] = {'date': row[0], 'shift': row[1], 'positions': json.loads(row[2])}
            conn.close()
            return self._respond(*json_response({'records': records}))
        
        elif parsed.path == '/api/attendance/get':
            date = params.get('date', [None])[0]
            shift = params.get('shift', [None])[0]
            if not date or not shift:
                return self._respond(*error('需要 date 和 shift 参数'))
            
            conn = sqlite3.connect(DB_PATH)
            cur = conn.execute('SELECT data FROM attendance WHERE date = ? AND shift = ?', (date, shift))
            row = cur.fetchone()
            conn.close()
            if row:
                return self._respond(*json_response({'record': {'date': date, 'shift': shift, 'positions': json.loads(row[0])}}))
            else:
                return self._respond(*json_response({'record': None}))
        
        else:
            return self._respond(*error('Not found', 404))

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return self._respond(*error('无效的 JSON'))
        
        if self.path == '/api/attendance/save':
            date = data.get('date')
            shift = data.get('shift')
            positions = data.get('positions')
            if not all([date, shift, positions]):
                return self._respond(*error('缺少必要字段: date, shift, positions'))
            
            conn = sqlite3.connect(DB_PATH)
            conn.execute('''
                INSERT OR REPLACE INTO attendance (date, shift, data, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (date, shift, json.dumps(positions, ensure_ascii=False)))
            conn.commit()
            conn.close()
            return self._respond(*json_response({'status': 'ok', 'key': date + '_' + shift}))
        
        elif self.path == '/api/attendance/delete':
            date = data.get('date')
            shift = data.get('shift')
            if not date or not shift:
                return self._respond(*error('需要 date 和 shift'))
            
            conn = sqlite3.connect(DB_PATH)
            conn.execute('DELETE FROM attendance WHERE date = ? AND shift = ?', (date, shift))
            conn.commit()
            conn.close()
            return self._respond(*json_response({'status': 'deleted'}))
        
        else:
            return self._respond(*error('Not found', 404))

    def do_DELETE(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return self._respond(*error('无效的 JSON'))
        
        if self.path == '/api/attendance/delete':
            date = data.get('date')
            shift = data.get('shift')
            if not date or not shift:
                return self._respond(*error('需要 date 和 shift'))
            
            conn = sqlite3.connect(DB_PATH)
            conn.execute('DELETE FROM attendance WHERE date = ? AND shift = ?', (date, shift))
            conn.commit()
            conn.close()
            return self._respond(*json_response({'status': 'deleted'}))
        
        return self._respond(*error('Not found', 404))

    def _respond(self, status, headers, body):
        self.send_response(status)
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]} {args[1]} {args[2]}")

if __name__ == '__main__':
    init_db()
    server = HTTPServer(('127.0.0.1', PORT), AttendanceHandler)
    print(f"Attendance API server running on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("Server stopped")
