#!/bin/bash
set -e

VPS_IP="107.172.32.153"
VPS_PORT="9966"
SSH="ssh -p $VPS_PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$VPS_IP"

echo "=== 1. Copy server to VPS ==="
scp -P $VPS_PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  /tmp/jinhe-paibian/server.py root@$VPS_IP:/opt/attendance-api/

echo "=== 2. Setup directories ==="
$SSH "mkdir -p /var/lib/attendance && chown www-data:www-data /var/lib/attendance"

echo "=== 3. Setup systemd service ==="
scp -P $VPS_PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  /tmp/jinhe-paibian/attendance-api.service root@$VPS_IP:/etc/systemd/system/

$SSH "systemctl daemon-reload && systemctl enable attendance-api && systemctl start attendance-api && sleep 2 && systemctl status attendance-api --no-pager | head -5"

echo "=== 4. Add nginx location ==="
$SSH "python3 -c \"
c = open('/etc/nginx/sites-enabled/default').read()
if 'location /api/attendance/' not in c:
    loc = '''\\n    # Attendance API backend
    location /api/attendance/ {
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
    }\\n'''
    # Insert before the final }
    c = c[:c.rfind('}')] + loc + '}'
    open('/etc/nginx/sites-enabled/default', 'w').write(c)
    print('nginx config updated')
else:
    print('location already exists')
\" && nginx -t && nginx -s reload && echo 'nginx OK'"

echo "=== 5. Verify API ==="
sleep 2
$SSH "curl -s http://127.0.0.1:8083/api/attendance/list?year=2026\&month=6 | head -5"

echo "=== DONE! ==="
