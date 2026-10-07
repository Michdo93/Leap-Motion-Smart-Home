"""
Kapitel 26 – Brücke ROS 2 <-> MQTT <-> openHAB („Smart Home ist auch Robotik“).

  openHAB -> MQTT robot/<name>/enable (ON/OFF)        -> ROS /leap_enable (Bool)
  ROS /cmd_vel (Twist)                                -> MQTT robot/<name>/cmd_vel/{linear_x,linear_y,angular_z}
  ROS /leap_zone (String)                             -> MQTT robot/<name>/zone
  Zustand der Freigabe                                -> MQTT robot/<name>/enable/state

Damit erscheint der Roboter in openHAB wie ein Gerät: Freigabe-Schalter, Zone und
aktuelle Fahrbefehle als Items (26-robotik/openhab).

Start:
  ros2 run leap_smarthome_control mqtt_bridge --ros-args -p host:=localhost \
       -p username:=robot -p password:=... -p robot:=pepper
"""

import paho.mqtt.client as mqtt
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Bool, String


class MqttBridge(Node):
    def __init__(self):
        super().__init__("leap_mqtt_bridge")
        for name, default in (("host", "localhost"), ("port", 1883), ("username", ""),
                              ("password", ""), ("robot", "pepper")):
            self.declare_parameter(name, default)
        p = lambda n: self.get_parameter(n).value  # noqa: E731
        self.base = f"robot/{p('robot')}"

        self.enable_pub = self.create_publisher(Bool, "leap_enable", 10)
        self.create_subscription(Twist, "cmd_vel", self.on_twist, 10)
        self.create_subscription(String, "leap_zone", self.on_zone, 10)
        self.last = {}

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"ros-{p('robot')}")
        if p("username"):
            self.client.username_pw_set(p("username"), p("password"))
        self.client.will_set(f"{self.base}/status", "offline", retain=True)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect_async(p("host"), int(p("port")))
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        client.publish(f"{self.base}/status", "online", retain=True)
        client.subscribe(f"{self.base}/enable")
        self.get_logger().info(f"MQTT verbunden ({reason_code})")

    def on_message(self, client, userdata, msg):
        on = msg.payload.decode().strip().upper() in ("ON", "1", "TRUE")
        self.enable_pub.publish(Bool(data=on))
        client.publish(f"{self.base}/enable/state", "ON" if on else "OFF", retain=True)

    def publish_if_changed(self, topic, value):
        if self.last.get(topic) != value:
            self.last[topic] = value
            self.client.publish(f"{self.base}/{topic}", value, retain=True)

    def on_twist(self, msg: Twist):
        self.publish_if_changed("cmd_vel/linear_x", f"{msg.linear.x:.2f}")
        self.publish_if_changed("cmd_vel/linear_y", f"{msg.linear.y:.2f}")
        self.publish_if_changed("cmd_vel/angular_z", f"{msg.angular.z:.2f}")

    def on_zone(self, msg: String):
        self.publish_if_changed("zone", msg.data)

    def destroy_node(self):
        self.client.publish(f"{self.base}/status", "offline", retain=True)
        self.client.loop_stop()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MqttBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
