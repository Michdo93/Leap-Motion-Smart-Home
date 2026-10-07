from setuptools import find_packages, setup

package_name = "leap_smarthome_control"

setup(
    name=package_name,
    version="1.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Michael Christian Dörflinger",
    maintainer_email="michaeldoerflinger93@gmail.com",
    description="Leap Motion -> cmd_vel mit Totmann-Prinzip und MQTT-Brücke zu openHAB",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "leap_cmdvel = leap_smarthome_control.leap_cmdvel_node:main",
            "mqtt_bridge = leap_smarthome_control.mqtt_bridge_node:main",
        ],
    },
)
