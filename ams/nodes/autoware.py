#!/usr/bin/env python
# coding: utf-8

from transforms3d.quaternions import axangle2quat

from ams import Topic
from ams.nodes import Vehicle
from ams.messages import autoware_message


class Autoware(Vehicle):

    class ROSTOPIC(object):
        PUBLISH = "/based/lane_waypoints_array"
        SUBSCRIBE = "/closest_waypoint"

    class TOPIC(object):
        PUBLISH = "pub_autoware"
        SUBSCRIBE = "sub_autoware"

    def __init__(self, name, waypoint, arrow, route, waypoint_id, velocity, schedules=None, dt=1.0):
        super().__init__(name, waypoint, arrow, route, waypoint_id, velocity, schedules, dt)

        self.name = name

        self.autowarePublishTopic = Topic()
        self.autowarePublishTopic.set_id(self.name)
        self.autowarePublishTopic.set_root(Autoware.TOPIC.PUBLISH)
        self.autowarePublishTopic.set_message(autoware_message)

        self.autowareSubscribeTopic = Topic()
        self.autowareSubscribeTopic.set_id(self.name)
        self.autowareSubscribeTopic.set_root(Autoware.TOPIC.SUBSCRIBE)
        self.autowareSubscribeTopic.set_message(autoware_message)

        self.pose_index = 0
        self.current_poses = []

        self.add_on_message_function(self.set_autoware_pose)
        self.set_subscriber(self.autowareSubscribeTopic.private+"/closest_waypoint")

    def set_autoware_pose(self, _client, _userdata, topic, payload):
        if topic == self.autowareSubscribeTopic.private+"/closest_waypoint":
            message = self.autowareSubscribeTopic.unserialize(payload)
            if 0 <= message["index"] < len(self.current_poses):
                self.pose_index = message["index"]
                print(self.current_poses[self.pose_index])
                self.arrow_code = self.current_poses[self.pose_index]["arrow_code"]
                self.waypoint_id = self.current_poses[self.pose_index]["waypoint_id"]
                self.position = self.waypoint.get_position(self.waypoint_id)
                self.yaw = self.arrow.get_heading(self.arrow_code, self.waypoint_id)
            else:
                print("Lost Autoware.")

    def set_autoware_waypoints(self):
        waypoints = []
        schedule = self.schedules[0]

        arrow_waypoint_array = self.route.get_arrow_waypoint_array({
            "start_waypoint_id": schedule["route"]["start"]["waypoint_id"],
            "goal_waypoint_id": schedule["route"]["goal"]["waypoint_id"],
            "arrow_codes": schedule["route"]["arrow_codes"]
        })
        for arrowWaypoint in arrow_waypoint_array:
            waypoint_id = arrowWaypoint["waypoint_id"]
            waypoints.append({
                "position": dict(zip(["x", "y", "z"], self.waypoint.get_position(waypoint_id))),
                "orientation": dict(zip(
                    ["w", "x", "y", "z"], axangle2quat([0, 0, 1], self.waypoint.get_yaw(waypoint_id)))),
                "velocity": 2.0
            })
        if 0 < len(waypoints):
            num = min(10, len(waypoints))
            for i in range(num-1, 0, -1):
                waypoints[-i]["velocity"] = (i/num)*waypoints[-i-1]["velocity"]
            self.current_poses = arrow_waypoint_array
            payload = self.autowarePublishTopic.serialize(waypoints)
            self.publish(self.autowarePublishTopic.private+"/waypoints", payload)
