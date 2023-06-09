import asyncio
import os

from viam.robot.client import RobotClient
from viam.rpc.dial import Credentials, DialOptions
from viam.components.base import Base
from viam.components.camera import Camera
from viam.services.vision import VisionServiceClient, VisModelConfig, VisModelType

from viam.components.sensor import Sensor

from tipsy_helpers import \
    swivel_arbitrary_amount, \
    check_if_any_people_in_view, \
    turn_towards_center_of_person, \
    move_forward_safely, \
    pause_to_serve_drinks, \
    turn_a_little_to_the_right, \
    move_forward_safely_for_specified_distance

# These must be set, you can get them from your robot's 'CODE SAMPLE' tab
robot_secret = os.getenv('ROBOT_SECRET') or ''
robot_address = os.getenv('ROBOT_ADDRESS') or ''

async def connect():
    creds = Credentials(
        type='robot-location-secret',
        payload=robot_secret)
    opts = RobotClient.Options(
        refresh_interval=0,
        dial_options=DialOptions(credentials=creds)
    )
    return await RobotClient.at_address(robot_address, opts)

async def main():
    robot = await connect()
    rover_base = Base.from_robot(robot, 'viam_base')
    camera = Camera.from_robot(robot, "my-camera")

    # Get and set up the Vision Service
    vision = VisionServiceClient.from_robot(robot)
    params = {"model_path": "./effdet0.tflite", "label_path": "./labels.txt", "num_threads": 1}
    personDet = VisModelConfig(name="person_detector", type=VisModelType("tflite_detector"), parameters=params)
    await vision.add_detector(personDet)
    names = await vision.get_detector_names()
    print(names)

    ultrasonic_sensor = Sensor.from_robot(robot, "ultrasonic")

    # N is number of times we will be running thru the control loop
    N = 200

    # Start control loop wherein we will look for objects, and move accordingly
    for i in range(N):

        await swivel_arbitrary_amount(rover_base)
        person_found = await check_if_any_people_in_view(camera, vision)
             
        if person_found:
            d, image = person_found
            await turn_towards_center_of_person(rover_base, d, image)
            await move_forward_safely(rover_base, ultrasonic_sensor)
            print("Any nearby people: feel free to grab a drink!")
            await pause_to_serve_drinks()
        else:
            print("No thirsty people in this direction!")
            print("I'll check around a bit here before I spin again!")
            local_search_attempt_counter = 0
            while local_search_attempt_counter < 4:
                turn_a_little_to_the_right()
                person_found = check_if_any_people_in_view(camera, vision)
                if person_found:
                    d, image = person_found
                    await turn_towards_center_of_person(rover_base, d, image)
                    await move_forward_safely(rover_base, ultrasonic_sensor)
                    print("Any nearby people: feel free to grab a drink!")
                    await pause_to_serve_drinks()
                else:
                    local_search_attempt_counter+=1

        if (i+1) % 10 == 0: 
            ultrasonic_sensor_result = await ultrasonic_sensor.get_readings()
            distance = ultrasonic_sensor_result["distance"]
            if distance > 10:
                distance = 10
            if distance > 3:
                distance = distance - 1
                move_forward_safely_for_specified_distance(rover_base, distance)
                    
        # the above if is meant to convey:
            # every so often, make the rover just safely move away from where it is
            # (checking that it won't hit anything),
            # just to inject some randomness so the robot is less likely to get stuck near 
            # the same cluster of people 

    await asyncio.sleep(5)
    await robot.close()

if __name__ == '__main__':
    asyncio.run(main())
