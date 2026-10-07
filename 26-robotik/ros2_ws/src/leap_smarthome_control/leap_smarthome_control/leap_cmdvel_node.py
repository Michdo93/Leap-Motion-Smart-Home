"""
Kapitel 26 – ROS-2-Node: Leap Motion -> /cmd_vel (Weiterentwicklung von leap_control).

Neu gegenüber leap_control:
  * Sensor per Seriennummer wählbar (Parameter "serial") – mehrere Sensoren/Roboter
  * Totmann-Prinzip: ohne Hand, bei Sensorverlust oder ohne Freigabe -> Null-Twist
  * Freigabe über Topic /leap_enable (std_msgs/Bool), z. B. aus openHAB per MQTT-Brücke
  * nutzt leapsmarthome.leapdevices (pip install -e <Repo> im selben Python)

Start:
  ros2 run leap_smarthome_control leap_cmdvel --ros-args -p serial:=LP19566274693
"""

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Bool, String

from leapsmarthome.leapdevices import LeapDeviceManager

TIMEOUT_S = 0.5   # so lange ohne Frame -> Stopp


def twist_values(x, z, limit):
    col = -1 if x < -limit else (1 if x > limit else 0)
    row = -1 if z > limit else (1 if z < -limit else 0)
    lx = ly = az = 0.0
    if row == -1:
        lx, az = 0.5, {-1: 0.8, 0: 0.0, 1: -0.8}[col]
        zone = {-1: "VORNE_LINKS_DREHEN", 0: "VORWAERTS", 1: "VORNE_RECHTS_DREHEN"}[col]
    elif row == 1:
        lx, az = -0.4, {-1: 0.8, 0: 0.0, 1: -0.8}[col]
        zone = {-1: "HINTEN_LINKS_DREHEN", 0: "RUECKWAERTS", 1: "HINTEN_RECHTS_DREHEN"}[col]
    else:
        ly = {-1: 0.4, 0: 0.0, 1: -0.4}[col]
        zone = {-1: "LINKS_GLEITEN", 0: "STOPP", 1: "RECHTS_GLEITEN"}[col]
    return lx, ly, az, zone


class LeapCmdVel(Node):
    def __init__(self):
        super().__init__("leap_cmdvel")
        self.declare_parameter("serial", "")
        self.declare_parameter("limit_mm", 25.0)
        self.declare_parameter("rate_hz", 20.0)
        self.declare_parameter("enabled_on_start", True)

        serial = self.get_parameter("serial").value
        self.limit = float(self.get_parameter("limit_mm").value)
        self.enabled = bool(self.get_parameter("enabled_on_start").value)

        self.pub = self.create_publisher(Twist, "cmd_vel", 10)
        self.zone_pub = self.create_publisher(String, "leap_zone", 10)
        self.create_subscription(Bool, "leap_enable", self.on_enable, 10)

        self.mgr = LeapDeviceManager(
            serials={serial} if serial else None,
            on_device_added=lambda i: self.get_logger().info(f"Sensor {i.serial} verbunden"),
            on_device_removed=lambda i: self.get_logger().warn(f"Sensor {i.serial} getrennt -> STOPP"),
        ).open()
        self.last_frame_time = self.get_clock().now()
        self.last_zone = None
        self.create_timer(1.0 / float(self.get_parameter("rate_hz").value), self.tick)
        self.get_logger().info(f"Leap -> /cmd_vel aktiv (Sensor: {serial or 'beliebig'})")

    def on_enable(self, msg: Bool):
        self.enabled = bool(msg.data)
        self.get_logger().info(f"Freigabe: {'AN' if self.enabled else 'AUS'}")

    def tick(self):
        frames = self.mgr.poll_latest(timeout_ms=5)   # nur das neueste Frame (Echtzeit)
        frame = next(iter(frames.values()), None)
        now = self.get_clock().now()
        if frame is not None:
            self.last_frame_time = now
        hand = frame.hand() if frame else None

        twist = Twist()
        zone = "STOPP"
        fresh = (now - self.last_frame_time).nanoseconds / 1e9 < TIMEOUT_S
        if self.enabled and fresh and hand is not None:
            x, _, z = hand.palm_position
            lx, ly, az, zone = twist_values(x, z, self.limit)
            twist.linear.x, twist.linear.y, twist.angular.z = lx, ly, az
        elif not self.enabled:
            zone = "GESPERRT"
        self.pub.publish(twist)       # immer senden: Null-Twist hält den Roboter an
        if zone != self.last_zone:
            self.zone_pub.publish(String(data=zone))
            self.last_zone = zone

    def destroy_node(self):
        self.pub.publish(Twist())
        self.mgr.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = LeapCmdVel()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
