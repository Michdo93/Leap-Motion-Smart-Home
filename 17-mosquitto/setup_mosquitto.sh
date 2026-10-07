#!/usr/bin/env bash
# Kapitel 17 – Mosquitto auf dem Raspberry Pi installieren und einrichten
#   sudo bash setup_mosquitto.sh
# Fragt die Passwörter interaktiv ab (nichts landet in der Shell-Historie).
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"

apt-get install -y mosquitto mosquitto-clients
install -m 644 "$DIR/mosquitto/conf.d/leap.conf" /etc/mosquitto/conf.d/leap.conf
install -m 640 -o root -g mosquitto "$DIR/mosquitto/acl" /etc/mosquitto/acl

touch /etc/mosquitto/passwd
for user in leap openhab robot; do
    echo "Passwort für MQTT-Benutzer '$user':"
    mosquitto_passwd /etc/mosquitto/passwd "$user"
done
chown root:mosquitto /etc/mosquitto/passwd
chmod 640 /etc/mosquitto/passwd

systemctl enable mosquitto
systemctl restart mosquitto
systemctl --no-pager status mosquitto | head -5

cat <<'TXT'

Test in zwei Terminals:
  mosquitto_sub -h localhost -u openhab -P <passwort> -t 'leap/#' -v
  mosquitto_pub -h localhost -u leap    -P <passwort> -t leap/test -m hallo
TXT
